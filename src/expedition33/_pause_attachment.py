"""Native-owned detach for the SDK-created pause button; no retry on ambiguity."""
import secrets
import struct
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQII')
SIZE = HEADER.size + call.SIZE

def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Invalid pause attachment size')
    version, op, owner, lease, error, state = HEADER.unpack_from(data)
    if version != 1 or op not in range(1, 8) or not owner or error or state:
        raise ValueError('Invalid pause attachment header')
    if (op in (1,3,4) and not lease) or (op in (2,7) and (lease or any(data[HEADER.size:]))) or (op in (5,6) and lease):
        raise ValueError('Invalid pause attachment ownership')

class PauseAttachment:
    def __init__(self, scope):
        self.scope = scope
        self.owner = secrets.randbits(64) or 1
        self.state = 'empty'

    def _send(self, op, lease=0, plan=None):
        session = self.scope._session
        session._check()
        body = call.encode_plan(plan) if plan is not None else bytes(call.SIZE)
        sent = HEADER.pack(1, op, self.owner, lease, 0, 0) + body
        validate_request(sent)
        self.state = 'unknown'
        try:
            response = session._transport.command('pause-attachment', sent)
            data = bytes.fromhex(response['pause_attachment_packet'])
            if len(data) != SIZE or data[:24] != sent[:24] or data[32:] != sent[32:]:
                raise ValueError('Pause attachment acknowledgement mismatch')
            error, state = HEADER.unpack_from(data)[4:]
            if error == 407 and state == 1:
                self.state = 'armed'
                return False
            if error or state != (0 if op == 2 else 1):
                raise RuntimeError(f'Pause attachment rejected ({error}, state {state})')
            self.state = 'armed' if state else 'closed'
            return True
        except BaseException:
            session._abort_ownership()
            raise

    def arm(self, lease, plan):
        if self.state != 'empty' or not lease.active or lease not in self.scope._leases or lease.object != plan.target:
            raise ValueError('Pause attachment needs its owned widget lease')
        return self._send(1, lease._token, plan)

    def close(self):
        if self.state in ('empty', 'closed'): return True
        if self.state != 'armed': raise RuntimeError('Pause detach outcome unknown; native cleanup owns it')
        return self._send(2)

    def arm_restore(self, lease, opacity, enabled):
        if self.state != 'armed' or not lease.active or lease not in self.scope._leases:
            raise ValueError('Pause restore requires its retained panel')
        for op,plan in ((3,opacity),(4,enabled)):
            if plan.target != lease.object: raise ValueError('Restore target differs from lease')
            self._send(op,lease._token,plan)

    def conceal(self, opacity, enabled):
        if self.state != 'armed': raise RuntimeError('Pause ownership is unavailable')
        if not self._send(5,plan=opacity): return False
        return self._send(6,plan=enabled)

    def restore(self):
        if self.state != 'armed': raise RuntimeError('Pause ownership is unavailable')
        return self._send(7)
