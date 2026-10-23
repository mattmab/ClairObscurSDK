"""Controller-owned registry routing over the bounded v19 native key queue."""
import logging
from . import RuntimeQueryError
from . import _key_wire as wire
from ._session import supports_keys
from .management import ManagementError


class KeybindService:
    def __init__(self, session, registry):
        session._check()
        if not supports_keys(session._transport):
            raise ValueError('Keybind delivery requires the v19 runtime')
        if getattr(session, '_key_binding_owner', None) is not None:
            raise ValueError('This session already has a keybind owner')
        self.session, self.registry = session, registry
        self._routes = None
        self._generation = 0
        self._closed = self._failed = False
        self.dropped = 0
        self._capture = None
        session._key_binding_owner = self

    def _exchange(self, operation, bindings=()):
        sent = wire.request(operation, self.session._transport.button_action_session,
                            self._generation, bindings)
        try:
            response = self.session._transport.command('keys', sent)
            error, dropped, events = wire.decode(sent, response.get('key_packet'))
            if error:
                raise RuntimeQueryError(f'Native key request rejected ({error}); no retry')
            return dropped, events
        except BaseException:
            self._failed = True
            raise

    def _replace(self, routes, *, capture=False):
        if len(routes) > wire.CAPACITY:
            raise ManagementError('At most 96 active nonconflicting keybinds are supported')
        self._generation = getattr(self.session, '_key_map_sequence', 0) + 1
        self.session._key_map_sequence = self._generation
        self._exchange('capture' if capture else 'replace', tuple((i + 1, route[3]) for i, route in enumerate(routes)))
        self._routes = routes

    def begin_capture(self, owner, callback):
        """Replace gameplay routes with one menu-owned, one-shot keyboard capture."""
        self.session._check()
        if self._closed or self._failed or self._capture is not None:
            raise ManagementError('Key capture is unavailable or already active')
        if getattr(self.session._transport,'key_capture_protocol',0)!=1:
            raise ManagementError('This runtime does not support press-a-key capture')
        if owner is None or not callable(callback): raise ValueError('Capture needs an owner and callback')
        from .keys import VIRTUAL_KEYS
        routes=tuple((None,None,key,vk) for key,vk in VIRTUAL_KEYS.items())
        self._replace(routes,capture=True)
        self._capture=(owner,callback)

    def cancel_capture(self, owner):
        self.session._check()
        if self._capture is None or self._capture[0] is not owner:return False
        self._capture=None
        if not self._closed and not self._failed:self._replace(self.registry.key_routes())
        return True

    def poll(self):
        if self._closed or self._failed:
            return 0
        self.session._check()
        routes = self._routes if self._capture else self.registry.key_routes()
        if routes != self._routes:
            self._replace(routes)
        dropped, events = self._exchange('drain')
        if any(token > len(routes) or routes[token-1][3] != key for token, key in events):
            self._failed = True
            raise RuntimeQueryError('Native key event does not match the acknowledged map')
        if dropped:
            self.dropped += dropped + len(events)
            logging.getLogger(__name__).warning('Discarded overflowing key batch (%d events)', dropped + len(events))
            return 0
        if self._capture and events:
            owner,callback=self._capture
            key=routes[events[0][0]-1][2]
            # Clear the capture and all remaining queued presses before any UI
            # callback. The captured key must never invoke a gameplay action.
            self.cancel_capture(owner)
            callback(key)
            return 1
        delivered = 0
        for token, _key in events:
            if self._closed or getattr(self.session, '_closed', False):
                break
            selection, binding, key, _vk = routes[token-1]
            try:
                self.registry.dispatch_key(selection, binding, key)
                delivered += 1
            except ManagementError as error:
                # Reload/remap/disable during an earlier callback revokes later
                # deliveries. A mod exception is contained by the same boundary.
                logging.getLogger(__name__).warning('Keybind delivery rejected: %s', error)
        return delivered

    def close(self):
        if self._closed:
            return
        # Only the validated native exit report proves the target is gone.
        # A broken transport alone must retain borrowed-session ownership.
        target_exited = getattr(self.session._transport, 'target_exit_code', None) is not None
        try:
            if not target_exited and not getattr(self.session, '_closed', False):
                self.session._check()
                if self._failed:
                    # Preserve borrowed-session ownership. Its host must close
                    # the transport; retain our claim so it cannot be adopted.
                    raise RuntimeQueryError('Key transport outcome uncertain; close the owning session')
                else:
                    self._replace(())
        finally:
            self._capture = None
            self._closed = True
            self._routes = ()
            if (target_exited or not self._failed or getattr(self.session, '_closed', False)) and getattr(self.session, '_key_binding_owner', None) is self:
                self.session._key_binding_owner = None
