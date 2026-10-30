"""Native lifetime registration for one independently owned media widget."""
import secrets
import struct
import logging
from dataclasses import replace, fields, is_dataclass
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQII')
SIZE = HEADER.size + 2 * call.SIZE


def _target_difference(expected, actual):
    """Local diagnostics only; exact snapshot equality remains the admission gate."""
    differences = []
    if type(expected) is not type(actual):
        differences.append(f'type: lease={type(expected).__name__}, target={type(actual).__name__}')
    names = sorted({field.name for value in (expected, actual)
                    if is_dataclass(value) and not isinstance(value, type)
                    for field in fields(value)})
    missing = object()
    for name in names:
        left, right = getattr(expected, name, missing), getattr(actual, name, missing)
        if left != right:
            show = lambda value: '<missing>' if value is missing else repr(value)[:256]
            differences.append(f'{name}: lease={show(left)}, target={show(right)}')
    return '; '.join(differences) or 'unequal values without differing dataclass fields'

def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Invalid media owner size')
    version, op, owner, lease, error, state = HEADER.unpack_from(data)
    if version != 1 or op not in (1,2,3,4) or not owner or error or state:
        raise ValueError('Invalid media owner header')
    if op == 1 and not lease or op != 1 and (lease or any(data[HEADER.size:])):
        raise ValueError('Invalid media owner payload')

class NativeMediaOwner:
    def __init__(self, scope):
        self.scope, self.owner, self.state = scope, secrets.randbits(64) or 1, 'new'
        self._retiring=False
        self._retirement_ack=False
        self.retirement_error=None

    def _send(self, op, lease=0, plans=()):
        session = self.scope._session
        session._check()
        if self.state == 'unknown': raise RuntimeError('Unknown native media outcome')
        sent = HEADER.pack(1,op,self.owner,lease,0,0)
        sent += b''.join(call.encode_plan(p) for p in plans) if plans else bytes(2*call.SIZE)
        validate_request(sent)
        self.state = 'unknown'
        try:
            response = session._transport.command('media-owner',sent)
            data = bytes.fromhex(response['media_owner_packet'])
            if len(data)!=SIZE or data[:24]!=sent[:24] or data[32:]!=sent[32:]:
                raise ValueError('Media acknowledgement mismatch')
            error, state = HEADER.unpack_from(data)[4:]
            if op==4:
                if error in (407,1404) and state==1:
                    self.retirement_error=error;self.state='armed';return False
                if error or state!=0:raise RuntimeError(f'Native media retirement rejected ({error}, {state})')
                self._retirement_ack=True
            if error == 407 and state == 1:
                self.state = 'armed'
                return False
            if error or state not in (0,1): raise RuntimeError(f'Native media rejected ({error}, {state})')
            self.state = 'armed' if state else 'closed'
            return True
        except BaseException:
            if op==4:
                self.state='unknown'
                raise
            logging.getLogger(__name__).exception('Media ownership operation %s failed', op)
            session._abort_ownership()
            raise

    def arm(self, lease, close, remove):
        if self.state!='new' or not lease.active or lease not in self.scope._leases:
            raise ValueError('Owned media lease required')
        if lease.object!=close.target or lease.object!=remove.target:
            detail = ' | '.join(f'{name}: {_target_difference(lease.object, plan.target)}'
                for name, plan in (('close',close),('remove',remove)) if lease.object!=plan.target)
            raise ValueError(f'Media cleanup targets differ ({detail})')
        if any(p.parameter_size or p.parameters or p.objects for p in (close,remove)):
            raise ValueError('Media cleanup must have empty parameter frames')
        # A parameterless plan has no POD values. Use the base invocation
        # protocol for the durable cleanup executor, which has no POD context.
        close, remove = (replace(p,wire_version=1) for p in (close,remove))
        return self._send(1,lease._token,(close,remove))

    def status(self):
        self._send(3)
        return self.state

    def close(self):
        if self.state in ('new','closed'): return True
        if self._retiring:return self.retire_world()
        return self._send(2)

    def retire_world(self):
        if self.state in ('new','closed'):return True
        capability=getattr(self.scope._session._transport,'media_retirement_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Verified native media retirement capability required')
        self._retiring=True
        return self._send(4)
