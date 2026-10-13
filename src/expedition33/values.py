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


@dataclass(frozen=True)
class StoredMap:
    """Complete copied supported map; never a native allocation owner."""
    items: object


@dataclass(frozen=True)
class StoredMapEntries:
    """Copied pairs for reflected struct keys, which are not Python hash keys."""
    entries: tuple


def _map_value(metadata, value, catalog=None):
    kinds = metadata.get('map_key_type'), metadata.get('map_value_type')
    if kinds not in (('NameProperty', 'BoolProperty'), ('ByteProperty', 'StructProperty'),
                     ('NameProperty', 'StructProperty'), ('ByteProperty', 'DoubleProperty'), ('ByteProperty', 'IntProperty'),
                     ('NameProperty', 'ObjectProperty'), ('StructProperty', 'ObjectProperty'), ('StructProperty', 'StructProperty')):
        raise ValueError('Unsupported map element types')
    struct_key, struct_value = kinds[0] == 'StructProperty', kinds[1] == 'StructProperty'
    if (struct_key or struct_value or kinds[1] == 'ObjectProperty') and catalog is None:
        raise ValueError('Struct maps require an identity catalog')
    expected = _struct_type(catalog, metadata, 'map_value_struct') if struct_value else None
    expected_key = _struct_type(catalog, metadata, 'map_key_struct') if struct_key else None
    if type(value) is not dict or set(value) != {'$map'}:
        raise ValueError('Missing map tag')
    payload = value['$map']
    if type(payload) is not dict or set(payload) != {'length', 'items'}:
        raise ValueError('Unexpected map fields')
    length, items = payload['length'], payload['items']
    if type(length) is not int or not 0 <= length <= 4096 or type(items) is not list or len(items) != length:
        raise ValueError('Invalid map extent')
    result, pairs, seen = {}, [], set()
    budget = [4096]
    for pair in items:
        if type(pair) is not list or len(pair) != 2:
            raise ValueError('Invalid or duplicate map entry')
        key, entry = pair
        if kinds[0] == 'ByteProperty':
            if type(key) is not int or not 0 <= key <= 255:
                raise ValueError('Invalid byte map key')
            key_token = key
        elif struct_key:
            key = _struct_value(catalog, key, budget=budget)
            if key.type_object != expected_key or key.errors or key.truncated:
                raise ValueError('Invalid or incomplete map struct key')
            if any(type(v) not in (str, int, bool) for v in key.fields.values()):
                raise ValueError('Unsupported map struct key member')
            key_token = tuple(sorted((name, type(v).__name__, v) for name, v in key.fields.items()))
        else:
            if type(key) is not str or not key or len(key) > 1024:
                raise ValueError('Invalid name map key')
            key_token = key
        if struct_value:
            entry = _struct_value(catalog, entry, budget=budget)
            if entry.type_object != expected:
                raise ValueError('Map struct type mismatch')
        elif kinds[1] == 'BoolProperty':
            if type(entry) is not bool:
                raise ValueError('Invalid map entry')
        elif kinds[1] == 'IntProperty':
            if type(entry) is not int or not -2147483648 <= entry <= 2147483647:
                raise ValueError('Invalid map integer value')
        elif kinds[1] == 'DoubleProperty':
            if type(entry) in (int, float):
                entry = float(entry)
            elif isinstance(entry, dict) and set(entry) == {'$float'} and entry['$float'] in ('nan', 'inf', '-inf'):
                entry = float(entry['$float'])
            else:
                raise ValueError('Invalid map double value')
        elif entry is not None:
            if type(entry) is not dict or set(entry) != {'$reference'}:
                raise ValueError('Invalid map object reference')
            raw = entry['$reference']
            if type(raw) is not dict or set(raw) != {'index', 'serial', 'address', 'name'}:
                raise ValueError('Invalid map object reference')
            entry = catalog.by_index.get(raw['index'])
            if (entry is None or entry.serial != raw['serial'] or entry.address != int(raw['address'], 16)
                    or entry.name != raw['name']):
                raise _StaleStruct('Map object reference changed since catalog; refresh required')
        if key_token in seen:
            raise ValueError('Duplicate map entry')
        seen.add(key_token)
        if struct_key:
            pairs.append((key, entry))
        else:
            result[key] = entry
    if struct_key:
        return StoredMapEntries(tuple(pairs))
    return StoredMap(MappingProxyType(result))


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
        elif kind in ('ObjectProperty', 'ClassProperty'):
            if item is not None:
                if type(item) is not dict or set(item) != {'$reference'}:
                    raise ValueError('Invalid struct object reference')
                item = reference(item['$reference'])
                if kind == 'ClassProperty' and item.index not in catalog.classes:
                    raise ValueError('Struct class reference is not a reflected class')
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
    return _decode_values(catalog, obj, start, rows)


def read_table_rows(catalog, observed):
    """Read up to 256 DataTable rows through the ordinary reflected decoder.

    Native storage, accessor, row schema and table identity are verified afresh.
    No addresses are accepted for individual rows and nothing is invoked.
    """
    obj = catalog.resolve(observed)
    if obj.class_name not in ('DataTable', 'CompositeDataTable'):
        raise ValueError('Expected a DataTable observation')
    start, rows = _query(['--read-table', str(catalog.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
    targets = [row for row in rows if row['event'] == 'object']
    if len(targets) != 1:
        raise RuntimeQueryError('Table target missing or ambiguous')
    # Validate even an empty table's identity.
    _decode_values(catalog, obj, start, targets)
    groups, current = {}, None
    for row in rows:
        if row['event'] == 'table_row':
            current = row.get('name')
            if type(current) is not str or not current or current in groups or len(groups) >= 4096:
                raise RuntimeQueryError('Invalid table row identity')
            groups[current] = list(targets)
        elif current is not None and row['event'] != 'object':
            groups[current].append(row)
    return {name: _decode_values(catalog, obj, start, group) for name, group in groups.items()}


def read_values_many(catalog, observed, *, fields=None):
    """Read fresh values for up to 1023 identities in one bounded request.

    Optional named-field projection avoids reading unrelated complex values.
    Each object is independently identity-validated by the native reader and
    existing decoder; the result is an observation, not an atomic snapshot.
    """
    objects = tuple(catalog.resolve(obj) for obj in observed)
    if not objects:
        return {}
    if len(objects) > 1023 or len({obj.index for obj in objects}) != len(objects):
        raise ValueError('Read batch requires unique identities within limit')
    selector = ','.join(f'{obj.index}:{obj.serial}:{obj.address:x}' for obj in objects)
    if fields is not None:
        fields = tuple(fields)
        if not 1 <= len(fields) <= 64 or len(set(fields)) != len(fields) or any(
            type(name) is not str or not 1 <= len(name) <= 256 or any(ch in name for ch in ';|\r\n\t\0') for name in fields):
            raise ValueError('Invalid stored-value field projection')
        selector += ';' + '|'.join(fields)
    start, rows = _query(['--read-values', str(catalog.pid), selector])
    requested = {obj.index: obj for obj in objects}
    groups, current = {}, None
    for row in rows:
        if row['event'] == 'object':
            current = row['index']
            if current not in requested or current in groups:
                raise RuntimeQueryError('Unexpected value batch identity')
            groups[current] = []
        if current is not None:
            groups[current].append(row)
    if set(groups) != set(requested):
        raise RuntimeQueryError('Incomplete value batch')
    return {index: _decode_values(catalog, requested[index], start, group) for index, group in groups.items()}


def read_values_with_references(catalog, observed, *, fields=None):
    """Read stored values and capture missing structured reference closures.

    The initial decoder validates the response before its reference identities
    are used. The selected reader validates every newly observed identity; the
    same response is then decoded against that extended catalog. No retries or
    fabricated identities, and no global object enumeration.
    """
    from .catalog import capture_selected
    obj = catalog.resolve(observed)
    selector = f'{obj.index}:{obj.serial}:{obj.address:x}'
    if fields is not None:
        fields = tuple(fields)
        if not 1 <= len(fields) <= 64 or len(set(fields)) != len(fields) or any(
            type(name) is not str or not 1 <= len(name) <= 256 or any(ch in name for ch in ';|\r\n\t\0') for name in fields):
            raise ValueError('Invalid stored-value field projection')
        selector += ';' + '|'.join(fields)
    start, rows = _query(['--read-values', str(catalog.pid), selector])
    result = _decode_values(catalog, obj, start, rows)
    missing = set()
    def reference(raw):
        if type(raw) is not dict or set(raw) != {'index', 'serial', 'address', 'name'}:
            raise RuntimeQueryError('Invalid nested stored reference')
        identity = (raw['index'], raw['serial'], int(raw['address'], 16))
        current = catalog.by_index.get(raw['index'])
        if current is None or (current.index, current.serial, current.address) != identity:
            missing.add(identity)
        if len(missing) > 1023:
            raise RuntimeQueryError('Nested stored reference limit')
    def walk(value, depth=0):
        if depth > 16:
            raise RuntimeQueryError('Nested stored reference depth')
        if isinstance(value, dict):
            if '$reference' in value:
                reference(value['$reference'])
            if '$struct' in value:
                reference(value['$struct']['type'])
            for child in value.values(): walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value: walk(child, depth + 1)
    for row in rows:
        if row.get('event') == 'stored_value': walk(row.get('value'))
    if missing:
        fresh = capture_selected(catalog.pid, ((obj.index, obj.serial, obj.address), *sorted(missing)))
        catalog = catalog.with_observations(fresh)
        result = _decode_values(catalog, catalog.resolve(obj), start, rows)
    return result, catalog


def read_object_reference(catalog, observed, owner, name, *, project=False):
    """Observe one direct object property and its fresh dependency closure.

    Returns (reference_or_none, extended_catalog). No full enumeration, property
    retry or fabricated object occurs. This is an observation, not a GC lease or
    a guarantee that the property will still have this value at later dispatch.
    """
    from .catalog import capture_selected
    obj, owner = catalog.resolve(observed), catalog.resolve(owner)
    selector = f'{obj.index}:{obj.serial}:{obj.address:x}'
    if type(project) is not bool:
        raise ValueError('Reference projection must be bool')
    if project:
        if type(name) is not str or not 1 <= len(name) <= 256 or any(ch in name for ch in ';|\r\n\t\0'):
            raise ValueError('Invalid reference field projection')
        selector += ';' + name
    start, rows = _query(['--read-values', str(catalog.pid), selector])
    # Validate the complete original response before using an observed selector.
    _decode_values(catalog, obj, start, rows)
    key = (owner.index, name)
    fields = [r for r in rows if r['event'] == 'property_metadata' and
              (r['owner_index'], r['name']) == key]
    entries = [r for r in rows if r['event'] in ('stored_value', 'stored_value_error') and
               (r['owner_index'], r['name']) == key]
    if (len(fields) != 1 or fields[0]['type'] not in ('ObjectProperty', 'ClassProperty') or fields[0]['dimension'] != 1 or
            len(entries) != 1 or entries[0]['event'] != 'stored_value' or entries[0]['element'] != 0):
        raise RuntimeQueryError('Expected one readable scalar object property')
    value = entries[0]['value']
    if value is None:
        return None, catalog
    try:
        if type(value) is not dict or set(value) != {'$reference'}:
            raise ValueError('Expected object reference')
        ref = value['$reference']
        if type(ref) is not dict or set(ref) != {'index', 'serial', 'address', 'name'}:
            raise ValueError('Invalid reference fields')
        identity = (ref['index'], ref['serial'], int(ref['address'], 16))
        target_identity = (obj.index, obj.serial, obj.address)
        identities = (target_identity,) if identity == target_identity else (target_identity, identity)
        fresh = capture_selected(catalog.pid, identities)
        combined = catalog.with_observations(fresh)
        result = _decode_values(combined, combined.resolve(obj), start, rows)
        if key not in result.values:
            raise RuntimeQueryError('Object property reference changed during observation')
        return result.values[key], combined
    except (KeyError, ValueError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid object property reference: {error}') from error


def _decode_values(catalog, obj, start, rows):
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
            if metadata[key]['type'] == 'MapProperty':
                try:
                    if row.get('truncated', False):
                        raise ValueError('Partial maps are unsupported')
                    value = _map_value(metadata[key], value, catalog)
                except _StaleStruct as error:
                    errors[key] = str(error)
                except (KeyError, ValueError, TypeError) as error:
                    raise RuntimeQueryError(f'Invalid map observation: {error}') from error
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
                    if element_type not in ('ObjectProperty', 'ClassProperty', 'FloatProperty', 'DoubleProperty',
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
                        elif element_type in ('ObjectProperty', 'ClassProperty'):
                            if item is not None:
                                reference = item['$reference']
                                observed_ref = catalog.by_index.get(reference['index'])
                                if (observed_ref is None or observed_ref.serial != reference['serial'] or
                                        observed_ref.address != int(reference['address'], 16) or
                                        observed_ref.name != reference['name']):
                                    errors[key] = 'Array reference changed since catalog; refresh required'
                                item = observed_ref
                                if item is not None and element_type == 'ClassProperty' and item.index not in catalog.classes:
                                    raise ValueError('Class array item is not a class descriptor')
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


