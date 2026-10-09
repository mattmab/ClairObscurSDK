"""Mod-owned resources on a shared controller Session; trusted code, not a sandbox."""
import threading
import weakref


class ScopedConsole:
    def __init__(self, scope):
        self._scope = scope
        self._commands = []
        self._exposed = {}

    def register(self, name, callback, *, owner):
        self._scope._check()
        if owner is None or not callable(callback):
            raise ValueError('A callback and lifecycle owner are required')
        def guarded(arguments):
            self._scope._check()
            return callback(arguments)
        handle = self._scope._session.console.register(name, guarded, owner=self)
        self._commands.append((owner, handle))
        return handle

    def remove_owner(self, owner):
        self._scope._check()
        for registered_owner, handle in tuple(self._commands):
            if registered_owner is owner:
                handle.remove()
                self._commands.remove((registered_owner, handle))

    def expose(self, name, value):
        self._scope._check()
        self._scope._session.console.expose(name, value)
        self._exposed[name] = value

    def execute(self, command):
        self._scope._check()
        return self._scope._session.console.execute(command)

    def write(self, text):
        self._scope._check()
        return self._scope._session.console.write(text)

    def complete(self, prefix):
        self._scope._check()
        return self._scope._session.console.complete(prefix)

    @property
    def history(self):
        self._scope._check()
        return self._scope._session.console.history

    def _close(self):
        console = self._scope._session.console
        try:
            if self._commands:
                console.remove_owner(self)
        finally:
            self._commands.clear()
            for name, value in self._exposed.items():
                # Preserve a user replacement made through persistent Python.
                if console.dispatcher.namespace.get(name) is value:
                    del console.dispatcher.namespace[name]
            self._exposed.clear()


class SessionScope:
    """A mod can release its resources without closing another mod's transport.

    Console attachment and toggle configuration belong to the controller. Explicit
    supported methods avoid exposing a second independent transport lifecycle.
    """
    def __init__(self, session):
        self._session = session
        self._owner = threading.get_ident()
        self._closed = False
        self._hooks = []
        self._leases = []
        self._menus = []
        self.console = ScopedConsole(self)

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Mod resources require the owning Python thread')
        if self._closed:
            raise RuntimeError('Mod resource scope is closed')
        self._session._check()

    @property
    def pid(self):
        self._check()
        return self._session.pid

    def find_object(self, name):
        self._check()
        return self._session.find_object(name)

    def call(self, obj, target):
        self._check()
        return self._session.call(obj, target)

    @property
    def supports_reflected_invocation(self):
        self._check()
        return self._session.supports_reflected_invocation

    def invoke(self, obj, function, **arguments):
        self._check()
        return self._session.invoke(obj, function, **arguments)

    @property
    def supports_retained_invocation(self):
        self._check()
        return self._session.supports_retained_invocation

    @property
    def supports_stable_returns(self):
        self._check()
        return self._session.supports_stable_returns

    @property
    def supports_object_assignment(self):
        self._check()
        return self._session.supports_object_assignment

    @property
    def supports_pod_values(self):
        self._check()
        return self._session.supports_pod_values

    @property
    def supports_text_values(self):
        self._check()
        return self._session.supports_text_values

    @property
    def supports_enum_values(self):
        self._check()
        return self._session.supports_enum_values

    def assign_object(self, obj, owner, name, value, *, expected, element=0, allow_mutation=False):
        self._check()
        return self._session.assign_object(obj, owner, name, value, expected=expected,
                                           element=element, allow_mutation=allow_mutation)

    def invoke_retained(self, obj, function, **arguments):
        self._check()
        result = self._session.invoke_retained(obj, function, **arguments)
        result._scope = weakref.ref(self)
        self._leases = [value for value in self._leases if value.active or value.release_pending]
        for lease in result._leases:
            lease._scope = weakref.ref(self)
            self._leases.append(lease)
        return result

    @property
    def supports_object_leases(self):
        self._check()
        return self._session.supports_object_leases

    def retain(self, obj):
        self._check()
        lease = self._session.retain(obj)
        lease._scope = weakref.ref(self)
        self._leases = [value for value in self._leases if value.active or value.release_pending]
        self._leases.append(lease)
        return lease

    def hook(self, obj, target, callback):
        self._check()
        if not callable(callback):
            raise ValueError('A callback is required')
        def guarded(context):
            if not self._closed:
                self._check()
                callback(context)
        handle = self._session.hook(obj, target, guarded)
        self._hooks.append(handle)
        return handle

    def poll(self):
        self._check()
        return self._session.poll()

    @property
    def failures(self):
        self._check()
        return self._session.failures

    def prepare_menu(self, widget, child, player, *, z_order=1000):
        """Prepare native lifecycle ownership for this scope's retained widgets."""
        self._check()
        from .menu import prepare
        self._menus = [menu for menu in self._menus if menu.active]
        before = set(self._session._menus)
        try:
            return prepare(self._session, widget, child, player, self._leases, z_order=z_order)
        finally:
            self._menus.extend(self._session._menus - before)

    @property
    def supports_menu_ownership(self):
        self._check()
        return self._session.supports_menu_ownership

    def close(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Mod cleanup requires the owning Python thread')
        if self._closed:
            return
        # Revoke callback access before any transport operation can fail.
        self._closed = True
        errors = []
        menus_closed = True
        for menu in reversed(self._menus):
            try:
                if not menu.close(): menus_closed = False
            except BaseException as error:
                menus_closed = False
                errors.append(type(error).__name__)
        self._menus.clear()
        for lease in reversed(self._leases):
            if not menus_closed:
                if lease._state == 'active': lease._state = 'pending_release'
                continue
            try:
                lease.release()
            except BaseException as error:
                errors.append(type(error).__name__)
        self._leases.clear()
        for hook in reversed(self._hooks):
            try:
                hook.remove()
            except BaseException as error:
                errors.append(type(error).__name__)
        self._hooks.clear()
        try:
            self.console._close()
        except BaseException as error:
            errors.append(type(error).__name__)
        self._session = None
        if errors:
            raise RuntimeError('Mod resource cleanup failed: ' + ', '.join(errors))
