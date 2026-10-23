"""Native-owned detach for the SDK-created pause button; no retry on ambiguity."""
import secrets
import struct
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQII')
SIZE = HEADER.size + call.SIZE

def validate_request(data,*,allow_retired=False):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Invalid pause attachment size')
    version, op, owner, lease, error, state = HEADER.unpack_from(data)
    if version != 1 or op not in range(1,9 if allow_retired else 8) or not owner or error or state:
        raise ValueError('Invalid pause attachment header')
    if (op in (1,3,4) and not lease) or (op in (2,7,8) and (lease or any(data[HEADER.size:]))) or (op in (5,6) and lease):
        raise ValueError('Invalid pause attachment ownership')

class PauseCaptureDeferred(RuntimeError):
    """Native preparation is not ready; its temporary collector remains owned."""

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
        validate_request(sent,allow_retired=getattr(session._transport,'retired_world_cleanup_protocol',0)==1)
        self.state = 'unknown'
        try:
            response = session._transport.command('pause-attachment', sent)
            data = bytes.fromhex(response['pause_attachment_packet'])
            if len(data) != SIZE or data[:24] != sent[:24] or data[32:] != sent[32:]:
                raise ValueError('Pause attachment acknowledgement mismatch')
            error, state = HEADER.unpack_from(data)[4:]
            if error==407 and state==2 and op in (1,2,8):
                self.state='capture_pending'
                if op==1:raise PauseCaptureDeferred('Pause preparation cleanup deferred; retain owner')
                return False
            if error == 407 and state == 1:
                self.state = 'armed'
                return False
            if error or state != (0 if op in (2,8) else 1):
                raise RuntimeError(f'Pause attachment rejected ({error}, state {state})')
            self.state = 'armed' if state else 'closed'
            return True
        except PauseCaptureDeferred:
            raise
        except BaseException:
            session._abort_ownership()
            raise

    def arm(self, lease, plan):
        if self.state != 'empty' or not lease.active or lease not in self.scope._leases or lease.object != plan.target:
            raise ValueError('Pause attachment needs its owned widget lease')
        return self._send(1, lease._token, plan)

    def close(self):
        if self.state in ('empty', 'closed'): return True
        if self.state not in ('armed','capture_pending'): raise RuntimeError('Pause detach outcome unknown; native cleanup owns it')
        return self._send(2)

    def retire_world(self):
        if self.state in ('empty','closed'):return True
        if self.state not in ('armed','capture_pending'):raise RuntimeError('Pause detach outcome unknown; preserve native journal')
        transport=self.scope._session._transport
        if type(getattr(transport,'retired_world_cleanup_protocol',0)) is not int or transport.retired_world_cleanup_protocol!=1:
            raise RuntimeError('Native retired-world cleanup unavailable')
        return self._send(8)

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

    def show_busy(self, enabled):
        """Keep the panel visible, with native-owned restoration of disabled input."""
        if not self.restore(): return False
        return self._send(6, plan=enabled)

    def hide_busy(self, opacity):
        """Hide after show_busy; input is already disabled by this owner."""
        return self._send(5, plan=opacity)
