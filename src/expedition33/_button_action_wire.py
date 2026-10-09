"""Bounded v16 action packets; decoding never dispatches or retries callbacks."""
from dataclasses import dataclass
import struct

SIZE = 2632
EVENTS_AT = 72
OPERATIONS = {'bind': 1, 'drain': 2, 'unbind': 3, 'status': 4}
HEADER = struct.Struct('<8I5Q')
EVENT = struct.Struct('<5Q')


def _token(value):
    return type(value) is int and 0 < value < 2**64


def request(operation, owner, child_lease, *, action=0):
    if operation not in OPERATIONS or not _token(owner) or not _token(child_lease):
        raise ValueError('Invalid button action operation or owner/lease')
    if type(action) is not int or (not _token(action) if operation == 'bind' else action != 0):
        raise ValueError('Only bind requires an action ID')
    packet = bytearray(SIZE)
    HEADER.pack_into(packet, 0, 1, OPERATIONS[operation], 0, 0, 0, 0, 0, 0,
                     owner, child_lease, action, 0, 0)
    return bytes(packet)


@dataclass(frozen=True)
class ActionEvent:
    session: int
    registration: int
    owner: int
    action: int
    sequence: int


@dataclass(frozen=True)
class ActionReply:
    error: int
    outcome: str
    state: int
    registration: int
    dropped: int
    events: tuple[ActionEvent, ...]


def decode(sent, encoded, *, session):
    if not _token(session) or type(sent) is not bytes or len(sent) != SIZE:
        raise ValueError('Invalid action request/session')
    version, operation, *_ = HEADER.unpack_from(sent)
    owner, lease, action = struct.unpack_from('<3Q', sent, 32)
    name = next((name for name, code in OPERATIONS.items() if code == operation), None)
    if version != 1 or name is None or request(name, owner, lease, action=action) != sent:
        raise ValueError('Action request was not a clean v1 packet')
    if type(encoded) is not str or len(encoded) != SIZE*2:
        raise ValueError('Invalid action acknowledgement size')
    received = bytes.fromhex(encoded)
    if len(received) != SIZE or received[:8] != sent[:8] or received[24:56] != sent[24:56]:
        raise ValueError('Action acknowledgement changed request identity')
    _, _, error, outcome, count, state, _, _, _, _, _, dropped, registration = HEADER.unpack_from(received)
    if count > 64 or state > 6 or not (
        (error == 910 and outcome == 0) or (error == 916 and outcome == 1) or
        (error in (0, 911, 912, 913, 914) and outcome == 2)
    ):
        raise ValueError('Inconsistent action outcome')
    if error:
        # Unknown output can be partial. Never deliver any of it to a callback.
        if outcome != 1 and (count or dropped or registration or any(received[EVENTS_AT:])):
            raise ValueError('Rejected action returned event data')
        if error == 910 and state != 0:
            raise ValueError('Malformed request changed action state')
        return ActionReply(error, ('not_started', 'unknown', 'returned')[outcome], state, 0, 0, ())
    if state not in (0, 2, 3, 5) or bool(registration) != (state == 2):
        raise ValueError('Inconsistent action lifecycle state')
    if (name == 'bind' and state != 2) or (name == 'unbind' and state != 0):
        raise ValueError('Action did not reach its required state')
    if name == 'drain' and state == 0:
        raise ValueError('Empty action owner cannot return a successful drain')
    if name != 'drain' and (count or dropped):
        raise ValueError('Only drain can return events')
    if any(received[EVENTS_AT + count*EVENT.size:]):
        raise ValueError('Nonzero unused action output')
    events = tuple(ActionEvent(*EVENT.unpack_from(received, EVENTS_AT+i*EVENT.size)) for i in range(count))
    previous = 0
    for event in events:
        if (event.session != session or event.owner != owner or
                not event.registration or event.registration != registration or
                not event.action or event.sequence <= previous):
            raise ValueError('Stale, foreign or unordered action event')
        previous = event.sequence
    return ActionReply(0, 'returned', state, registration, dropped, events)
