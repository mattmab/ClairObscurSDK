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
                                            'NameProperty', 'IntProperty', 'UInt16Property', 'ByteProperty'):
                        raise ValueError('Unsupported array element type')
                    decoded = []
                    for item in items:
                        if element_type == 'ObjectProperty':
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
                except (KeyError, ValueError, TypeError, OverflowError) as error:
                    raise RuntimeQueryError(f'Invalid array observation: {error}') from error
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
