"""Durable native ownership for one explicitly planned object reference."""
import secrets
import struct
from . import _assignment_wire as wire
from .reflection import describe

HEADER = struct.Struct('<IIQQII')
SIZE = HEADER.size + wire.SIZE


def validate_request(data):
    if type(data) is not bytes or len(data) != SIZE:
        raise ValueError('Scoped assignment size')
    version, op, owner, reserved, error, state = HEADER.unpack_from(data)
    if version != 1 or op not in (1, 2, 3) or not owner or reserved or error or state:
        raise ValueError('Scoped assignment header')
    if op != 1 and any(data[HEADER.size:]):
        raise ValueError('Unexpected scoped assignment payload')


class NativeScopedAssignment:
    def __init__(self, scope):
        self.scope = scope
        self.owner = secrets.randbits(64) or 1
        self.state = 'new'
        scope._reference_owners.append(self)

    def _send(self, op, assignment=None):
        self.scope._session._check()
        if self.state == 'unknown':
            raise RuntimeError('Unknown scoped assignment outcome')
        request = HEADER.pack(1, op, self.owner, 0, 0, 0) + (assignment or bytes(wire.SIZE))
        validate_request(request)
        self.state = 'unknown'
        try:
            reply = self.scope._session._transport.command('scoped-assignment', request)
            data = bytes.fromhex(reply['scoped_assignment_packet'])
            if len(data) != SIZE or data[:24] != request[:24] or data[32:] != request[32:]:
                raise ValueError('Scoped assignment acknowledgement mismatch')
            error, state = HEADER.unpack_from(data)[4:]
            if error == 407 and state == 1:
                self.state = 'armed'
                return False
            if error or state not in (0, 1):
                raise RuntimeError(f'Native scoped assignment rejected ({error}, {state})')
            self.state = 'armed' if state else 'closed'
            return True
        except BaseException:
            self.scope._session._abort_ownership()
            raise

    def open(self, catalog, target, owner, name, expected, value):
        self.scope._check()
        if self.state != 'new':
            raise RuntimeError('Scoped assignment already used')
        target, owner, expected, value = (catalog.resolve(o) for o in (target, owner, expected, value))
        if catalog.pid != self.scope.pid or owner.index not in catalog.ancestors(target.class_index):
            raise ValueError('Scoped assignment target ancestry/session mismatch')
        props = [p for p in describe(catalog, (owner,))[owner.index].properties
                 if p['owner_index'] == owner.index and p['name'] == name]
        if len(props) != 1:
            raise ValueError('Expected one declared object property')
        prop = props[0]
        if (prop['type'] != 'ObjectProperty' or prop['element_size'] != 8 or
                prop['dimension'] != 1 or int(prop['vtable_rva'], 16) != 0x6e11d38):
            raise ValueError('Unsupported scoped reference layout')
        constraint = catalog.by_index[prop['property_class_index']]
        if constraint.index not in catalog.ancestors(value.class_index):
            raise ValueError('Replacement does not satisfy the property class')
        leases = [self.scope.retain(o) for o in (target, expected, value)]
        request = wire.request(target, owner, constraint, expected, value, prop, 0,
                               tuple(lease._token for lease in leases))
        return self._send(1, request)

    def status(self):
        self._send(3)
        return self.state

    def close(self):
        if self.state in ('new', 'closed'):
            return True
        return self._send(2)
