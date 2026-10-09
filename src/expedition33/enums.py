"""Copied, build-verified native UEnum members; no callable or pinned handles."""
from dataclasses import dataclass
from types import MappingProxyType

from . import RuntimeQueryError, _query
from .catalog import CatalogObject


@dataclass(frozen=True)
class EnumMember:
    name: str
    value: int


@dataclass(frozen=True)
class EnumDescriptor:
    object: CatalogObject
    members: tuple[EnumMember, ...]


def describe_enums(catalog, observed):
    """Read native UEnum members selected by catalog identity.

    Values may alias and may include sentinels such as _MAX. Membership does not
    prove a valid function argument. Native subclasses are currently unsupported.
    Double-read checks detect changes; they do not provide an atomic GC snapshot.
    """
    targets = tuple(catalog.resolve(obj) for obj in observed)
    if len(targets) > 1024 or len({obj.index for obj in targets}) != len(targets):
        raise ValueError('Expected at most 1024 distinct enum identities')
    results = {}
    for offset in range(0, len(targets), 128):
        batch = targets[offset:offset + 128]
        selectors = ','.join(f'{obj.index}:{obj.serial}:{obj.address:x}' for obj in batch)
        start, rows = _query(['--describe-enums', str(catalog.pid), selectors])
        expected = {obj.index: obj for obj in batch}
        current = None
        received = set()
        try:
            if start['pid'] != catalog.pid:
                raise ValueError('Enum process changed')
            for row in rows:
                if row['event'] == 'object':
                    if current is not None:
                        raise ValueError('Missing enum metadata')
                    obj = expected[row['index']]
                    if (obj.index in received or row['serial'] != obj.serial or
                            int(row['address'], 16) != obj.address or row['name'] != obj.name or
                            row['class_index'] != obj.class_index):
                        raise ValueError('Enum identity changed or duplicated')
                    current = obj
                elif row['event'] == 'enum_metadata':
                    if current is None or row['index'] != current.index:
                        raise ValueError('Enum metadata owner mismatch')
                    members = row['members']
                    if not isinstance(members, list) or len(members) > 65536:
                        raise ValueError('Invalid enum member list')
                    names, decoded = set(), []
                    for member in members:
                        name, value = member['name'], member['value']
                        if (not isinstance(name, str) or not name or name in names or
                                type(value) is not int or not -(1 << 63) <= value < (1 << 63)):
                            raise ValueError('Invalid enum member')
                        names.add(name)
                        decoded.append(EnumMember(name, value))
                    results[current.index] = EnumDescriptor(current, tuple(decoded))
                    received.add(current.index)
                    current = None
                else:
                    raise ValueError('Unexpected enum event')
            if current is not None or received != set(expected):
                raise ValueError('Enum result set incomplete')
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeQueryError(f'Invalid enum response: {error}') from error
    return MappingProxyType(results)
