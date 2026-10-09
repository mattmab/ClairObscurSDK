"""v17 menu-wide action batches; no dispatch or native mutation here."""
import struct
from ._button_action_wire import HEADER, EVENT, EVENTS_AT, OPERATIONS, ActionEvent, ActionReply, _token

SIZE = 2648
IDENTITY_AT = 2632
IDENTITY = struct.Struct('<iiQ')


def request(operation, owner, child_lease=0, *, action=0, child=None):
    if operation not in OPERATIONS or not _token(owner):
        raise ValueError('Invalid multi-button operation or owner')
    if operation == 'drain':
        if type(child_lease) is not int or child_lease != 0:
            raise ValueError('Drain is menu-wide')
    elif not _token(child_lease):
        raise ValueError('Control requires an owned lease')
    if type(action) is not int or (not _token(action) if operation == 'bind' else action != 0):
        raise ValueError('Only bind requires an action ID')
    identity = (-1, 0, 0)
    if operation == 'bind':
        if child is None:
            raise ValueError('Bind requires a child identity')
        identity = (child.index, child.serial, child.address)
        if (any(type(value) is not int for value in identity) or
                not 0 <= identity[0] < 2**31 or not 0 < identity[1] < 2**31 or
                not 0x10000 <= identity[2] < 2**64 or identity[2] & 7):
            raise ValueError('Invalid child identity')
    elif child is not None:
        raise ValueError('Only bind accepts a child identity')
    packet = bytearray(SIZE)
    HEADER.pack_into(packet, 0, 1, OPERATIONS[operation], 0, 0, 0, 0, 0, 0,
                     owner, child_lease, action, 0, 0)
    IDENTITY.pack_into(packet, IDENTITY_AT, *identity)
    return bytes(packet)


def validate_request(sent):
    from types import SimpleNamespace
    if type(sent) is not bytes or len(sent) != SIZE:
        raise ValueError('Invalid multi-button packet')
    version, operation, *_ = HEADER.unpack_from(sent)
    name = next((name for name, code in OPERATIONS.items() if operation == code), None)
    owner, lease, action = struct.unpack_from('<3Q', sent, 32)
    index, serial, address = IDENTITY.unpack_from(sent, IDENTITY_AT)
    child = SimpleNamespace(index=index, serial=serial, address=address) if name == 'bind' else None
    if version != 1 or request(name, owner, lease, action=action, child=child) != sent:
        raise ValueError('Multi-button request is not a clean packet')
    return name, owner


def decode(sent, encoded, *, session):
    name, owner = validate_request(sent)
    if not _token(session) or type(encoded) is not str or len(encoded) != SIZE * 2:
        raise ValueError('Invalid multi-button acknowledgement')
    received = bytes.fromhex(encoded)
    if (len(received) != SIZE or received[:8] != sent[:8] or
            received[24:56] != sent[24:56] or received[IDENTITY_AT:] != sent[IDENTITY_AT:]):
        raise ValueError('Multi-button acknowledgement changed request identity')
    _, _, error, outcome, count, state, _, _, _, _, _, dropped, registration = HEADER.unpack_from(received)
    if count > 64 or state > 6 or not (
        (error == 1010 and outcome == 0) or (error == 1016 and outcome == 1) or
        (error in (0, 1011, 1012, 1013, 1014) and outcome == 2)
    ):
        raise ValueError('Inconsistent multi-button outcome')
    if error:
        if outcome != 1 and (count or dropped or registration or any(received[EVENTS_AT:IDENTITY_AT])):
            raise ValueError('Rejected multi-button request returned events')
        if error == 1010 and state:
            raise ValueError('Malformed request changed control state')
        return ActionReply(error, ('not_started', 'unknown', 'returned')[outcome], state, 0, 0, ())
    if state not in (0, 2, 3, 5) or bool(registration) != (state == 2):
        raise ValueError('Inconsistent control lifecycle')
    if ((name == 'bind' and state != 2) or (name in ('drain', 'unbind') and state != 0) or
            (name != 'drain' and (count or dropped))):
        raise ValueError('Unexpected multi-button response state')
    if any(received[EVENTS_AT + count * EVENT.size:IDENTITY_AT]):
        raise ValueError('Nonzero unused multi-button output')
    events = tuple(ActionEvent(*EVENT.unpack_from(received, EVENTS_AT + i * EVENT.size)) for i in range(count))
    previous = 0
    for event in events:
        if (event.session != session or event.owner != owner or not event.registration or
                not event.action or event.sequence <= previous):
            raise ValueError('Stale, foreign or unordered multi-button event')
        previous = event.sequence
    return ActionReply(0, 'returned', state, registration, dropped, events)
