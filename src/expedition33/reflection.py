"""Identity-selected, batched live UStruct metadata (including generated classes)."""
from dataclasses import dataclass
from types import MappingProxyType

from . import RuntimeQueryError, _query
from .catalog import CatalogObject


@dataclass(frozen=True)
class StructDescriptor:
    object: CatalogObject
    owners: tuple
    properties: tuple
    function: object


def describe(catalog, observed):
    """Describe up to 1024 observed UStructs after native identity/type validation.

    Arguments are CatalogObject observations, not arbitrary addresses. The native
    reader independently checks the current process, slots, serials, addresses,
    UStruct ancestry, field ownership and property extents before returning data.
    This remains an external observation, without GC pinning or callable handles.
    """
    targets = tuple(catalog.resolve(obj) for obj in observed)
    if len(targets) > 1024 or len({obj.index for obj in targets}) != len(targets):
        raise ValueError('Expected at most 1024 distinct descriptor identities')
    results = {}
    for offset in range(0, len(targets), 128):
        batch = targets[offset:offset + 128]
        selectors = ','.join(f'{obj.index}:{obj.serial}:{obj.address:x}' for obj in batch)
        start, rows = _query(['--describe', str(catalog.pid), selectors])
        if start['pid'] != catalog.pid:
            raise RuntimeQueryError('Descriptor process changed')
        expected = {obj.index: obj for obj in batch}
        grouped = {}
        current = None
        try:
            for row in rows:
                kind = row['event']
                if kind == 'object':
                    obj = expected[row['index']]
                    if (row['serial'] != obj.serial or int(row['address'], 16) != obj.address or
                        row['name'] != obj.name or row['class_index'] != obj.class_index):
                        raise ValueError('Descriptor identity changed')
                    current = {'object': obj, 'owners': [], 'properties': [], 'function': None}
                    if obj.index in grouped:
                        raise ValueError('Duplicate descriptor')
                    grouped[obj.index] = current
                elif current is None:
                    raise ValueError('Metadata precedes descriptor identity')
                elif kind == 'struct_metadata':
                    owner = catalog.by_index[row['index']]
                    if (owner.serial != row['serial'] or owner.address != int(row['address'], 16)
                            or owner.name != row['name']):
                        raise ValueError('Reflected owner changed since catalog')
                    current['owners'].append(MappingProxyType(dict(row)))
                elif kind == 'property_metadata':
                    for kind_name in ('struct', 'enum', 'property_class', 'meta_class', 'signature_function',
                                      'inner_struct', 'inner_enum', 'inner_property_class', 'inner_meta_class'):
                        if kind_name + '_index' in row:
                            reference = catalog.by_index[row[kind_name + '_index']]
                            if (reference.serial != row[kind_name + '_serial'] or
                                    reference.name != row[kind_name + '_name'] or
                                    (kind_name + '_address' in row and
                                     reference.address != int(row[kind_name + '_address'], 16))):
                                raise ValueError('Property type changed since catalog')
                    row = dict(row, flags=int(row['flags'], 16))
                    current['properties'].append(MappingProxyType(row))
                elif kind == 'function_metadata':
                    if current['function'] is not None:
                        raise ValueError('Duplicate function metadata')
                    current['function'] = MappingProxyType(dict(row, flags=int(row['flags'], 16)))
                else:
                    raise ValueError('Unexpected descriptor event')
            if set(grouped) != set(expected):
                raise ValueError('Descriptor set incomplete')
            for index, group in grouped.items():
                if not group['owners'] or group['owners'][0]['index'] != index:
                    raise ValueError('Descriptor owner missing')
                results[index] = StructDescriptor(group['object'], tuple(group['owners']),
                    tuple(group['properties']), group['function'])
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeQueryError(f'Invalid descriptor response: {error}') from error
    return MappingProxyType(results)
