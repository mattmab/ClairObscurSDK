"""Identity-selected, batched live UStruct metadata (including generated classes)."""
from dataclasses import dataclass
from types import MappingProxyType

from . import RuntimeQueryError, _query
from .catalog import CatalogObject

REFERENCE_KINDS = ('struct', 'enum', 'property_class', 'meta_class', 'signature_function',
                   'inner_struct', 'inner_enum', 'inner_property_class', 'inner_meta_class',
                   'map_key_struct', 'map_value_struct')


@dataclass(frozen=True)
class ReflectionSnapshot:
    """Selected descriptors and their observed referenced-type catalog closure.

    Neither descriptors nor catalog own engine objects or authorize invocation.
    Reads are bounded observations, not a GC-atomic snapshot.
    """
    catalog: object
    descriptors: object


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
    return _describe(catalog, observed, _query)


def _describe(catalog, observed, query):
    targets = tuple(catalog.resolve(obj) for obj in observed)
    if len(targets) > 1024 or len({obj.index for obj in targets}) != len(targets):
        raise ValueError('Expected at most 1024 distinct descriptor identities')
    results = {}
    for offset in range(0, len(targets), 128):
        batch = targets[offset:offset + 128]
        selectors = ','.join(f'{obj.index}:{obj.serial}:{obj.address:x}' for obj in batch)
        start, rows = query(['--describe', str(catalog.pid), selectors])
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
                    for kind_name in REFERENCE_KINDS:
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


def describe_selected(pid, identities):
    """Capture descriptors without discovering unrelated live objects.

    ``identities`` contains 1..1024 observed ``(index, serial, address)`` tuples
    for UStructs (classes, functions or script structs). The independent native
    reader validates them and supplies referenced property-type identities.
    Missing types are captured in batches of at most 128, with at most 1024
    additional types and 16384 total catalog objects. No name lookup, process
    registry enumeration, native invocation or object retention occurs here.

    Returns ``ReflectionSnapshot(catalog, descriptors)``. The descriptors are
    revalidated against the selected type closure before publication. A changed
    identity rejects the observation; it is never silently substituted/retried.
    A legacy reader lacking a missing type's address is explicitly rejected;
    use ``describe`` with a complete catalog or update the read-only reader.
    This does not recursively describe referenced schemas or read their values.
    """
    from .catalog import capture_selected
    identities = tuple(identities)
    catalog = capture_selected(pid, identities)
    targets = tuple(catalog.by_index[identity[0]] for identity in identities)
    batches = []
    missing = {}
    for offset in range(0, len(targets), 128):
        batch = targets[offset:offset + 128]
        selectors = ','.join(f'{obj.index}:{obj.serial}:{obj.address:x}' for obj in batch)
        start, rows = _query(['--describe', str(pid), selectors])
        if start['pid'] != pid:
            raise RuntimeQueryError('Descriptor process changed')
        rows = tuple(rows)
        batches.append((start, rows))
        try:
            for row in rows:
                if row['event'] != 'property_metadata':
                    continue
                for kind in REFERENCE_KINDS:
                    if kind + '_index' not in row:
                        continue
                    index, serial, name = (row[kind + suffix] for suffix in ('_index', '_serial', '_name'))
                    if type(index) is not int or type(serial) is not int or type(name) is not str:
                        raise ValueError('Invalid referenced type identity')
                    known = catalog.by_index.get(index)
                    if known is not None:
                        if known.serial != serial or known.name != name:
                            raise ValueError('Referenced type changed since catalog')
                        address = known.address
                        if kind + '_address' in row and int(row[kind + '_address'], 16) != address:
                            raise ValueError('Referenced type address changed since catalog')
                    else:
                        if kind + '_address' not in row:
                            raise ValueError('Reader omits referenced type address; update reader or use describe with a complete catalog')
                        address = int(row[kind + '_address'], 16)
                    identity = (index, serial, address)
                    previous = missing.get(index)
                    if previous is not None and previous != (identity, name):
                        raise ValueError('Conflicting referenced type identities')
                    if known is None:
                        missing[index] = (identity, name)
                    if len(missing) > 1024:
                        raise ValueError('Referenced type limit exceeded')
        except (KeyError, ValueError, TypeError) as error:
            raise RuntimeQueryError(f'Invalid descriptor dependency response: {error}') from error
    references = tuple(value[0] for value in missing.values())
    for offset in range(0, len(references), 128):
        fresh = capture_selected(pid, references[offset:offset + 128])
        catalog = catalog.with_observations(fresh)
        if len(catalog.objects) > 16384:
            raise RuntimeQueryError('Descriptor catalog dependency limit exceeded')
    # Reuse the ordinary strict decoder on exactly the observed rows. This is
    # not a metadata retry; dependency reads validate type identities only.
    # Keeping the decoder shared also preserves inherited owner/type checks.
    responses = iter(batches)
    descriptors = _describe(catalog, targets, lambda arguments: next(responses))
    return ReflectionSnapshot(catalog, descriptors)
