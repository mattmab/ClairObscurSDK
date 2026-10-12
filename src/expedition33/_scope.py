"""Mod-owned resources on a shared controller Session; trusted code, not a sandbox."""
import threading
import weakref
from contextlib import contextmanager


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


class ScopedTrace:
    """A trace handle whose public operations require its mod scope to be live."""
    def __init__(self, scope, native):
        self._scope, self._native = scope, native

    @property
    def state(self):
        self._scope._check()
        return self._native.state

    @property
    def plan(self):
        self._scope._check()
        return self._native.plan

    def read(self):
        self._scope._check()
        return self._native.read()

    def status(self):
        self._scope._check()
        return self._native.status()

    def stop(self):
        self._scope._check()
        return self._native.stop()

    def renew(self, *, duration_ms=300000, limit=1000):
        self._scope._check()
        return self._native.renew(duration_ms=duration_ms, limit=limit)

    def close(self):
        self._scope._check()
        self._native.close()
        if self._native in self._scope._traces:
            self._scope._traces.remove(self._native)

    def __enter__(self):
        self._scope._check()
        return self

    def __exit__(self, *_exc):
        self.close()


class SessionScope:
    """A mod can release its resources without closing another mod's transport.

    Console attachment and toggle configuration belong to the controller. Explicit
    supported methods avoid exposing a second independent transport lifecycle.
    """
    def __init__(self, session, *, lease_owner=None):
        self._parent = None
        self._children = []
        inherited_owner=None
        if isinstance(session, SessionScope):
            session._check()
            self._parent = weakref.ref(session)
            session._children.append(self)
            inherited_owner=getattr(session,'_lease_owner_id',0)
            session = session._session
        self._session = session
        self._lease_owner_id=0
        if getattr(getattr(session,'_transport',None),'lease_policy_protocol',0)==1:
            from .lease_policy import owner_id
            self._lease_owner_id=inherited_owner if inherited_owner is not None else owner_id(session,lease_owner or 'sdk')
        self._owner = threading.get_ident()
        self._closed = False
        self._hooks = []
        self._traces = []
        self._leases = []
        self._menus = []
        self._sequence_owners = []
        self._reference_owners = []
        self._audio_owners = []
        self.console = ScopedConsole(self)
        self.actions = None

    @contextmanager
    def _lease_context(self):
        self._check()
        transport=getattr(self._session,'_transport',None)
        if getattr(transport,'lease_policy_protocol',0)!=1:
            yield;return
        previous=getattr(transport,'_lease_owner',0)
        transport._lease_owner=self._lease_owner_id
        try:yield
        finally:transport._lease_owner=previous

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Mod resources require the owning Python thread')
        if self._closed:
            raise RuntimeError('Mod resource scope is closed')
        if self._parent is not None:
            parent = self._parent()
            if parent is None or parent._closed:
                raise RuntimeError('Parent resource scope is closed')
        self._session._check()

    @property
    def supports_traces(self):
        self._check()
        return self._session.supports_traces

    def trace(self, function, exemplar, *, target=None, duration_ms=10000, limit=100):
        self._check()
        native = self._session.trace(function, exemplar, target=target,
                                     duration_ms=duration_ms, limit=limit)
        self._traces.append(native)
        return ScopedTrace(self, native)

    def _trace_plan_for(self, function):
        self._check()
        return self._session._trace_plan_for(function)

    @property
    def supports_multi_controls(self):
        self._check()
        return self._session.supports_multi_controls

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
    def supports_vector_values(self):
        self._check()
        return self._session.supports_vector_values

    @property
    def supports_timespan_values(self):
        self._check()
        return self._session.supports_timespan_values

    @property
    def supports_frame_time_values(self):
        self._check()
        return self._session.supports_frame_time_values

    @property
    def supports_pod_values(self):
        self._check()
        return self._session.supports_pod_values

    @property
    def supports_string_values(self):
        self._check()
        return self._session.supports_string_values

    @property
    def supports_text_values(self):
        self._check()
        return self._session.supports_text_values

    @property
    def supports_enum_values(self):
        self._check()
        return self._session.supports_enum_values

    def assign_object(self, obj, owner, name, value, *, expected, element=0, allow_mutation=False, catalog=None):
        self._check()
        return self._session.assign_object(obj, owner, name, value, expected=expected,
                                           element=element, allow_mutation=allow_mutation, catalog=catalog)

    def invoke_retained(self, obj, function, **arguments):
        self._check()
        with self._lease_context():
            result = self._session.invoke_retained(obj, function, **arguments)
        return self._adopt_retained(result)

    def _adopt_retained(self, result):
        result._scope = weakref.ref(self)
        self._leases = [value for value in self._leases if value.active or value.release_pending]
        for lease in result._leases:
            lease._scope = weakref.ref(self)
            self._leases.append(lease)
        return result

    def invocation_planner(self, *, selected_results=False, catalog=None, observations=None):
        """Prepared calls retain the same mod-scope lifetime and result ownership."""
        self._check()
        from .prepared_invocation import InvocationPlanner
        return InvocationPlanner(self._session, scope=self, selected_results=selected_results, catalog=catalog, observations=observations)

    @property
    def supports_object_leases(self):
        self._check()
        return self._session.supports_object_leases

    def retain(self, obj):
        self._check()
        with self._lease_context():
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

    def prepare_menu(self, widget, child, player, *, z_order=1000, catalog=None):
        """Prepare native lifecycle ownership for this scope's retained widgets."""
        self._check()
        from .menu import prepare
        self._menus = [menu for menu in self._menus if menu.active]
        before = set(self._session._menus)
        try:
            return prepare(self._session, widget, child, player, self._leases, z_order=z_order, catalog=catalog)
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
        if self.actions is not None:
            try:
                self.actions._close()
            except BaseException as error:
                errors.append(type(error).__name__)
        for child in reversed(tuple(self._children)):
            try:
                child.close()
            except BaseException as error:
                errors.append(type(error).__name__)
        self._children.clear()
        trace_cleanup_failed = False
        for trace in reversed(self._traces):
            try:
                trace.close()
            except BaseException as error:
                trace_cleanup_failed = True
                errors.append('trace cleanup: ' + type(error).__name__)
        self._traces.clear()
        if trace_cleanup_failed:
            # The scope is already revoked and cannot own a deferred retry.
            # Controller exit invokes the target-owned close/retry machinery.
            for trace in getattr(self._session, '_traces', ()):
                trace._state = 'unknown'
            try:
                self._session._transport._abort()
            except BaseException as error:
                errors.append('trace controller cleanup: ' + type(error).__name__)
        menus_closed = True
        for owner in reversed(self._sequence_owners):
            try:
                if not owner.close():
                    menus_closed = False
                    errors.append('native sequence cleanup deferred')
            except BaseException as error:
                menus_closed = False
                errors.append('sequence cleanup: ' + type(error).__name__)
        self._sequence_owners.clear()
        for owner in reversed(self._audio_owners):
            try:
                if not owner.close():
                    menus_closed = False
                    errors.append('native audio cleanup deferred')
            except BaseException as error:
                menus_closed = False
                errors.append('audio cleanup: ' + type(error).__name__)
        self._audio_owners.clear()
        for owner in reversed(self._reference_owners):
            try:
                if not owner.close():
                    menus_closed = False
                    errors.append('native reference restoration deferred')
            except BaseException as error:
                menus_closed = False
                errors.append('reference restoration: ' + type(error).__name__)
        self._reference_owners.clear()
        if not menus_closed:
            # Closed scopes cannot retry deferred ownership work. Native session
            # teardown retains the owner and retries only pre-dispatch deferral.
            self._session._abort_ownership()
        for menu in reversed(self._menus):
            try:
                if not menu.close():
                    menus_closed = False
                    errors.append('native menu cleanup deferred')
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
        if self._parent is not None:
            parent = self._parent()
            if parent is not None and self in parent._children:
                parent._children.remove(self)
            self._parent = None
        if errors:
            raise RuntimeError('Mod resource cleanup failed: ' + ', '.join(errors))
