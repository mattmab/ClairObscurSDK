"""Identity-checked stored property observations; no getters, writes or GC pinning."""
from dataclasses import dataclass
from types import MappingProxyType
import re
import time

from . import RuntimeQueryError, _query

# Matches the native reader's per-value allowance for large cinematic casts.
# Depth, array length, field extent and identity validation remain independent.
_STRUCT_NODE_BUDGET = 32768


def _array_prefix_limits(catalog, owner_index, field, element_type, struct_type):
    limits = (64, 256)
    cast_types = {'Spawnables': 'MovieSceneSpawnable',
                  'Possessables': 'MovieScenePossessable',
                  'ObjectBindings': 'MovieSceneBinding'}
    expected = cast_types.get(field)
    owner = catalog.by_index.get(owner_index)
    if (expected and element_type == 'StructProperty' and owner is not None and
            struct_type is not None and
            catalog.path_name(owner) == '/Script/MovieScene.MovieScene' and
            catalog.path_name(struct_type) == '/Script/MovieScene.' + expected):
        return limits + (4096,)
    return limits


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
    native: object = None


@dataclass(frozen=True)
class StoredFrameRange:
    """Build-qualified pointer-free endpoints; open bounds have no value."""
    lower_kind: str
    lower: int | None
    upper_kind: str
    upper: int | None

    def __post_init__(self):
        for kind,value in ((self.lower_kind,self.lower),(self.upper_kind,self.upper)):
            if kind not in ('exclusive','inclusive','open') or (value is not None if kind=='open' else
                    type(value) is not int or not -(1<<31)<=value<(1<<31)):
                raise ValueError('Invalid frame range endpoint')

    @property
    def start(self):return None if self.lower is None else self.lower+int(self.lower_kind=='exclusive')
    @property
    def end(self):return None if self.upper is None else self.upper+int(self.upper_kind=='inclusive')


@dataclass(frozen=True)
class StoredMap:
    """Complete copied supported map; never a native allocation owner."""
    items: object


@dataclass(frozen=True)
class StoredMapEntries:
    """Copied pairs for reflected struct keys, which are not Python hash keys."""
    entries: tuple


@dataclass(frozen=True)
class StoredSoftObjectPath:
    """Copied stored soft path; no resolution, loading, weak cache or ownership."""
    package: str | None
    asset: str | None
    subpath: str

    def __post_init__(self):
        if type(self.subpath) is not str or len(self.subpath)>4096 or '\0' in self.subpath:
            raise ValueError('Invalid stored soft object subpath')
        try:
            encoded=self.subpath.encode('utf-16-le')
        except UnicodeError:
            raise ValueError('Invalid stored soft object UTF16') from None
        if len(encoded)>8192:
            raise ValueError('Stored soft object subpath exceeds UTF16 limit')
        if self.package is None or self.asset is None:
            if self.package is not None or self.asset is not None or self.subpath:
                raise ValueError('Null soft object path requires no package, asset or subpath')
        elif (type(self.package) is not str or type(self.asset) is not str or
              len(self.package)>1024 or len(self.asset)>1024 or
              re.fullmatch(r'/[A-Za-z0-9_]+(?:/[A-Za-z0-9_]+)*',self.package) is None or
              re.fullmatch(r'[A-Za-z0-9_]+',self.asset) is None):
            raise ValueError('Invalid stored soft object package or asset')

    @property
    def path(self):
        return None if self.package is None else self.package+'.'+self.asset+(':'+self.subpath if self.subpath else '')


def _soft_object_path(value):
    if type(value) is not dict or set(value)!={'$soft_object_path'}:
        raise ValueError('Missing stored soft object path tag')
    payload=value['$soft_object_path']
    if type(payload) is not dict or set(payload)!={'package','asset','subpath'}:
        raise ValueError('Invalid stored soft object path fields')
    return StoredSoftObjectPath(**payload)


def _map_value(metadata, value, catalog=None):
    kinds = metadata.get('map_key_type'), metadata.get('map_value_type')
    if kinds not in (('NameProperty', 'BoolProperty'), ('NameProperty', 'ByteProperty'), ('ByteProperty', 'StructProperty'),
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
    budget = [_STRUCT_NODE_BUDGET]
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
        elif kinds[1] == 'ByteProperty':
            if type(entry) is not int or not 0 <= entry <= 255:
                raise ValueError('Invalid map byte value')
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
    budget = [_STRUCT_NODE_BUDGET] if budget is None else budget
    budget[0] -= 1
    if depth >= 4 or budget[0] < 0:
        raise ValueError('Struct depth or node limit')
    if type(value) is not dict or set(value) != {'$struct'}:
        raise ValueError('Missing struct tag')
    payload = value['$struct']
    if type(payload) is not dict or set(payload) not in ({'type', 'fields', 'truncated'}, {'type', 'fields', 'truncated', 'native'}):
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
        if budget[0] < 0 or type(row) is not dict or set(row) not in ({'name', 'type', 'value'}, {'name', 'type', 'error'}, {'name', 'type', 'value', 'inner_type'}, {'name', 'type', 'value', 'inner_type', 'inner_struct'}, {'name', 'type', 'value', 'map_key_type', 'map_value_type'}):
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
        if kind == 'ArrayProperty':
            element_kind=row.get('inner_type')
            expected_fields={'name','type','value','inner_type'}|({'inner_struct'} if element_kind=='StructProperty' else set())
            if set(row)!=expected_fields or element_kind not in ('ObjectProperty','ClassProperty','StructProperty',
                    'BoolProperty','FloatProperty','DoubleProperty','IntProperty','UInt16Property','ByteProperty','NameProperty'):
                raise ValueError('Unsupported nested array schema')
            expected=None
            if element_kind=='StructProperty':
                if type(row['inner_struct']) is not dict or set(row['inner_struct'])!={'$reference'}:
                    raise ValueError('Invalid nested array struct identity')
                expected=reference(row['inner_struct']['$reference'])
                if expected.class_name!='ScriptStruct':raise ValueError('Nested array type is not a ScriptStruct')
            if type(item) is not dict or set(item)!={'$array'}:raise ValueError('Missing nested array tag')
            array=item['$array']
            if (type(array) is not dict or set(array)!={'length','items'} or type(array['length']) is not int
                    or not 0<=array['length']<=1048576 or type(array['items']) is not list
                    or len(array['items'])!=min(array['length'],64)):
                raise ValueError('Invalid nested array extent')
            entries=[]
            budget[0]-=len(array['items'])
            if budget[0]<0:raise ValueError('Struct node limit')
            for entry in array['items']:
                if element_kind=='StructProperty':
                    entry=_struct_value(catalog,entry,depth+1,budget)
                    if entry.type_object!=expected:raise ValueError('Nested array struct type mismatch')
                elif element_kind in ('ObjectProperty','ClassProperty'):
                    if entry is not None:
                        if type(entry) is not dict or set(entry)!={'$reference'}:raise ValueError('Invalid nested array reference')
                        entry=reference(entry['$reference'])
                        if element_kind=='ClassProperty' and entry.index not in catalog.classes:
                            raise ValueError('Nested class array reference is not a reflected class')
                elif element_kind=='BoolProperty':
                    if type(entry) is not bool:raise ValueError('Invalid nested array bool')
                elif element_kind in ('FloatProperty','DoubleProperty'):
                    if type(entry) not in (int,float) and not (type(entry) is dict and set(entry)=={'$float'} and entry['$float'] in ('nan','inf','-inf')):
                        raise ValueError('Invalid nested array float')
                    entry=float(entry['$float']) if isinstance(entry,dict) else float(entry)
                elif element_kind=='NameProperty':
                    if type(entry) is not str:raise ValueError('Invalid nested array name')
                else:
                    low,high={'ByteProperty':(0,255),'UInt16Property':(0,65535),'IntProperty':(-2147483648,2147483647)}[element_kind]
                    if type(entry) is not int or not low<=entry<=high:raise ValueError('Invalid nested array integer')
                entries.append(entry)
            item=StoredArray(tuple(entries),array['length'])
        elif kind == 'MapProperty':
            if set(row) != {'name', 'type', 'value', 'map_key_type', 'map_value_type'} or (row['map_key_type'],row['map_value_type']) != ('NameProperty','ByteProperty'):
                raise ValueError('Unsupported nested map schema')
            item = _map_value(row,item,catalog)
            budget[0] -= len(item.items)
            if budget[0] < 0:raise ValueError('Struct node limit')
        elif kind == 'StructProperty':
            item = _struct_value(catalog, item, depth + 1, budget)
        elif kind == 'SoftObjectProperty':
            item = _soft_object_path(item)
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
        elif kind == 'StrProperty':
            if type(item) is not str or len(item) > 4096:
                raise ValueError('Invalid struct string')
        elif kind == 'NameProperty':
            if type(item) is not str: raise ValueError('Invalid struct name')
        elif kind in ('ByteProperty', 'IntProperty', 'UInt16Property'):
            low, high = {'ByteProperty': (0, 255), 'IntProperty': (-2147483648, 2147483647), 'UInt16Property': (0, 65535)}[kind]
            if type(item) is not int or not low <= item <= high: raise ValueError('Invalid struct integer')
        else:
            raise ValueError('Unsupported struct member value')
        fields[name] = item
    native=None
    if 'native' in payload:
        if (catalog.path_name(type_object)!='/Script/MovieScene.MovieSceneFrameRange' or
                type_object.class_name!='ScriptStruct' or fields or errors or payload['truncated'] or
                type(payload['native']) is not dict or set(payload['native'])!={'frame_range'}):
            raise ValueError('Unsupported native struct observation')
        bounds=payload['native']['frame_range']
        if type(bounds) is not dict or set(bounds)!={'lower','upper'}:raise ValueError('Invalid frame range observation')
        for bound in bounds.values():
            if type(bound) is not dict or set(bound)!={'kind','value'}:raise ValueError('Invalid frame range bound')
        native=StoredFrameRange(bounds['lower']['kind'],bounds['lower']['value'],bounds['upper']['kind'],bounds['upper']['value'])
    return StoredStruct(type_object, MappingProxyType(fields), MappingProxyType(errors),
                        MappingProxyType(types), payload['truncated'],native)


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


def capture_selected_values(pid,identities,*,fields,references=False):
    """Fresh class/outer closures and projected values in one read-only request.

    Two callers' observations are never combined. A v1 worker uses the existing
    two-query path; v2 emits both parts in one bounded framed response.
    """
    from .catalog import capture_selected,_decode_catalog
    from ._reader import active_reader
    identities=tuple(identities);fields=tuple(fields)
    reader=active_reader()
    if reader is None or getattr(reader,'supports_catalog_values',False) is not True:
        catalog=capture_selected(pid,identities)
        if references:
            result={}
            for row in identities:
                result[row[0]],catalog=read_values_with_references(catalog,catalog.by_index[row[0]],fields=fields)
            return catalog,result
        return catalog,read_values_many(catalog,tuple(catalog.by_index[row[0]] for row in identities),fields=fields)
    if type(pid) is not int or not 0<pid<=0xffffffff or not 1<=len(identities)<=1023:
        raise ValueError('Expected bounded selected-value identities')
    requested={}
    for row in identities:
        if (type(row) is not tuple or len(row)!=3 or any(type(v) is not int for v in row)
                or not 0<=row[0]<100000000 or not -0x80000000<=row[1]<=0x7fffffff
                or not 0x10000<=row[2]<=0x7fffffffffff or row[0] in requested):
            raise ValueError('Invalid selected-value identity')
        requested[row[0]]=row
    if (not 1<=len(fields)<=64 or len(set(fields))!=len(fields) or any(
            type(n) is not str or not 1<=len(n)<=256 or any(ch in n for ch in ';|\r\n\t\0') for n in fields)):
        raise ValueError('Invalid selected-value projection')
    selectors=','.join(f'{i}:{serial}:{address:x}' for i,serial,address in identities)+';'+'|'.join(fields)
    start,rows=_query(['--catalog-values',str(pid),selectors])
    if start['pid']!=pid:raise RuntimeQueryError('Selected-value process changed')
    catalog=_decode_catalog(start,[row for row in rows if row['event'] in ('object','class_relation')])
    if len(catalog.objects)>16384:raise RuntimeQueryError('Selected-value dependency limit exceeded')
    groups={};current=None
    for row in rows:
        if row['event']=='object':
            current=row['index']
            if current in requested:
                if current in groups:raise RuntimeQueryError('Duplicate selected-value target')
                groups[current]=[]
        if row['event'] not in ('object','class_relation') and current not in requested:
            raise RuntimeQueryError('Selected values outside a requested target')
        if current in requested and row['event']!='class_relation':groups[current].append(row)
    if set(groups)!=set(requested):raise RuntimeQueryError('Incomplete selected-value targets')
    result={}
    for index,(i,serial,address) in requested.items():
        obj=catalog.by_index.get(index)
        if obj is None or (obj.serial,obj.address)!=(serial,address):
            raise RuntimeQueryError('Selected-value identity changed')
        result[index]=_decode_values(catalog,obj,start,groups[index])
    if references:
        missing=_missing_references(catalog,rows)
        if missing:
            catalog=_extend_reference_catalog(catalog,tuple(requested.values()),missing)
            result={index:_decode_values(catalog,catalog.by_index[index],start,groups[index]) for index in requested}
    return catalog,result


SOURCE_VALUE_BATCH_LIMIT=256


def read_values_many_with_references(catalog,observed,*,fields=None,metrics=None):
    """Read siblings in one request, then validate their missing reference closure."""
    from .catalog import capture_selected
    objects=tuple(catalog.resolve(obj) for obj in observed)
    if not objects:return {},catalog
    # Decode reference identities from the same observation, rather than reread
    # values after extending the catalog (which could mix two graph states).
    selector=','.join(f'{o.index}:{o.serial}:{o.address:x}' for o in objects)
    if len(objects)>SOURCE_VALUE_BATCH_LIMIT or len({o.index for o in objects})!=len(objects):raise ValueError('Bounded unique source batch required')
    if fields is not None:
        fields=tuple(fields)
        if not 1<=len(fields)<=64 or len(set(fields))!=len(fields) or any(type(n) is not str or not n or any(c in n for c in ';|\r\n\t\0') for n in fields):raise ValueError('Invalid stored-value field projection')
        selector+=';'+'|'.join(fields)
    started=time.perf_counter() if metrics is not None else None
    start,rows=_query(['--read-values',str(catalog.pid),selector])
    if metrics is not None:
        metrics['source_values_query_ms']=metrics.get('source_values_query_ms',0.)+(time.perf_counter()-started)*1000
        started=time.perf_counter()
    requested={o.index:o for o in objects};groups={};current=None
    for row in rows:
        if row['event']=='object':
            current=row['index']
            if current not in requested or current in groups:raise RuntimeQueryError('Unexpected source batch identity')
            groups[current]=[]
        if current is not None:groups[current].append(row)
    if set(groups)!=set(requested):raise RuntimeQueryError('Incomplete source batch')
    result={i:_decode_values(catalog,requested[i],start,group) for i,group in groups.items()}
    if metrics is not None:
        metrics['source_values_decode_ms']=metrics.get('source_values_decode_ms',0.)+(time.perf_counter()-started)*1000
        started=time.perf_counter()
    affected=set()
    missing=_missing_references(catalog,rows,affected=affected)
    if metrics is not None:
        metrics['source_reference_scan_ms']=metrics.get('source_reference_scan_ms',0.)+(time.perf_counter()-started)*1000
    if missing:
        old_catalog=catalog
        started=time.perf_counter() if metrics is not None else None
        catalog=_extend_reference_catalog(catalog,tuple((o.index,o.serial,o.address) for o in objects),missing)
        if metrics is not None:
            metrics['source_reference_capture_ms']=metrics.get('source_reference_capture_ms',0.)+(time.perf_counter()-started)*1000
            started=time.perf_counter()
        # An extended observation can update an existing outer, flags or class
        # relation. In that case every group must be decoded against the new
        # catalog as before. Otherwise only groups with previously missing
        # references need a second decode; untouched groups were already fully
        # validated from the same read-only response.
        stable=(old_catalog.classes==catalog.classes and all(
            catalog.by_index.get(index)==obj for index,obj in old_catalog.by_index.items()))
        if stable and None not in affected:
            for i,group in groups.items():
                if i in affected:
                    result[i]=_decode_values(catalog,catalog.by_index[i],start,group)
                else:
                    prior=result[i]
                    result[i]=StoredValues(catalog.by_index[i],prior.values,prior.errors,prior.types,prior.truncated)
        else:
            result={i:_decode_values(catalog,catalog.by_index[i],start,group) for i,group in groups.items()}
        if metrics is not None:
            metrics['source_values_decode_ms']=metrics.get('source_values_decode_ms',0.)+(time.perf_counter()-started)*1000
    return result,catalog


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
    missing=_missing_references(catalog,rows)
    if missing:
        catalog = _extend_reference_catalog(catalog,((obj.index,obj.serial,obj.address),),missing)
        result = _decode_values(catalog, catalog.resolve(obj), start, rows)
    return result, catalog


def _extend_reference_catalog(catalog,targets,missing):
    """Validate large closures in bounded selected reads, never reread values."""
    from .catalog import capture_selected
    missing=tuple(sorted(missing));targets=tuple(targets)
    if not 1<=len(targets)<=1023 or len(missing)>16384:
        raise RuntimeQueryError('Stored reference closure limit')
    room=1023-len(targets)
    if room:
        for start in range(0,len(missing),room):
            catalog=catalog.with_observations(capture_selected(catalog.pid,targets+missing[start:start+room]))
    else:
        for start in range(0,len(missing),1023):
            catalog=catalog.with_observations(capture_selected(catalog.pid,missing[start:start+1023]))
        catalog=catalog.with_observations(capture_selected(catalog.pid,targets))
    return catalog


def _missing_references(catalog,rows,*,affected=None):
    missing = set()
    # Large cooked cinematic batches can contain over 268,000 values even
    # at modest depth. Bound total work independently from wrapper depth.
    walk_budget=[1048576]
    def reference(raw):
        if type(raw) is not dict or set(raw) != {'index', 'serial', 'address', 'name'}:
            raise RuntimeQueryError('Invalid nested stored reference')
        identity = (raw['index'], raw['serial'], int(raw['address'], 16))
        current = catalog.by_index.get(raw['index'])
        if current is None or (current.index, current.serial, current.address) != identity:
            missing.add(identity)
            if affected is not None:affected.add(target)
        if len(missing) > 16384:
            raise RuntimeQueryError('Nested stored reference limit')
    def walk(value, depth=0):
        walk_budget[0]-=1
        # Four typed struct levels can contain array/map/tag wrappers. Count
        # JSON wrapper depth separately from the decoder's typed depth bound.
        if depth > 32:
            raise RuntimeQueryError('Nested stored reference depth')
        if walk_budget[0]<0:
            raise RuntimeQueryError('Nested stored reference traversal limit')
        if isinstance(value, dict):
            if '$reference' in value:
                reference(value['$reference'])
            if '$struct' in value:
                reference(value['$struct']['type'])
            for child in value.values(): walk(child, depth + 1)
        elif isinstance(value, list):
            for child in value: walk(child, depth + 1)
    target=None
    for row in rows:
        if row.get('event')=='object':target=row['index']
        if row.get('event') == 'stored_value': walk(row.get('value'))
        elif row.get('event') == 'property_metadata':
            # Empty containers have no nested $struct value from which to
            # discover their type. Their descriptor still requires that exact
            # observed struct closure before the same response can be decoded.
            for prefix in ('struct','inner_struct','map_key_struct','map_value_struct'):
                if all(prefix+'_'+key in row for key in ('index','serial','address','name')):
                    reference({key:row[prefix+'_'+key] for key in ('index','serial','address','name')})
    if len(missing)>16384:raise RuntimeQueryError('Nested stored reference limit')
    return missing


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
            if metadata[key]['type'] in ('SoftObjectProperty', 'SoftClassProperty'):
                meta = metadata[key]
                expected_vtable = '0x6e12cb8' if meta['type'] == 'SoftClassProperty' else '0x6e128d8'
                try:
                    if (type(meta.get('element_size')) is not int or meta['element_size'] != 40 or
                            meta.get('vtable_rva') != expected_vtable or row.get('truncated', False)):
                        raise ValueError('Invalid soft property layout')
                    if meta['type'] == 'SoftClassProperty' and (
                            type(meta.get('meta_class_name')) is not str or not meta['meta_class_name'] or
                            type(meta.get('meta_class_index')) is not int or meta['meta_class_index'] < 0 or
                            type(meta.get('meta_class_serial')) is not int or meta['meta_class_serial'] < 0):
                        raise ValueError('Invalid soft class constraint')
                    value = _soft_object_path(value)
                except (KeyError, TypeError, ValueError) as error:
                    raise RuntimeQueryError(f'Invalid soft property observation: {error}') from error
            if metadata[key]['type'] == 'EnumProperty':
                meta = metadata[key]
                kind = meta.get('inner_type')
                widths = {'ByteProperty': 1, 'IntProperty': 4}
                bounds = {'ByteProperty': (0, 255), 'IntProperty': (-(1 << 31), (1 << 31) - 1)}
                if (kind not in widths or type(meta.get('element_size')) is not int or
                        meta['element_size'] != widths[kind] or type(meta.get('inner_element_size')) is not int or
                        meta['inner_element_size'] != widths[kind] or
                        type(meta.get('enum_name')) is not str or not meta['enum_name'] or
                        type(meta.get('enum_index')) is not int or meta['enum_index'] < 0 or
                        type(meta.get('enum_serial')) is not int or meta['enum_serial'] < 0 or
                        type(value) is not int or not bounds[kind][0] <= value <= bounds[kind][1]):
                    raise RuntimeQueryError('Invalid stored enum observation')
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
                    element_type = metadata[key]['inner_type']
                    struct_type = _struct_type(catalog, metadata[key], 'inner_struct') if element_type == 'StructProperty' else None
                    prefix_limits = _array_prefix_limits(catalog, key[0], key[1], element_type, struct_type)
                    if (type(length) is not int or not 0 <= length <= 1048576 or type(items) is not list
                            or len(items) not in tuple(min(length, limit) for limit in prefix_limits)
                            or row.get('truncated') is not (length > len(items))):
                        raise ValueError('Invalid array extent or truncation')
                    if element_type not in ('ObjectProperty', 'ClassProperty', 'FloatProperty', 'DoubleProperty',
                                            'NameProperty', 'IntProperty', 'UInt16Property', 'ByteProperty', 'StructProperty'):
                        raise ValueError('Unsupported array element type')
                    decoded = []
                    struct_budget = [_STRUCT_NODE_BUDGET]
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
