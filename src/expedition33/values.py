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
    metadata, elements, errors = {}, {}, {}
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
            if metadata[key]['type'] == 'FloatProperty' and type(value) in (int, float):
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
                        MappingProxyType({key: meta['type'] for key, meta in metadata.items()}))
