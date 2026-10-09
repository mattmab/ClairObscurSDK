"""Small mod-facing API for the experimentally supported runtime specimen.

Use ``with sdk.Session() as session``. Callbacks observe copied results on the
Python owner thread when poll() runs; they cannot alter the engine call.
"""
import weakref
from pathlib import Path

from . import RuntimeQueryError, ObjectSnapshot, objects
from ._callbacks import CallbackDispatcher, ObservedIdentity, ObserverContext
from ._session import SessionTransport
from ._console import Console

TARGET = 'Actor.IsActorBeingDestroyed'


class Hook:
    def __init__(self, session, subscription):
        self._session = weakref.ref(session)
        self._subscription = subscription

    @property
    def active(self):
        return self._subscription.active

    def remove(self):
        session = self._session()
        if session is not None:
            if session._closed:
                return
            session._check()
            self._subscription.remove()
            session._reconcile()

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.remove()


class Session:
    """One native session with fixed observation and opt-in reflected calls.

    Object snapshots are observations, never owning pointers. Native identity,
    thread, build, layout and lifetime checks remain authoritative for each call.
    Close explicitly or use a context manager to remove hooks deterministically.
    """
    def __init__(self, *, reflected=False):
        if type(reflected) is not bool:
            raise ValueError('reflected must be a bool')
        self._transport = (SessionTransport(_executable=Path(__file__).resolve().parents[2] /
                           'build/research-probe-v6/research_probe.exe') if reflected else SessionTransport())
        self._dispatcher = CallbackDispatcher()
        self._hooks = []
        self._enabled = False
        self._closed = False
        self._polling = False
        self._sequence = 0
        self.dropped_events = 0
        self.console = Console(self)
        row = next(row for row in self._transport.objects if row['class_name'] == 'Actor')
        self._object = ObjectSnapshot(pid=self._transport.start['pid'], index=row['index'],
            serial=row['serial'], address=int(row['address'], 16), name=row['name'],
            class_name=row['class_name'], metaclass_name=row['metaclass_name'], class_index=row['class_index'])

    def _check(self):
        self._transport._check_thread()
        if self._closed:
            raise RuntimeQueryError('SDK session is closed')

    @property
    def pid(self):
        """Process identity established by this session's native handshake."""
        self._check()
        return self._object.pid

    def find_object(self, name):
        self._check()
        matches = [obj for obj in objects() if obj.pid == self._object.pid and obj.name == name]
        if len(matches) != 1:
            raise RuntimeQueryError(f'Expected one object named {name!r}; found {len(matches)}')
        return matches[0]

    def _validate_target(self, obj, target):
        self._check()
        if obj != self._object or target != TARGET:
            raise ValueError('This build supports only Default__Actor.Actor.IsActorBeingDestroyed')

    def call(self, obj, target):
        self._validate_target(obj, target)
        result = self._transport.command('invoke')['result']
        if result not in (0, 1):
            raise RuntimeQueryError('Invalid native bool result')
        return bool(result)

    @property
    def supports_reflected_invocation(self):
        self._check()
        return getattr(self._transport, 'reflected_protocol', 0) == 1

    def invoke(self, obj, function, **arguments):
        """Invoke an observed native UFunction through the opt-in v6 backend.

        Returns InvocationResult with named outputs and a separate return value.
        Object results are observations, not GC roots. Native-owned argument
        types remain unsupported; dispatch return does not prove an RPC ran.
        """
        self._check()
        from .invocation import prepare_call, decode_result, UnsupportedInvocation, InvocationError
        from ._invocation_wire import encode_plan, decode_reply
        from .catalog import capture
        if not self.supports_reflected_invocation:
            raise UnsupportedInvocation('This session has no reflected invocation backend')
        if not isinstance(obj, ObjectSnapshot) or obj.pid != self.pid:
            raise ValueError('Invocation target must belong to this session')
        catalog = capture()
        plan = prepare_call(catalog, obj, function, arguments)
        request = encode_plan(plan)
        try:
            response = self._transport.command('reflected-invoke', request)
            reply = decode_reply(request, response['call_packet'])
        except (RuntimeQueryError, ValueError, KeyError) as error:
            raise InvocationError(f'Invocation acknowledgement unavailable: {error}', outcome='unknown') from error
        if reply.outcome != 'dispatch_returned' or reply.error:
            return decode_result(plan, reply, catalog)
        try:
            current = capture() if reply.objects else catalog
        except RuntimeQueryError as error:
            raise InvocationError(f'Dispatch returned; result catalog unavailable: {error}',
                                  outcome='dispatch_returned') from error
        return decode_result(plan, reply, current)

    def hook(self, obj, target, callback):
        self._validate_target(obj, target)
        # Drop older observations before changing subscriber membership.
        self.poll()
        subscription = self._dispatcher.subscribe(target, callback)
        try:
            if not self._enabled:
                self._transport.command('enable')
                self._enabled = True
        except BaseException:
            subscription.remove()
            raise
        handle = Hook(self, subscription)
        self._hooks.append(handle)
        return handle

    def _reconcile(self):
        self._hooks = [hook for hook in self._hooks if hook.active]
        if not self._hooks and self._enabled:
            self._transport.command('disable')
            self._enabled = False

    def poll(self):
        self._check()
        if self._polling:
            raise RuntimeError('Recursive SDK event polling is not supported')
        self._polling = True
        delivered = 0
        try:
            batch = self._transport.command('drain')
            self.dropped_events += batch['dropped']
            identity = ObservedIdentity(self._object.pid, self._object.index, self._object.serial,
                                        self._object.name, self._object.class_name)
            for event in batch['events']:
                if (int(event['object_address'], 16) != self._object.address or
                    event['thread'] != self._transport.start['game_thread_id'] or event['result'] not in (0, 1)):
                    raise RuntimeQueryError('Native hook event identity or result mismatch')
                self._sequence += 1
                delivered += self._dispatcher.deliver(ObserverContext(self._sequence, TARGET,
                    identity, event['thread'], bool(event['result'])))
            self._reconcile()
            return delivered
        finally:
            self._polling = False

    @property
    def failures(self):
        return self._dispatcher.failures()

    def close(self):
        self._transport._check_thread()
        if self._closed:
            return
        try:
            self._transport.close()
        finally:
            self.console._close()
            self._dispatcher.close()
            self._hooks.clear()
            self._enabled = False
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
