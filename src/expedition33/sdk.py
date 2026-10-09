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
    """One native session with fixed observation, opt-in calls and object leases.

    Object snapshots are observations, never owning pointers. Native identity,
    thread, build, layout and lifetime checks remain authoritative for each call.
    Close explicitly or use a context manager to remove hooks deterministically.
    """
    def __init__(self, *, reflected=False, leases=False, retained=False, stable_returns=False):
        if any(type(flag) is not bool for flag in (reflected, leases, retained, stable_returns)):
            raise ValueError('reflected, leases, retained and stable_returns must be bools')
        retained = retained or stable_returns
        backend = ('research-probe-v9' if stable_returns else 'research-probe-v8' if retained
                   else 'research-probe-v7' if leases else 'research-probe-v6')
        self._transport = (SessionTransport(_executable=Path(__file__).resolve().parents[2] /
                           f'build/{backend}/research_probe.exe') if reflected or leases or retained else SessionTransport())
        if stable_returns and any(getattr(self._transport, name, 0) != 1 for name in
                                  ('reflected_protocol', 'lease_protocol', 'retained_protocol', 'stable_identity_protocol')):
            try:
                self._transport.close()
            finally:
                raise RuntimeQueryError('Stable retained-return backend handshake missing')
        self._dispatcher = CallbackDispatcher()
        self._hooks = []
        self._leases = set()
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
    def supports_stable_returns(self):
        self._check()
        return self.supports_retained_invocation and getattr(self._transport, 'stable_identity_protocol', 0) == 1

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

    @property
    def supports_object_leases(self):
        self._check()
        return getattr(self._transport, 'lease_protocol', 0) == 1

    @property
    def supports_retained_invocation(self):
        self._check()
        return (getattr(self._transport, 'retained_protocol', 0) == 1 and
                self.supports_object_leases and self.supports_reflected_invocation)

    def _abort_ownership(self):
        for lease in self._leases:
            lease._state = 'unknown'
        if not getattr(self._transport, '_closed', False):
            self._transport._abort()

    def invoke_retained(self, obj, function, **arguments):
        """Invoke and own object outputs before the game-thread request returns.

        Requires Session(retained=True). Release the returned owner explicitly,
        use its context manager, or rely on mod-scope/session cleanup. Copied
        snapshots remain observations and are not ownership handles themselves.
        """
        self._check()
        from .invocation import prepare_call, decode_result, UnsupportedInvocation, InvocationError
        from .ownership import ObjectLease, RetainedInvocation
        from . import _retained_wire as wire
        from .catalog import capture
        if not self.supports_retained_invocation:
            raise UnsupportedInvocation('This session has no retained invocation backend')
        if not isinstance(obj, ObjectSnapshot) or obj.pid != self.pid:
            raise ValueError('Invocation target must belong to this session')
        catalog = capture()
        plan = prepare_call(catalog, obj, function, arguments)
        request = wire.encode_plan(plan)
        try:
            response = self._transport.command('retained-invoke', request)
            reply, tokens = wire.decode_reply(request, response['retained_packet'])
        except BaseException as error:
            self._abort_ownership()
            if not isinstance(error, Exception):
                raise
            raise InvocationError(f'Retained acknowledgement unavailable: {error}', outcome='unknown') from error
        if reply.outcome == 'unknown':
            self._abort_ownership()
        if reply.outcome != 'dispatch_returned' or reply.error:
            return decode_result(plan, reply, catalog)
        acquired = []
        try:
            if {token for _, token in tokens} & {lease._token for lease in self._leases}:
                raise ValueError('Native output token aliases existing session ownership')
            # Adopt every native token before a catalog read or result conversion
            # can fail. A failed conversion still has deterministic cleanup.
            for offset, token in tokens:
                lease = ObjectLease(self, token, None)
                self._leases.add(lease)
                acquired.append((offset, lease))
            current = capture() if reply.objects else catalog
            result = decode_result(plan, reply, current)
            identities = {offset: index for offset, index, *_ in reply.objects}
            for offset, lease in acquired:
                lease._object = current.by_index[identities[offset]]
            return RetainedInvocation(self, result, tuple(lease for _, lease in acquired))
        except BaseException as error:
            # A construction failure before all tokens were adopted must close
            # the controller; otherwise clean up only this invocation's owners.
            if len(acquired) != len(tokens):
                self._abort_ownership()
            else:
                for _, lease in acquired:
                    try:
                        lease.release()
                    except BaseException:
                        self._abort_ownership()
                        break
            if not isinstance(error, Exception):
                raise
            raise InvocationError(f'Dispatch returned; retained result could not be exposed: {error}',
                                  outcome='dispatch_returned') from error

    def _lease_command(self, command, **kwargs):
        from . import _lease_wire as wire
        from .ownership import LeaseError
        packet = wire.request(command, **kwargs)
        try:
            response = self._transport.command(command, packet)
            reply = wire.decode(command, packet, response['lease_packet'])
        except (RuntimeQueryError, ValueError, KeyError) as error:
            # A bad acknowledgement may follow successful native mutation.
            # End this controller so target-owned cleanup runs; never retry it.
            for lease in self._leases:
                lease._state = 'unknown'
            if not getattr(self._transport, '_closed', False):
                self._transport._abort()
            raise LeaseError(f'Lease acknowledgement unavailable: {error}', outcome='unknown') from error
        if reply.outcome != 'completed':
            if reply.outcome == 'unknown':
                for lease in self._leases:
                    lease._state = 'unknown'
                self._transport._abort()
            raise LeaseError('Native lease operation did not complete', outcome=reply.outcome, native_error=reply.error)
        return reply

    def retain(self, obj):
        """Retain an existing observed object with an independent native lease.

        Requires Session(leases=True). This separate operation is not suitable
        for retaining a newly created invocation result across a GC gap.
        """
        self._check()
        from .ownership import ObjectLease, LeaseError
        if not self.supports_object_leases:
            raise LeaseError('This session has no object lease backend', outcome='not_dispatched')
        if not isinstance(obj, ObjectSnapshot) or obj.pid != self.pid:
            raise ValueError('Retained object must belong to this session')
        reply = self._lease_command('lease-acquire', object=obj)
        if reply.error:
            raise LeaseError('Native object acquisition rejected', outcome=reply.outcome, native_error=reply.error)
        lease = ObjectLease(self, reply.token, obj)
        self._leases.add(lease)
        return lease

    def _release_lease(self, lease):
        self._check()
        from .ownership import LeaseError
        if lease not in self._leases:
            raise LeaseError('Lease does not belong to this session', outcome='not_dispatched')
        reply = self._lease_command('lease-release', token=lease._token)
        if reply.error == 407:
            lease._state = 'pending_release'
            return False
        if reply.error:
            lease._state = 'invalid'
            raise LeaseError('Native lease release rejected', outcome=reply.outcome, native_error=reply.error)
        lease._state = 'released'
        self._leases.remove(lease)
        return True

    def _release_pending_leases(self):
        for lease in tuple(getattr(self, '_leases', ())):
            if lease.release_pending:
                self._release_lease(lease)

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
            self._release_pending_leases()
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
        leases_closed = False
        transport_was_closed = getattr(self._transport, '_closed', False)
        try:
            self._transport.close()
            leases_closed = not transport_was_closed
        finally:
            for lease in getattr(self, '_leases', ()):
                lease._state = 'released' if leases_closed and lease._state != 'unknown' else 'unknown'
            if hasattr(self, '_leases'):
                self._leases.clear()
            self.console._close()
            self._dispatcher.close()
            self._hooks.clear()
            self._enabled = False
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
