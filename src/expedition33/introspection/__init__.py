"""Port of Mattmab's BL4 Introspection core, using independent E33 primitives.

This adapter supports discovery, schema and an expanding set of stored values. The original
core is preserved verbatim; remaining operations are explicit pending work.
"""
import threading
from types import SimpleNamespace

from ..catalog import capture
from ..reflection import describe
from ..enums import describe_enums
from ..values import read_values, StoredArray, StoredStruct
from .. import ObjectSnapshot, RuntimeQueryError
from .. import _pod_values
from .core import Explorer


class UnsupportedCapability(RuntimeError):
    pass


class _StructValue:
    def __init__(self, backend, observation):
        self._backend, self._observation = backend, observation
        self._type = SimpleNamespace(Name=observation.type_object.name,
            _properties=lambda: (SimpleNamespace(Name=name) for name in observation.types))

    def __getattr__(self, name):
        if name in self._observation.errors:
            raise UnsupportedCapability(self._observation.errors[name])
        if name not in self._observation.fields:
            raise AttributeError(name)
        return _adapt(self._backend, self._observation.fields[name])

    def __str__(self):
        return f'Reflected observation of {self._type.Name}; native state is not owned'


class _CopiedNumericStruct(_StructValue):
    """Expose typed numeric copies to the original WrappedStruct encoder."""
    def __init__(self, backend, value):
        self._backend, self._value = backend, value
        self._observation = SimpleNamespace(truncated=False)
        self._type = SimpleNamespace(Name=value.path.rsplit('.',1)[1],
            _properties=lambda: (SimpleNamespace(Name=name) for name in value))

    def __getattr__(self, name):
        if name not in self._value:
            raise AttributeError(name)
        return _adapt(self._backend, self._value[name])

    def __str__(self):
        return f'Copied numeric {self._type.Name}; no native allocation'


def _adapt(backend, value):
    if isinstance(value, _pod_values.NumericStructValue): return _CopiedNumericStruct(backend, value)
    if isinstance(value, ObjectSnapshot): return backend.wrap(value)
    if isinstance(value, StoredStruct): return _StructValue(backend, value)
    if isinstance(value, StoredArray): return StoredArray(tuple(_adapt(backend, item) for item in value.items), value.length)
    if isinstance(value, tuple): return tuple(_adapt(backend, item) for item in value)
    return value


class _Object:
    def __init__(self, backend, observed):
        object.__setattr__(self, '_backend', backend)
        object.__setattr__(self, '_observed', observed)

    def __setattr__(self, name, value):
        backend = self._backend
        if not backend.mutation_authorized or not backend.assignment:
            raise UnsupportedCapability('Writes require an authorized set request and v10 assignment')
        prop = self.Class._find_prop(name)
        if prop.Class.Name != 'ObjectProperty' or prop.ArrayDim != 1:
            raise UnsupportedCapability('Harness set currently supports scalar ObjectProperty only')
        if value is not None and (not isinstance(value, _Object) or value._backend is not backend):
            raise ValueError('Object property requires null or a reference from this Harness')
        before = getattr(self, name)
        if before is not None and not isinstance(before, _Object):
            raise UnsupportedCapability('Current object reference could not be observed')
        backend.session.assign_object(self._observed,
            backend.catalog.by_index[prop._row['owner_index']], name,
            value._observed if value is not None else None,
            expected=before._observed if before is not None else None, allow_mutation=True)
        backend.mutation_completed = True
        # Invalidate the before-value cache so the original core's final getattr
        # performs an independent post-mutation observation.
        backend.refresh()

    @property
    def Name(self):
        return self._observed.name

    @property
    def Class(self):
        return self._backend.wrap(self._backend.catalog.by_index[self._observed.class_index])

    def _path_name(self):
        return self._backend.catalog.path_name(self._observed)

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        if self._backend.session is not None:
            for owner in self._backend.catalog.ancestors(self._observed.class_index):
                matches = [fn for fn in self._backend.function_children.get(owner, ()) if fn.name == name]
                if len(matches) > 1:
                    raise RuntimeQueryError('Ambiguous reflected member')
                if matches:
                    function = matches[0]
                    def invoke(**arguments):
                        def unwrap(value):
                            if isinstance(value, _Object): return value._observed
                            if isinstance(value, _CopiedNumericStruct): return value._value
                            if type(value) in (list, tuple): return tuple(unwrap(item) for item in value)
                            return value
                        call = (self._backend.session.invoke_retained if self._backend.retained
                                else self._backend.session.invoke)
                        result = call(self._observed, function,
                            **{key: unwrap(value) for key, value in arguments.items()})
                        if self._backend.retained:
                            self._backend.pending_owner = result
                        try:
                            self._backend.refresh()
                            returned = _adapt(self._backend, result.return_value)
                            value = (returned if not result.outputs else
                                     {'return': returned, 'out': {key: _adapt(self._backend, value)
                                      for key, value in result.outputs.items()}})
                            if self._backend.retained:
                                self._backend.pending_value = value
                            return value
                        except RuntimeQueryError as error:
                            from ..invocation import InvocationError
                            raise InvocationError(f'Dispatch returned; Harness result observation failed: {error}',
                                                  outcome='dispatch_returned') from error
                    return invoke
        if self._observed.index not in self._backend.observations:
            self._backend.observations[self._observed.index] = read_values(self._backend.catalog, self._observed)
        observation = self._backend.observations[self._observed.index]
        key = next((key for key in observation.types if key[1] == name), None)
        if key is None:
            raise AttributeError(name)
        if key in observation.errors:
            raise UnsupportedCapability(observation.errors[key])
        return _adapt(self._backend, observation.values[key])


class _Struct(_Object):
    def _find_prop(self, name):
        if type(name) is not str or not name:
            raise ValueError('Expected a reflected property name')
        self._backend.ensure_described((self._observed,))
        rows = self._backend.descriptors[self._observed.index].properties
        matches = [row for row in rows if row['name'] == name]
        if len(matches) != 1:
            raise ValueError('Reflected property is missing or ambiguous')
        return _Property(self._backend, matches[0])

    def _superfields(self):
        self._backend.ensure_described((self._observed,))
        descriptor = self._backend.descriptors[self._observed.index]
        for owner in descriptor.owners:
            yield self._backend.wrap(self._backend.catalog.by_index[owner['index']])

    def _properties(self):
        if self._observed.index not in self._backend.properties:
            self._backend.ensure_described((self._observed,))
        return iter(self._backend.properties[self._observed.index])

    def _fields(self):
        return (self._backend.wrap(obj) for obj in self._backend.function_children.get(self._observed.index, ()))


class _Function(_Struct):
    pass


class _Property:
    def __init__(self, backend, row):
        self._row = row
        self.Name, self.Class = row['name'], SimpleNamespace(Name=row['type'])
        self.PropertyFlags, self.ArrayDim, self.Offset_Internal = row['flags'], row['dimension'], row['offset']
        for key, attr in (('struct_index', 'Struct'), ('enum_index', 'Enum'),
                          ('property_class_index', 'PropertyClass'), ('meta_class_index', 'MetaClass'),
                          ('signature_function_index', 'SignatureFunction')):
            if key in row:
                setattr(self, attr, backend.wrap(backend.catalog.by_index[row[key]]))
        if row.get('inner_type'):
            self.Inner = SimpleNamespace(Name=row['inner_name'], Class=SimpleNamespace(Name=row['inner_type']),
                                         ElementSize=row['inner_element_size'])
            for key, attr in (('inner_struct_index', 'Struct'), ('inner_enum_index', 'Enum'),
                              ('inner_property_class_index', 'PropertyClass'), ('inner_meta_class_index', 'MetaClass')):
                if key in row:
                    setattr(self.Inner, attr, backend.wrap(backend.catalog.by_index[row[key]]))


class _Explorer(Explorer):
    """Add copied inner-type metadata without modifying the preserved core."""
    def __init__(self, sdk):
        super().__init__(sdk)
        self._owners = {}

    def _sweep_owners(self):
        errors = []
        for name, (value, owner) in tuple(self._owners.items()):
            if name in self.values and self.values[name] is value:
                continue
            del self._owners[name]
            try:
                owner.release()
            except BaseException as error:
                errors.append(error)
        if errors:
            raise errors[0]

    def expire(self):
        super().expire()
        self._sweep_owners()

    def close(self):
        try:
            super().close()
        finally:
            self._sweep_owners()

    def dispatch(self, request):
        try:
            return super().dispatch(request)
        finally:
            owner = getattr(self.sdk, 'pending_owner', None)
            if owner is not None:
                value = self.sdk.pending_value
                self.sdk.pending_owner = None
                self.sdk.pending_value = object()
                name = request.get('retain') if request['op'] == 'invoke' else None
                if isinstance(name, str) and name in self.values and self.values[name] is value:
                    previous = self._owners.get(name)
                    self._owners[name] = (value, owner)
                    if previous is not None:
                        previous[1].release()
                else:
                    owner.release()
            self._sweep_owners()

    def encode(self, value, depth=2, budget=None):
        result = super().encode(value, depth, budget)
        if isinstance(value, _StructValue) and '$struct' in result and value._observation.truncated:
            result['truncated'] = True
        return result

    def prop_schema(self, prop):
        result = super().prop_schema(prop)
        enum = getattr(prop, 'Enum', None)
        if enum is not None and 'Enum' in result:
            result['Enum'].update(self.sdk.enum_schema(enum))
        inner = getattr(prop, 'Inner', None)
        if inner is not None:
            detail = result['Inner']
            detail['property_type'] = inner.Class.Name
            detail['element_size'] = inner.ElementSize
            for attr in ('Struct', 'Enum', 'PropertyClass', 'MetaClass'):
                reference = getattr(inner, attr, None)
                if reference is not None:
                    detail[attr] = self.ref(reference)
                    if attr == 'Enum':
                        detail[attr].update(self.sdk.enum_schema(reference))
        return result


class _Backend:
    __version__ = 'expedition33-independent/introspection-stage1'
    unreal = SimpleNamespace(UObject=_Object, UFunction=_Function,
        WrappedStruct=_StructValue, WrappedArray=StoredArray)

    def __init__(self, session=None):
        self.session = session
        self.retained = bool(session is not None and getattr(session, 'supports_retained_invocation', False))
        self.assignment = bool(session is not None and getattr(session, 'supports_object_assignment', False))
        self.pod_values = bool(session is not None and getattr(session, 'supports_pod_values', False))
        self.mutation_authorized = self.mutation_completed = False
        self.pending_owner = None
        self.pending_value = object()
        self.catalog = None
        self.descriptors, self.properties, self.function_children = {}, {}, {}
        self.observations = {}
        self.enum_descriptors = {}

    def refresh(self):
        self.catalog = capture()
        self.descriptors, self.properties, self.function_children = {}, {}, {}
        self.observations = {}
        self.enum_descriptors = {}
        self._struct_class = self.catalog.find_class('Struct').index
        self._function_class = self.catalog.find_class('Function').index
        for obj in self.catalog.objects:
            if self._function_class in self.catalog.ancestors(obj.class_index):
                self.function_children.setdefault(obj.outer_index, []).append(obj)

    def clear(self):
        self.catalog = None
        self.descriptors.clear(); self.properties.clear(); self.function_children.clear()
        self.observations.clear()
        self.enum_descriptors.clear()

    def enum_schema(self, enum):
        obj = self.catalog.resolve(enum._observed)
        if obj.index not in self.enum_descriptors:
            try:
                descriptor = describe_enums(self.catalog, [obj])[obj.index]
                # Bound schema expansion independently of the native reader limit.
                self.enum_descriptors[obj.index] = {
                    'members': tuple((m.name, m.value) for m in descriptor.members[:128]),
                    'member_count': len(descriptor.members),
                    'members_truncated': len(descriptor.members) > 128}
            except RuntimeQueryError as error:
                self.enum_descriptors[obj.index] = {'members_error': str(error)[:500]}
        result = dict(self.enum_descriptors[obj.index])
        if 'members' in result:
            result['members'] = [dict(name=name, value=value) for name, value in result['members']]
        return result

    def wrap(self, obj):
        obj = self.catalog.resolve(obj)
        lineage = self.catalog.ancestors(obj.class_index)
        kind = _Function if self._function_class in lineage else _Struct if self._struct_class in lineage else _Object
        return kind(self, obj)

    def ensure_described(self, objects):
        missing = tuple(obj for obj in objects if obj.index not in self.descriptors)
        if not missing:
            return
        descriptors = describe(self.catalog, missing)
        self.descriptors.update(descriptors)
        for descriptor in descriptors.values():
            grouped = {row['index']: [] for row in descriptor.owners}
            for prop in descriptor.properties:
                grouped[prop['owner_index']].append(_Property(self, prop))
            self.properties.update(grouped)

    def find_class(self, name):
        if name.startswith('/'):
            return self.find_object('Class', name)
        return self.wrap(self.catalog.by_index[self.catalog.find_class(name).index])

    def make_struct(self, name, **fields):
        if not self.pod_values:
            raise UnsupportedCapability('Typed numeric structs require the v11 POD capability')
        matches = [path for path in _pod_values.PROFILES if name in (path, path.rsplit('.',1)[1])]
        if len(matches) != 1:
            raise UnsupportedCapability('Only Vector2D, LinearColor, Margin and Anchors have verified value codecs')
        fields = {key: value._value if isinstance(value, _CopiedNumericStruct) else value
                  for key, value in fields.items()}
        # This is a copied Python value, not native construction. Invocation
        # planning and the game-thread backend revalidate the current schema.
        value = _pod_values.decode(matches[0], _pod_values.encode(matches[0], fields))
        return _CopiedNumericStruct(self, value)

    def find_object(self, class_name, path):
        matches = [obj for obj in self.find_all(class_name) if obj._path_name() == path]
        if len(matches) != 1:
            raise RuntimeQueryError('Exact object path missing or ambiguous')
        return matches[0]

    def find_all(self, class_name, exact=False):
        if self.catalog is None:
            raise RuntimeQueryError('No current request catalog')
        if class_name.startswith('/'):
            matches = [cls for cls in self.catalog.classes.values()
                       if self.catalog.path_name(self.catalog.by_index[cls.index]) == class_name]
            if len(matches) != 1:
                raise RuntimeQueryError('Exact class path missing or ambiguous')
            target = matches[0].index
            rows = (obj for obj in self.catalog.objects if
                (obj.class_index == target if exact else target in self.catalog.ancestors(obj.class_index)))
        else:
            rows = self.catalog.select(class_name, exact=exact)
        return (self.wrap(obj) for obj in rows)


class Harness:
    """Persistent original Explorer with an external owner-thread SDK adapter."""
    SUPPORTED = frozenset(('status', 'roots', 'search', 'schema', 'inspect', 'snapshot', 'diff'))

    def __init__(self, session=None):
        self._owner = threading.get_ident()
        enabled = session is not None and session.supports_reflected_invocation
        self.SUPPORTED = type(self).SUPPORTED | (frozenset(('invoke',)) if enabled else frozenset())
        self._backend = _Backend(session if enabled else None)
        if self._backend.retained:
            self.SUPPORTED |= frozenset(('release_value',))
        if self._backend.assignment:
            self.SUPPORTED |= frozenset(('set',))
        self._explorer = _Explorer(self._backend)
        self._closed = False
        self._running = False

    def request(self, request):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Harness requests must run on the owning Python thread')
        if self._closed or self._running:
            raise RuntimeError('Harness is closed or request dispatch is reentrant')
        if not isinstance(request, dict) or not isinstance(request.get('op'), str):
            raise ValueError('Request requires an operation string')
        if request['op'] not in self.SUPPORTED:
            raise UnsupportedCapability(
                f"{request['op']!r} is not ported yet; see research/INTROSPECTION_PORT.md")
        if request['op'] == 'invoke' and request.get('retain') is not None and not self._backend.retained:
            raise UnsupportedCapability('Retained native result ownership is not implemented; no call dispatched')
        self._running = True
        self._backend.mutation_authorized = request['op'] == 'set' and request.get('allow_mutation') is True
        self._backend.mutation_completed = False
        try:
            self._explorer.expire()
            if request['op'] not in ('status', 'diff', 'release_value'):
                self._backend.refresh()
            if request['op'] == 'schema':
                cls = (self._backend.find_object('Struct', request['struct']) if 'struct' in request
                       else self._backend.find_class(request['class']))
                self._backend.ensure_described((cls._observed,))
                # Keep original deduplication/page semantics, with a single native
                # metadata batch for the selected functions instead of N processes.
                offset = max(0, int(request.get('offset', 0)))
                from .core import bounded
                limit = bounded(request.get('limit'))
                from itertools import islice
                functions = list(islice(self._explorer.functions(cls), offset, offset + limit))
                self._backend.ensure_described(tuple(fn._observed for fn in functions))
            result = self._explorer.dispatch(request)
            if request['op'] == 'status':
                result['original_operations'] = result['operations']
                result['operations'] = sorted(self.SUPPORTED)
                result['original_argument_types'] = result['argument_types']
                result['argument_types'] = (['primitive', '$object', 'fixed_array'] if 'invoke' in self.SUPPORTED else [])
                if self._backend.retained:
                    result['argument_types'].append('$value')
                if self._backend.pod_values:
                    result['argument_types'].append('$struct')
                result['struct_types'] = list(_pod_values.PROFILES) if self._backend.pod_values else []
                result['parity_complete'] = False
                result['write_types'] = ['ObjectProperty'] if self._backend.assignment else []
                result['limitations'] = ['Stored scalars, strings, references, selected arrays and bounded reflected structs; opaque native state is not owned',
                    ('Set supports scalar ObjectProperty only; other writes pending' if self._backend.assignment else 'Writes pending') +
                    '; traces and agent bridge pending; invocation requires opt-in v6 and supported parameter types',
                    ('Retain supports copied primitives and leased object outputs; opaque native values unsupported'
                     if self._backend.retained else 'Invocation retain and opaque native values unsupported') +
                    '; out parameters use named return/out result fields',
                    'Container/string/enum-valued struct members, map/set and additional property variants pending',
                    'Function pages use registry identity order within each declaring class']
                result['execution'] = ('external Python owner thread; native calls on game thread' if 'invoke' in self.SUPPORTED
                                       else 'external Python owner thread; read-only native catalog')
            return result
        except RuntimeQueryError as error:
            if request['op'] == 'set' and self._backend.mutation_completed:
                from ..invocation import InvocationError
                raise InvocationError(f'Assignment returned; Harness after-observation failed: {error}',
                                      outcome='dispatch_returned') from error
            raise
        finally:
            self._backend.mutation_authorized = self._backend.mutation_completed = False
            self._backend.clear()
            self._running = False

    def poll(self):
        if threading.get_ident() != self._owner or self._closed or self._running:
            raise RuntimeError('Harness expiry requires an idle owning thread')
        self._explorer.expire()

    def close(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Harness cleanup must run on the owning Python thread')
        if self._running:
            raise RuntimeError('Cannot close during a harness request')
        try:
            self._explorer.close()
        finally:
            self._backend.clear()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
