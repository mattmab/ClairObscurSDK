"""Bounded independent creation groups with retained outputs; never replayed."""
from dataclasses import dataclass
from types import SimpleNamespace

from . import _retained_wire, _ui_batch

OPERATIONS = frozenset(('SpawnObject', 'AddChildToCanvas', 'AddChildToOverlay', 'AddChild', 'SetContent'))
LIMIT = 24


def available(session):
    return _ui_batch.available(session) and getattr(session._transport, 'ui_construction_protocol', 0) == 1


def invoke_group(scope, planner, prepared):
    from .catalog import capture_selected
    from .invocation import decode_result
    from .ownership import ObjectLease, RetainedInvocation
    session = scope._session
    if not available(session) or not 1 <= len(prepared) <= LIMIT:
        raise ValueError('Construction batch capability or bound unavailable')
    plans = []
    for call in prepared:
        owner, current = call._check()
        if owner is not planner or current is not session or call._plan.function.name not in OPERATIONS:
            raise ValueError('Invalid construction batch plan')
        plans.append(call._plan)
    requests = [('retained-invoke', _retained_wire.encode_plan(plan)) for plan in plans]
    catalog = planner._catalog
    # Revoke before dispatch, including failures. Never reuse uncertain plans.
    planner._generation += 1
    planner._catalog = None
    try:
        with scope._lease_context():
            responses = _ui_batch.execute(session, requests)
        decoded = [_retained_wire.decode_reply(sent, response['retained_packet'])
                   for (_, sent), response in zip(requests, responses)]
        tokens = [token for _, leases in decoded for _, token in leases]
        if len(set(tokens)) != len(tokens) or set(tokens) & {lease._token for lease in session._leases}:
            raise ValueError('Construction outputs alias native ownership')
        # Adopt ALL ownership before any read/decode can fail. Unknown/partial
        # batch acknowledgements abort the controller and use native cleanup.
        groups = []
        for reply, leases in decoded:
            if reply.outcome != 'dispatch_returned' or reply.error:
                raise ValueError('Construction did not return successfully')
            acquired = []
            for offset, token in leases:
                lease = ObjectLease(session, token, None)
                session._leases.add(lease)
                acquired.append((offset, lease))
            groups.append(acquired)
        identities = tuple(dict.fromkeys((index, serial, address)
            for reply, _ in decoded for _, index, serial, address in reply.objects))
        current = catalog.with_observations(capture_selected(session.pid, identities))
        results = []
        for plan, (reply, _), acquired in zip(plans, decoded, groups):
            result = decode_result(plan, reply, current)
            objects = {offset: index for offset, index, *_ in reply.objects}
            for offset, lease in acquired:
                lease._object = current.by_index[objects[offset]]
            owned = RetainedInvocation(session, result, tuple(lease for _, lease in acquired))
            scope._adopt_retained(owned)
            results.append(owned.return_value)
        planner._catalog = current
        return results
    except BaseException:
        session._abort_ownership()
        raise


@dataclass(frozen=True)
class PendingIndex:
    number: int


@dataclass(frozen=True)
class Pending:
    number: int

    @property
    def index(self):
        return PendingIndex(self.number)


class Construction:
    """Record detached tree creation, execute independent layers, resolve refs.

    Pending references never enter an invocation packet or a live Catalog.
    Only observed, same-call-retained outputs may be used by the next layer.
    """
    def __init__(self):
        self.calls = []
        self.results = {}

    def record(self, target, function, arguments):
        pending = Pending(len(self.calls))
        self.calls.append((pending, target, function, arguments))
        return SimpleNamespace(return_value=pending)

    def resolve(self, value):
        if isinstance(value, Pending):
            return self.results[value.number]
        if isinstance(value, PendingIndex):
            return self.results[value.number].index
        if isinstance(value, list):
            return [self.resolve(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self.resolve(item) for item in value)
        if isinstance(value, dict):
            return {self.resolve(key): self.resolve(item) for key, item in value.items()}
        return value

    def flush(self, panel):
        remaining, self.calls = self.calls, []
        while remaining:
            ready, later = [], []
            for pending, target, function, arguments in remaining:
                try:
                    target, arguments = self.resolve(target), self.resolve(arguments)
                except KeyError:
                    later.append((pending, target, function, arguments))
                    continue
                ready.append((pending, target, function, arguments))
            if not ready:
                raise ValueError('Unresolved construction dependency')
            for start in range(0, len(ready), LIMIT):
                group = ready[start:start + LIMIT]
                plans = [panel._planner.prepare(target, fn, **args) for _, target, fn, args in group]
                values = panel._mutate(invoke_group, panel.scope, panel._planner, plans)
                for (pending, *_), value in zip(group, values):
                    self.results[pending.number] = value
                # All returned leases and local dependencies are adopted before
                # servicing the independent title frontend; never yield mid-ACK.
                from .loading_preparation import service_loading_io
                service_loading_io(getattr(panel.scope,'_session',None))
            remaining = later
        # Includes text-bound dictionary keys and row/slot collections. Local
        # temporary references are not used after the explicit flush boundary.
        for name, value in tuple(vars(panel).items()):
            setattr(panel, name, self.resolve(value))
