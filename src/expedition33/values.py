"""Identity-checked stored property observations; no getters, writes or GC pinning."""
from dataclasses import dataclass
from types import MappingProxyType

from . import RuntimeQueryError, _query


@dataclass(frozen=True)
class StoredValues:
    target: object
    values: object
    errors: object
    types: object
    truncated: frozenset = frozenset()


@dataclass(frozen=True)
class StoredArray:
    """Copied prefix plus observed total length, never a native allocation owner.

    Iteration visits only copied items. Indexing an uncopied position fails rather
    than silently fabricating a value or issuing another potentially stale read.
    """
    items: tuple
    length: int

    def __len__(self):
        return self.length

    def __iter__(self):
        return iter(self.items)

    def __getitem__(self, index):
        if type(index) is not int or not 0 <= index < len(self.items):
            raise IndexError('Array index is outside the copied observation prefix')
        return self.items[index]


@dataclass(frozen=True)
class StoredStruct:
    """Reflected field copies; opaque native state is neither owned nor reconstructed."""
    type_object: object
    fields: object
    errors: object
    types: object
    truncated: bool


class _StaleStruct(ValueError):
    pass


def _struct_type(catalog, metadata, prefix):
    obj = catalog.by_index.get(metadata[prefix + '_index'])
    if (obj is None or obj.serial != metadata[prefix + '_serial'] or obj.name != metadata[prefix + '_name']
            or (prefix + '_address' in metadata and obj.address != int(metadata[prefix + '_address'], 16))):
        raise _StaleStruct('Struct metadata reference changed since catalog; refresh required')
    return obj


def _struct_value(catalog, value, depth=0, budget=None):
    budget = [4096] if budget is None else budget
    budget[0] -= 1
    if depth >= 4 or budget[0] < 0:
        raise ValueError('Struct depth or node limit')
    if type(value) is not dict or set(value) != {'$struct'}:
        raise ValueError('Missing struct tag')
    payload = value['$struct']
    if type(payload) is not dict or set(payload) != {'type', 'fields', 'truncated'}:
        raise ValueError('Unexpected struct fields')
    def reference(raw):
        if type(raw) is not dict or set(raw) != {'index', 'serial', 'address', 'name'}:
            raise ValueError('Invalid struct reference')
        obj = catalog.by_index.get(raw['index'])
        if (obj is None or obj.serial != raw['serial'] or obj.address != int(raw['address'], 16)
                or obj.name != raw['name']):
            raise _StaleStruct('Struct reference changed since catalog; refresh required')
        return obj
    type_object = reference(payload['type'])
    rows = payload['fields']
    if type(rows) is not list or len(rows) > 64 or type(payload['truncated']) is not bool:
        raise ValueError('Invalid struct extent')
    fields, errors, types = {}, {}, {}
    for row in rows:
        budget[0] -= 1
        if budget[0] < 0 or type(row) is not dict or set(row) not in ({'name', 'type', 'value'}, {'name', 'type', 'error'}):
            raise ValueError('Invalid struct member')
        name, kind = row['name'], row['type']
        if type(name) is not str or not name or len(name) > 1024 or name in types or type(kind) is not str:
            raise ValueError('Invalid or duplicate struct member identity')
        types[name] = kind
        if 'error' in row:
            if type(row['error']) is not str or len(row['error']) > 1024:
                raise ValueError('Invalid struct member error')
            errors[name] = row['error']
            continue
        item = row['value']
        if kind == 'StructProperty':
            item = _struct_value(catalog, item, depth + 1, budget)
        elif kind == 'ObjectProperty':
            if item is not None:
                if type(item) is not dict or set(item) != {'$reference'}:
                    raise ValueError('Invalid struct object reference')
                item = reference(item['$reference'])
        elif kind in ('FloatProperty', 'DoubleProperty'):
            if type(item) not in (int, float) and not (type(item) is dict and set(item) == {'$float'} and item['$float'] in ('nan', 'inf', '-inf')):
                raise ValueError('Invalid struct float')
            item = float(item['$float']) if isinstance(item, dict) else float(item)
        elif kind == 'BoolProperty':
            if type(item) is not bool: raise ValueError('Invalid struct bool')
        elif kind == 'NameProperty':
            if type(item) is not str: raise ValueError('Invalid struct name')
        elif kind in ('ByteProperty', 'IntProperty', 'UInt16Property'):
            low, high = {'ByteProperty': (0, 255), 'IntProperty': (-2147483648, 2147483647), 'UInt16Property': (0, 65535)}[kind]
            if type(item) is not int or not low <= item <= high: raise ValueError('Invalid struct integer')
        else:
            raise ValueError('Unsupported struct member value')
        fields[name] = item
    return StoredStruct(type_object, MappingProxyType(fields), MappingProxyType(errors),
                        MappingProxyType(types), payload['truncated'])


def read_values(catalog, observed):
    obj = catalog.resolve(observed)
    start, rows = _query(['--read-values', str(catalog.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
    if start['pid'] != obj.pid:
        raise RuntimeQueryError('Value process changed')
    targets = [row for row in rows if row['event'] == 'object']
    if len(targets) != 1:
        raise RuntimeQueryError('Value target missing')
    target = targets[0]
    if (target['index'] != obj.index or target['serial'] != obj.serial or
            int(target['address'], 16) != obj.address or target['class_index'] != obj.class_index or target['name'] != obj.name):
        raise RuntimeQueryError('Value target identity changed')
    metadata, elements, errors, truncated = {}, {}, {}, set()
    for row in rows:
        kind = row['event']
        if kind == 'property_metadata':
            key = (row['owner_index'], row['name'])
            if key in metadata:
                raise RuntimeQueryError('Duplicate property identity')
            metadata[key] = row
        elif kind in ('stored_value', 'stored_bool', 'stored_value_error'):
            key = (row['owner_index'], row['name'])
            if key not in metadata:
                raise RuntimeQueryError('Stored value has no property metadata')
            if kind == 'stored_value_error':
                errors[key] = row['error']
                continue
            if kind == 'stored_bool':
                if (type(row['value']) is not bool or not 0 < row['mask'] <= 255 or
                        not 0 <= row['raw_byte'] <= 255 or bool(row['raw_byte'] & row['mask']) != row['value']):
                    raise RuntimeQueryError('Invalid boolean storage result')
            index = row['element']
            if not 0 <= index < metadata[key]['dimension'] or index in elements.get(key, {}):
                raise RuntimeQueryError('Invalid static array element')
            value = row['value']
            if row.get('truncated') is True:
                truncated.add(key)
            if metadata[key]['type'] == 'ArrayProperty':
                try:
                    if not isinstance(value, dict) or set(value) != {'$array'}:
                        raise ValueError('Missing array tag')
                    array = value['$array']
                    if set(array) != {'length', 'items'}:
                        raise ValueError('Unexpected array fields')
                    length, items = array['length'], array['items']
                    if (type(length) is not int or not 0 <= length <= 1048576 or type(items) is not list
                            or len(items) != min(length, 64) or row.get('truncated') is not (length > 64)):
                        raise ValueError('Invalid array extent or truncation')
                    element_type = metadata[key]['inner_type']
                    if element_type not in ('ObjectProperty', 'FloatProperty', 'DoubleProperty',
                                            'NameProperty', 'IntProperty', 'UInt16Property', 'ByteProperty', 'StructProperty'):
                        raise ValueError('Unsupported array element type')
                    struct_type = _struct_type(catalog, metadata[key], 'inner_struct') if element_type == 'StructProperty' else None
                    decoded = []
                    struct_budget = [4096]
                    for item in items:
                        if element_type == 'StructProperty':
                            item = _struct_value(catalog, item, budget=struct_budget)
                            if item.type_object != struct_type:
                                raise ValueError('Array struct type mismatch')
                        elif element_type == 'ObjectProperty':
                            if item is not None:
                                reference = item['$reference']
                                observed_ref = catalog.by_index.get(reference['index'])
                                if (observed_ref is None or observed_ref.serial != reference['serial'] or
                                        observed_ref.address != int(reference['address'], 16) or
                                        observed_ref.name != reference['name']):
                                    errors[key] = 'Array reference changed since catalog; refresh required'
                                item = observed_ref
                        elif element_type in ('FloatProperty', 'DoubleProperty'):
                            if type(item) not in (int, float) and not (isinstance(item, dict) and
                                    set(item) == {'$float'} and item['$float'] in ('nan', 'inf', '-inf')):
                                raise ValueError('Invalid floating array item')
                            item = float(item['$float']) if isinstance(item, dict) else float(item)
                        elif element_type == 'NameProperty':
                            if type(item) is not str:
                                raise ValueError('Invalid name array item')
                        elif element_type in ('IntProperty', 'UInt16Property', 'ByteProperty'):
                            lower, upper = {'IntProperty': (-2147483648, 2147483647),
                                            'UInt16Property': (0, 65535), 'ByteProperty': (0, 255)}[element_type]
                            if type(item) is not int or not lower <= item <= upper:
                                raise ValueError('Invalid integer array item')
                        else:
                            raise ValueError('Unsupported array element type')
                        decoded.append(item)
                    value = StoredArray(tuple(decoded), length)
                except _StaleStruct as error:
                    errors[key] = str(error)
                except (KeyError, ValueError, TypeError, OverflowError) as error:
                    raise RuntimeQueryError(f'Invalid array observation: {error}') from error
            if metadata[key]['type'] == 'StructProperty':
                try:
                    value = _struct_value(catalog, value)
                    if value.type_object != _struct_type(catalog, metadata[key], 'struct'):
                        raise ValueError('Struct type mismatch')
                except _StaleStruct as error:
                    errors[key] = str(error)
                except (KeyError, ValueError, TypeError, OverflowError) as error:
                    raise RuntimeQueryError(f'Invalid struct observation: {error}') from error
            if metadata[key]['type'] in ('FloatProperty', 'DoubleProperty') and type(value) in (int, float):
                value = float(value)
            if isinstance(value, dict) and '$reference' in value:
                reference = value['$reference']
                observed_ref = catalog.by_index.get(reference['index'])
                if (observed_ref is None or observed_ref.serial != reference['serial'] or
                        observed_ref.address != int(reference['address'], 16) or observed_ref.name != reference['name']):
                    errors[key] = 'Reference changed since catalog; refresh required'
                value = observed_ref
            elif isinstance(value, dict) and '$float' in value:
                value = float(value['$float'])
            elements.setdefault(key, {})[index] = value
        elif kind not in ('object', 'struct_metadata'):
            raise RuntimeQueryError('Unexpected stored-value event')
    values = {}
    for key, meta in metadata.items():
        if key in errors:
            continue
        entries = elements.get(key, {})
        if len(entries) != meta['dimension']:
            errors[key] = f"Stored {meta['type']} conversion is not implemented or observation is incomplete"
            continue
        sequence = tuple(entries[i] for i in range(meta['dimension']))
        values[key] = sequence[0] if meta['dimension'] == 1 else sequence
    return StoredValues(obj, MappingProxyType(values), MappingProxyType(errors),
                        MappingProxyType({key: meta['type'] for key, meta in metadata.items()}), frozenset(truncated))
