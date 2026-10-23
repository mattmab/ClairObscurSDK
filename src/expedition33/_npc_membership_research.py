"""Read-only five-location NPC membership observation; no spawn authority."""
import secrets
import struct

SIZE = 20984
FIELDS = ('InteractiveObjects', 'DistantInteractiveObjects', 'DisplayedDistantInteractiveObjects', 'ActiveInteraction', '2DInteraction')


def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('NPC membership packet size')
    version, op, error, state, owner = struct.unpack_from('<4IQ', data)
    if (version, op, error, state) != (3, 135, 0, 0) or not owner or any(data[24:88]) or any(data[136:]):
        raise ValueError('NPC membership packet header/padding')
    for at in (88, 104, 120):
        index, serial, address = struct.unpack_from('<iiQ', data, at)
        if index < 0 or serial <= 0 or address < 0x10000:
            raise ValueError('Stabilized exact membership identity required')


def request(scope, identities):
    scope._check()
    cap = getattr(scope._session._transport, 'npc_membership_observation_research_protocol', 0)
    if type(cap) is not int or cap != 1:
        raise RuntimeError('NPC membership observation unavailable')
    if len(identities) != 3:
        raise ValueError('Expected exact system, controller and observed actor')
    packet = bytearray(SIZE)
    struct.pack_into('<4IQ', packet, 0, 3, 135, 0, 0, secrets.randbits(64) or 1)
    for n, obj in enumerate(identities):
        struct.pack_into('<iiQ', packet, 88 + 16 * n, obj.index, obj.serial, obj.address)
    validate_request(bytes(packet))
    with scope._lease_context():
        reply = scope._session._transport.command('mesh', bytes(packet))
    raw = bytes.fromhex(reply['mesh_packet'])
    if len(raw) != SIZE:
        raise RuntimeError('NPC membership acknowledgement size')
    compare = bytearray(raw)
    compare[8:16] = packet[8:16]
    compare[4096:4152] = packet[4096:4152]
    if compare != packet:
        raise RuntimeError('NPC membership acknowledgement changed immutable data')
    error, state = struct.unpack_from('<II', raw, 8)
    if error:
        if state or any(raw[4096:4152]):
            raise RuntimeError('Rejected NPC membership has success data')
        return dict(observed=False, native_error=error, actors_spawned=0)
    if state != 1:
        raise RuntimeError('NPC membership acknowledgement incomplete')
    values = struct.unpack_from('<10I2Q', raw, 4096)
    totals, owned = values[:5], values[5:10]
    if any(n > t for n, t in zip(owned, totals)) or any(t > 8192 for t in totals) or any(t > 1 for t in totals[3:]):
        raise RuntimeError('Invalid membership counts')
    obj, pointer = values[10:]
    expected = identities[2].address
    if bool(sum(owned)) != bool(obj) or (obj and obj != expected) or (not obj and pointer):
        raise RuntimeError('Invalid exact owned interface acknowledgement')
    return dict(observed=True, totals=dict(zip(FIELDS, totals)), owned=dict(zip(FIELDS, owned)),
                interface_pair=[obj, pointer], actors_spawned=0)
