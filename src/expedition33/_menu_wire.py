"""Experimental v14 native menu ownership envelope; never retries operations."""
from dataclasses import dataclass
import struct

from ._invocation_wire import SIZE as CALL_SIZE, IDENTITY, _identity

SIZE = 246608
PLANS_AT = 128
OPERATIONS = {'prepare': 1, 'attach': 2, 'focus': 3, 'close': 4, 'status': 5, 'open': 6}


def request(operation, owner, *, leases=None, identities=None, plans=None):
    if operation not in OPERATIONS or type(owner) is not int or not 0 < owner < 2**64:
        raise ValueError('Invalid menu operation or owner')
    packet = bytearray(PLANS_AT+CALL_SIZE*len(plans) if plans is not None else SIZE)
    struct.pack_into('<6IQ', packet, 0, 1, OPERATIONS[operation], 0, 0, 0, 0, owner)
    if operation in ('prepare','open'):
        if (leases is None or len(leases) != 2 or
                any(type(token) is not int or not 0 < token < 2**64 for token in leases) or leases[0] == leases[1]):
            raise ValueError('Menu preparation needs two distinct lease tokens')
        if identities is None or len(identities) != 5 or any(obj is None for obj in identities):
            raise ValueError('Menu preparation needs engine, widget, child, player and library identities')
        if plans is None or len(plans) not in (10,12):
            raise ValueError('Menu preparation needs ten ordered call plans')
        struct.pack_into('<2Q', packet, 32, *leases)
        for i, obj in enumerate(identities):
            IDENTITY.pack_into(packet, 48 + i * 16, *_identity(obj))
        for i, plan in enumerate(plans):
            if type(plan) is not bytes or len(plan) != CALL_SIZE or plan[:4] not in ((b'\x01\0\0\0', b'\x04\0\0\0') if i==10 else (b'\x01\0\0\0',)) or any(plan[32:40]):
                raise ValueError('Menu preparation needs undispatched v1 call plans')
            at = PLANS_AT + i * CALL_SIZE
            packet[at:at + CALL_SIZE] = plan
    elif any(value is not None for value in (leases, identities, plans)):
        raise ValueError('Only preparation accepts identities and plans')
    return bytes(packet)


@dataclass(frozen=True)
class MenuReply:
    error: int
    outcome: str
    active: bool


def decode(sent, encoded):
    if type(sent) is not bytes or len(sent) not in (SIZE,PLANS_AT+12*CALL_SIZE) or type(encoded) is not str or len(encoded) != len(sent) * 2:
        raise ValueError('Invalid menu acknowledgement size')
    received = bytes.fromhex(encoded)
    if len(received) != len(sent) or received[:8] != sent[:8] or received[20:] != sent[20:]:
        raise ValueError('Menu acknowledgement changed the request')
    error, outcome, active = struct.unpack_from('<3I', received, 8)
    if (active not in (0, 1) or
            not ((error == 810 and outcome == 0 and active == 0) or
                 (error == 816 and outcome == 1) or
                 (error in (0, 811, 812, 813, 814) and outcome == 2) or
                 (sent[4:8] in (b'\x01\0\0\0',b'\x06\0\0\0') and outcome == 2 and active == 0 and
                  (error in (901, 902) or 910 <= error <= 919 or 10000 <= error < 20000)))):
        raise ValueError('Inconsistent menu acknowledgement')
    return MenuReply(error, ('not_started', 'unknown', 'returned')[outcome], bool(active))
