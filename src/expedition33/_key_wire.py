"""v19 bounded key map/event wire format; events contain no Unreal pointers."""
import struct
from .keys import VIRTUAL_KEYS

HEADER = struct.Struct('<IIQQIIII')
BINDING = struct.Struct('<II')
CAPACITY = 64
SIZE = HEADER.size + BINDING.size * CAPACITY


def request(operation, session, generation, bindings=()):
    if operation not in ('replace', 'drain') or any(
            type(n) is not int or not 0 < n < 2**64 for n in (session, generation)):
        raise ValueError('Invalid key operation/session/generation')
    bindings = tuple(bindings)
    if len(bindings) > CAPACITY or (operation == 'drain' and bindings):
        raise ValueError('Invalid key map length')
    tokens, keys = set(), set()
    packet = bytearray(SIZE)
    HEADER.pack_into(packet, 0, 1, 1 if operation == 'replace' else 2,
                     session, generation, len(bindings), 0, 0, 0)
    for index, binding in enumerate(bindings):
        if type(binding) is not tuple or len(binding) != 2:
            raise ValueError('Expected token/key pairs')
        token, key = binding
        if (type(token) is not int or not 0 < token < 2**32 or type(key) is not int or
                key not in VIRTUAL_KEYS.values() or token in tokens or key in keys):
            raise ValueError('Invalid or duplicate key binding')
        tokens.add(token); keys.add(key)
        BINDING.pack_into(packet, HEADER.size + index * BINDING.size, token, key)
    return bytes(packet)


def validate_request(packet):
    if type(packet) is not bytes or len(packet) != SIZE:
        raise ValueError('Invalid key packet')
    version, operation, session, generation, count, *_ = HEADER.unpack_from(packet)
    if version != 1 or operation not in (1, 2) or count > CAPACITY:
        raise ValueError('Invalid key request header')
    bindings = tuple(BINDING.unpack_from(packet, HEADER.size + i * BINDING.size) for i in range(count))
    if request('replace' if operation == 1 else 'drain', session, generation, bindings) != packet:
        raise ValueError('Key request contains unexpected fields')
    return operation


def decode(sent, encoded):
    operation = validate_request(sent)
    if type(encoded) is not str or len(encoded) != SIZE * 2:
        raise ValueError('Invalid key acknowledgement')
    received = bytes.fromhex(encoded)
    if len(received) != SIZE or received[:24] != sent[:24]:
        raise ValueError('Key acknowledgement changed request identity')
    _, _, _, _, count, dropped, error, reserved = HEADER.unpack_from(received)
    if reserved or error not in (0, 1, 2, 3) or count > CAPACITY:
        raise ValueError('Invalid key acknowledgement header')
    if error or operation == 1:
        expected = bytearray(sent)
        struct.pack_into('<I', expected, 32, error)
        if received != expected:
            raise ValueError('Key rejection/replacement changed request data')
        return error, 0, ()
    if any(received[HEADER.size + count * BINDING.size:]):
        raise ValueError('Key acknowledgement has nonzero unused events')
    events = tuple(BINDING.unpack_from(received, HEADER.size + i * BINDING.size) for i in range(count))
    if any(not token or key not in VIRTUAL_KEYS.values() for token, key in events):
        raise ValueError('Invalid native key event')
    return 0, dropped, events
