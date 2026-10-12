"""Session-owned scalar POST traces; native registry remains authoritative."""
from dataclasses import dataclass
from . import RuntimeQueryError
from . import _trace_wire as wire
from .tracing import prepare_trace, decode_trace

STATES = ('unopened', 'active', 'stopped', 'expired', 'capped', 'closed')
CLEANUP = ('attached', 'restored', 'conflict', 'storage_lost', 'wrong_thread')


class TraceError(RuntimeQueryError):
    def __init__(self, code):
        self.code = code
        super().__init__(f'Native trace rejected operation ({code}); no automatic retry')


@dataclass(frozen=True)
class Observation:
    sequence: int
    monotonic_ms: int
    thread: int
    pid: int
    index: int
    serial: int
    arguments: object
    return_value: object
    session: int = 0
    phase: str = 'post'


def exchange(session, request):
    try:
        response = session._transport.command('trace', request)
        return wire.decode_reply(request, response['trace_packet'], expected_pid=session.pid,
            renewable=getattr(session._transport, 'trace_renew_protocol', 0) == 1)
    except (RuntimeQueryError, ValueError, KeyError) as error:
        # A start may have installed a hook before acknowledgement failed.
        # Exiting our controller wakes native cleanup instead of abandoning it.
        session._transport._abort()
        for handle in session._traces:
            handle._state = 'unknown'
        raise RuntimeQueryError(f'Trace acknowledgement unavailable; controller cleanup requested: {error}') from error


class Trace:
    def __init__(self, session, owner, plan, reply):
        self._session, self._owner, self.plan = session, owner, plan
        self.registration = reply.registration
        self._sequence = self._time = self._observed = self._dropped = 0
        self._state = STATES[reply.state]
        self.cleanup = CLEANUP[reply.cleanup]

    @property
    def state(self):
        return self._state

    def _command(self, operation, **kwargs):
        session = self._session
        session._check()
        if self._state in ('forgotten', 'unknown', 'session_closed'):
            raise RuntimeQueryError('Trace handle is no longer usable')
        request = wire.encode_request(operation, self._owner, self.registration, **kwargs)
        reply = exchange(session, request)
        if reply.error:
            raise TraceError(reply.error)
        if reply.observed < self._observed or reply.dropped < self._dropped:
            self._reject('Trace counters moved backwards')
        self._observed, self._dropped = reply.observed, reply.dropped
        self._state, self.cleanup = STATES[reply.state], CLEANUP[reply.cleanup]
        return reply

    def _reject(self, message):
        self._session._transport._abort()
        for handle in self._session._traces:
            handle._state = 'unknown'
        raise RuntimeQueryError(message)

    def status(self):
        return self._command('status')

    def stop(self):
        return self._command('stop')

    def renew(self, *, duration_ms=300000, limit=1000):
        if getattr(self._session._transport, 'trace_renew_protocol', 0) != 1:
            raise RuntimeQueryError('This runtime cannot renew native observations')
        return self._command('renew', duration_ms=duration_ms, limit=limit)

    def read(self):
        reply = self._command('drain')
        result = []
        sequence, timestamp = self._sequence, self._time
        for event in reply.events:
            if (event.sequence <= sequence or event.monotonic_ms < timestamp or
                    event.thread != self._session._transport.start['game_thread_id']):
                self._reject('Stale trace event or unexpected game thread')
            try:
                values = decode_trace(self.plan, event.data, session=getattr(self._session._transport, 'button_action_session', 0))
            except (ValueError, IndexError, KeyError) as error:
                self._reject(f'Trace payload does not match its retained plan: {error}')
            result.append(Observation(event.sequence, event.monotonic_ms, event.thread,
                event.pid, event.index, event.serial, values.arguments, values.return_value,
                getattr(self._session._transport, 'button_action_session', 0), getattr(self.plan, 'phase', 'post')))
            sequence, timestamp = event.sequence, event.monotonic_ms
        self._sequence, self._time = sequence, timestamp
        return tuple(result)

    def close(self):
        if self._state in ('forgotten', 'session_closed'):
            return
        self._command('forget')
        self._state = 'forgotten'
        self._session._traces.discard(self)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()


def start(session, function, exemplar, *, target=None, duration_ms=10000, limit=100, catalog=None):
    session._check()
    if not session.supports_traces:
        raise RuntimeQueryError('This session has no trace backend')
    from .catalog import capture
    catalog = capture() if catalog is None else catalog
    plan = session._trace_plan_for(function)
    if plan is None:
        plan = prepare_trace(catalog, function, blueprint=getattr(session._transport, 'blueprint_trace_protocol', 0) == 1)
    else:
        # The native thunk is already installed. Reuse its original observed
        # descriptor; registration still validates identities/schema natively.
        catalog.resolve(plan.function)
    exemplar = catalog.resolve(exemplar)
    target = catalog.resolve(target) if target is not None else None
    if plan.function.pid != session.pid:
        raise ValueError('Trace function must belong to this session')
    owner = session._trace_owner_sequence + 1
    request = wire.encode_request('start', owner, plan=plan, exemplar=exemplar,
                                 target=target, duration_ms=duration_ms, limit=limit)
    session._trace_owner_sequence = owner
    reply = exchange(session, request)
    if reply.error:
        raise TraceError(reply.error)
    handle = Trace(session, owner, plan, reply)
    session._traces.add(handle)
    return handle
