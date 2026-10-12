"""Experimental v7 ownership packet; no public retention API yet."""
from dataclasses import dataclass
import struct

PACKET = struct.Struct('<4IiiQQ')
SIZE = PACKET.size


def request(command, *, object=None, token=0):
    if command not in ('lease-acquire', 'lease-release', 'lease-status'):
        raise ValueError('Invalid lease command')
    if command == 'lease-acquire':
        if object is None or object.index < 0 or object.address <= 0 or token:
            raise ValueError('Acquire requires an object identity and no token')
        identity = object.index, object.serial, object.address
    else:
        if object is not None:
            raise ValueError('Only acquire takes an object')
        identity = -1, 0, 0
        if type(token) is not int or not 0 <= token < 2**64:
            raise ValueError('Invalid lease token')
        if (command == 'lease-release' and not token) or (command == 'lease-status' and token):
            raise ValueError('Token does not match lease command')
    return PACKET.pack(1, 0, 0, 0, *identity, token)


@dataclass(frozen=True)
class LeaseReply:
    error: int
    outcome: str
    active: int
    token: int


def decode(command, sent, encoded, *, capacity=128):
    if type(capacity) is not int or not 1<=capacity<=4096:
        raise ValueError('Invalid negotiated lease bound')
    if type(sent) is not bytes or len(sent) != SIZE or not isinstance(encoded, str) or len(encoded) != SIZE * 2:
        raise ValueError('Invalid lease packet size; operation outcome unknown')
    original = PACKET.unpack(sent)
    try:
        received = PACKET.unpack(bytes.fromhex(encoded))
    except (ValueError, struct.error) as error:
        raise ValueError('Invalid lease packet encoding; operation outcome unknown') from error
    version, error, outcome, active, index, serial, address, token = received
    if (version != 1 or received[4:7] != original[4:7] or
            outcome not in (0, 1, 2) or active > capacity or
            error not in (0, *range(400, 412)) or
            (outcome == 0 and not error) or
            (command != 'lease-acquire' and token != original[7]) or
            (command == 'lease-acquire' and ((not error and outcome == 1 and not token) or (error and token)))):
        raise ValueError('Inconsistent lease reply; operation outcome unknown')
    return LeaseReply(error, ('not_dispatched', 'completed', 'unknown')[outcome], active, token)
