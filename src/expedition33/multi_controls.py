"""Menu-owned v17 controls, drained once per external controller poll."""
import secrets
import traceback
from . import _multi_button_wire as wire
from .menu import MenuError


class ControlAction:
    def __init__(self, owner, lease, callback):
        self._owner, self._lease, self._callback = owner, lease, callback
        self._action = secrets.randbits(64) or 1
        self._registration = 0
        self._state = 'binding'
        self._failures = []

    @property
    def active(self): return self._state == 'active'

    @property
    def failures(self): return tuple(self._failures)

    def _revoke(self, state='closed'):
        self._callback = None
        self._state = state

    def remove(self):
        session = self._owner.session()
        session._transport._check_thread()
        if self._state == 'closed': return True
        if self._state in ('unknown', 'menu_closing'):
            raise MenuError('Control cleanup belongs to its menu/session', outcome='unknown')
        self._revoke('close_pending')
        reply = self._owner.send('unbind', self)
        if reply is None: return False
        self._state = 'closed'
        self._owner.controls.remove(self)
        return True


class MenuControls:
    def __init__(self, menu):
        self.menu = menu
        self.controls = []
        self.sequence = 0
        self.dropped_events = 0

    def session(self):
        session = self.menu._session()
        if session is None: raise MenuError('Control session unavailable', outcome='unknown')
        return session

    def revoke(self, state='closed'):
        for control in self.controls: control._revoke(state)

    def protects(self, lease):
        return any(c._lease is lease and c._state != 'closed' for c in self.controls)

    def abort(self):
        self.revoke('unknown')
        self.session()._abort_ownership()

    def send(self, operation, control=None):
        session = self.session()
        session._check()
        sent = wire.request(operation, self.menu._owner,
                            control._lease._token if control else 0,
                            action=control._action if operation == 'bind' else 0,
                            child=control._lease.object if operation == 'bind' else None)
        try:
            response = session._transport.command('multi-button', sent)
            reply = wire.decode(sent, response['multi_button_packet'],
                                session=session._transport.button_action_session)
            if reply.outcome == 'unknown' or reply.error == 1014:
                raise MenuError('Control ownership is uncertain', outcome='unknown')
        except BaseException:
            self.abort()
            raise
        if reply.error == 1013: return None
        if reply.error:
            raise MenuError('Native control request rejected', outcome=reply.outcome, native_error=reply.error)
        return reply

    def bind(self, child, callback):
        session = self.session()
        session._check()
        if not session.supports_multi_controls or self.menu._state not in ('attached', 'focused'):
            raise MenuError('Controls require an attached v17 menu', outcome='not_started')
        if not callable(callback): raise TypeError('Control callback must be callable')
        leases = [lease for lease in session._leases if lease.active and
                  (lease.object.pid, lease.object.index, lease.object.serial, lease.object.address) ==
                  (child.pid, child.index, child.serial, child.address)]
        if len(leases) != 1: raise ValueError('Control requires exactly one owned child lease')
        lease = leases[0]
        if self.protects(lease) or len(self.controls) >= 64:
            raise MenuError('Control already bound or menu capacity reached', outcome='not_started')
        control = ControlAction(self, lease, callback)
        self.controls.append(control)  # Protect the lease before native acquisition.
        try:
            reply = self.send('bind', control)
            if reply is None:
                # Deferred bind has not proven that a retained reference is absent.
                control._revoke('menu_closing')
                raise MenuError('Control bind deferred; close the menu', outcome='returned', native_error=1013)
            if any(c is not control and c._registration == reply.registration for c in self.controls):
                self.abort()
                raise MenuError('Duplicate native control registration', outcome='unknown')
            control._registration = reply.registration
            control._state = 'active'
        except BaseException:
            # Rejection may follow reference acquisition: retain ownership until
            # menu close. Never guess that the child lease is now releasable.
            if control._state == 'binding': control._revoke('menu_closing')
            raise
        return control

    def bind_many(self, bindings):
        from . import _ui_batch
        session = self.session()
        session._check()
        if not _ui_batch.available(session):
            return [self.bind(child, callback) for child, callback in bindings]
        if not session.supports_multi_controls or self.menu._state not in ('attached', 'focused'):
            raise MenuError('Controls require an attached menu', outcome='not_started')
        if len(self.controls) + len(bindings) > 64:
            raise ValueError('Menu control capacity exceeded')
        controls, requests = [], []
        for child, callback in bindings:
            if not callable(callback): raise TypeError('Button callback must be callable')
            leases = [lease for lease in session._leases if lease.active and
                      (lease.object.pid, lease.object.index, lease.object.serial, lease.object.address) ==
                      (child.pid, child.index, child.serial, child.address)]
            if len(leases) != 1 or self.protects(leases[0]) or any(c._lease is leases[0] for c in controls):
                raise ValueError('Control requires one unbound owned lease')
            control = ControlAction(self, leases[0], callback)
            controls.append(control)
            requests.append(('multi-button', wire.request('bind', self.menu._owner,
                control._lease._token, action=control._action, child=child)))
        if not controls: return []
        _ui_batch.encode(requests)
        self.controls.extend(controls)
        try:
            responses = _ui_batch.execute(session, requests)
            for control, (_, sent), response in zip(controls, requests, responses):
                reply = wire.decode(sent, response['multi_button_packet'],
                                    session=session._transport.button_action_session)
                if reply.error or any(c is not control and c._registration == reply.registration for c in self.controls):
                    raise MenuError('UI control batch rejected', outcome='unknown')
                control._registration, control._state = reply.registration, 'active'
        except BaseException:
            self.abort()
            raise
        return controls

    def remove_many(self, controls):
        from . import _ui_batch
        session = self.session()
        session._check()
        if not _ui_batch.available(session):
            for control in controls:
                if not control.remove(): return False
            return True
        active = [control for control in controls if control._state != 'closed']
        if any(c not in self.controls or c._state != 'active' for c in active):
            raise MenuError('UI control cleanup state is uncertain', outcome='unknown')
        if not active: return True
        requests = [('multi-button', wire.request('unbind', self.menu._owner, c._lease._token)) for c in active]
        _ui_batch.encode(requests)
        for control in active: control._revoke('close_pending')
        try:
            responses = _ui_batch.execute(session, requests)
            for control, (_, sent), response in zip(active, requests, responses):
                reply = wire.decode(sent, response['multi_button_packet'],
                                    session=session._transport.button_action_session)
                if reply.error: raise MenuError('UI control removal failed', outcome='unknown')
                control._state = 'closed'
                self.controls.remove(control)
        except BaseException:
            self.abort()
            raise
        return True

    def poll(self):
        for control in tuple(self.controls):
            if control._state == 'close_pending': control.remove()
        active = {c._registration: c for c in self.controls if c.active}
        if not active or self.menu._state not in ('attached', 'focused'): return 0
        reply = self.send('drain')
        if reply is None: return 0
        # Validate the entire snapshot before any user callback can mutate it.
        for event in reply.events:
            control = active.get(event.registration)
            if control is None or control._action != event.action or event.sequence <= self.sequence:
                self.abort()
                raise MenuError('Unknown, stale or replaced control event', outcome='unknown')
        self.dropped_events += reply.dropped
        delivered = 0
        for event in reply.events:
            self.sequence = event.sequence
            control = active[event.registration]
            if not control.active or self.menu._state not in ('attached', 'focused'): continue
            try:
                control._callback(event)
            except BaseException:
                control._failures.append(traceback.format_exc())
                del control._failures[:-32]
            delivered += 1
        return delivered
