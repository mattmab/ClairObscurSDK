"""Build-specific owned ObjectProperty assignment; no automatic retry."""
import struct

SIZE = 232
IDENTITY = struct.Struct('<iiQ')


def request(target, owner, constraint, expected, value, metadata, element, tokens):
    packet = bytearray(SIZE)
    struct.pack_into('<II3Q', packet, 0, 1, 0, *tokens)
    for i, obj in enumerate((target, owner, constraint, expected, value)):
        identity = (-1, 0, 0) if obj is None else (obj.index, obj.serial, obj.address)
        IDENTITY.pack_into(packet, 32 + i * 16, *identity)
    name = metadata['name'].encode('ascii')
    if not 0 < len(name) < 96 or b'\0' in name:
        raise ValueError('Invalid property name')
    struct.pack_into('<Q3I96sI', packet, 112, metadata['flags'], metadata['offset'],
                     metadata['dimension'], element, name, 0)
    return bytes(packet)


def decode(sent, encoded):
    if type(sent) is not bytes or len(sent) != SIZE or type(encoded) is not str or len(encoded) != SIZE * 2:
        raise ValueError('Invalid assignment acknowledgement size')
    received = bytes.fromhex(encoded)
    if len(received) != SIZE or received[:4] != sent[:4] or received[8:228] != sent[8:228]:
        raise ValueError('Assignment acknowledgement changed the request')
    error = struct.unpack_from('<I', received, 4)[0]
    outcome = struct.unpack_from('<I', received, 228)[0]
    if (error not in range(8) or outcome not in (0, 1, 2) or
            (error == 0 and outcome != 1) or (error in (1, 2, 3, 4, 6, 7) and outcome != 0) or
            (error == 5 and outcome != 2)):
        raise ValueError('Inconsistent assignment acknowledgement')
    return error, ('not_dispatched', 'dispatch_returned', 'unknown')[outcome]
