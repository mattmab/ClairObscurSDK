"""Menu-owned external-Python callbacks for the experimental v16 button path."""
import secrets
import traceback
from . import RuntimeQueryError
from . import _button_action_wire as wire
from .menu import MenuError


class ButtonAction:
    def __init__(self, menu, callback):
        self._menu = menu
        self._callback = callback
        self._action = secrets.randbits(64) or 1
        self._registration = 0
        self._state = 'binding'
        self._last_sequence = 0
        self.dropped_events = 0
        self._failures = []

    @property
    def active(self): return self._state == 'active'

    @property
    def failures(self): return tuple(self._failures)

    def _revoke(self, state='closed'):
        self._callback = None
        self._state = state

    def _send(self, operation):
        menu = self._menu
        session = menu._session()
        if session is None: raise MenuError('Button session unavailable', outcome='unknown')
        session._check()
        sent = wire.request(operation, menu._owner, menu._leases[1]._token,
                            action=self._action if operation == 'bind' else 0)
        try:
            response = session._transport.command('button-action', sent)
            result = wire.decode(sent, response['button_action_packet'],
                                 session=session._transport.button_action_session)
            if result.outcome == 'unknown' or result.error == 914:
                raise ValueError('Button ownership is uncertain')
        except (RuntimeQueryError, ValueError, KeyError) as error:
            self._revoke('unknown')
            session._abort_ownership()
            raise MenuError('Button action acknowledgement unavailable', outcome='unknown') from error
        except BaseException:
            self._revoke('unknown')
            session._abort_ownership()
            raise
        if result.error == 913: return None
        if result.error:
            raise MenuError('Button action rejected', outcome=result.outcome, native_error=result.error)
        return result

    def _bind(self):
        try:
            result = self._send('bind')
            if result is None:
                self._revoke('closed')
                raise MenuError('Button binding deferred before installation', outcome='returned', native_error=913)
            self._registration = result.registration
            self._state = 'active'
        except BaseException:
            if self._state != 'unknown': self._revoke('closed')
            raise

    def remove(self):
        session = self._menu._session()
        if session is not None: session._transport._check_thread()
        if self._state == 'closed': return True
        if self._state in ('unknown', 'menu_closing'):
            raise MenuError('Button cleanup belongs to its menu/session', outcome='unknown')
        self._revoke('close_pending')
        if self._send('unbind') is None: return False
        self._state = 'closed'
        return True

    def _poll(self):
        if self._state == 'close_pending':
            self.remove()
            return 0
        if not self.active: return 0
        result = self._send('drain')
        if result is None: return 0
        if result.state == 5:  # Native delegate destroyed; its route was revoked.
            self._revoke('close_pending')
            return 0
        if (result.state != 2 or result.registration != self._registration or
                any(event.registration != self._registration or event.action != self._action or
                    event.sequence <= self._last_sequence for event in result.events)):
            self._revoke('unknown')
            self._menu._session()._abort_ownership()
            raise MenuError('Stale or replaced button event registration', outcome='unknown')
        self.dropped_events += result.dropped
        delivered = 0
        for event in result.events:
            if not self.active or not self._menu.active: break
            self._last_sequence = event.sequence
            readiness=getattr(self._menu,'_world_callback_readiness',None)
            if readiness is not None and readiness() is not True:continue
            try:
                self._callback(event)
            except BaseException:
                self._failures.append(traceback.format_exc())
                del self._failures[:-32]
            delivered += 1
        return delivered

    def __enter__(self): return self
    def __exit__(self, *_exc): self.remove()
