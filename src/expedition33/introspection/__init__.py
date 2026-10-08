"""Port of Mattmab's BL4 Introspection core, using independent E33 primitives.

This adapter supports discovery, schema and an expanding set of stored values. The original
core is preserved verbatim; remaining operations are explicit pending work.
"""
import threading
from types import SimpleNamespace

from ..catalog import capture
from ..reflection import describe
from ..values import read_values
from .. import ObjectSnapshot, RuntimeQueryError
from .core import Explorer


class UnsupportedCapability(RuntimeError):
    pass


class _UnavailableValue:
    """Type marker only; no native wrapper construction is exposed yet."""


class _Object:
    def __init__(self, backend, observed):
        self._backend, self._observed = backend, observed

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
        if self._observed.index not in self._backend.observations:
            self._backend.observations[self._observed.index] = read_values(self._backend.catalog, self._observed)
        observation = self._backend.observations[self._observed.index]
        key = next((key for key in observation.types if key[1] == name), None)
        if key is None:
            raise AttributeError(name)
        if key in observation.errors:
            raise UnsupportedCapability(observation.errors[key])
        def adapt(value):
            if isinstance(value, ObjectSnapshot): return self._backend.wrap(value)
            if isinstance(value, tuple): return tuple(adapt(item) for item in value)
            return value
        return adapt(observation.values[key])


class _Struct(_Object):
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
        self.Name, self.Class = row['name'], SimpleNamespace(Name=row['type'])
        self.PropertyFlags, self.ArrayDim, self.Offset_Internal = row['flags'], row['dimension'], row['offset']
        for key, attr in (('struct_index', 'Struct'), ('enum_index', 'Enum')):
            if key in row:
                setattr(self, attr, backend.wrap(backend.catalog.by_index[row[key]]))
        if row.get('inner_type'):
            self.Inner = SimpleNamespace(Name=row['inner_name'], Class=SimpleNamespace(Name=row['inner_type']))


class _Backend:
    __version__ = 'expedition33-independent/introspection-stage1'
    unreal = SimpleNamespace(UObject=_Object, UFunction=_Function,
        WrappedStruct=_UnavailableValue, WrappedArray=_UnavailableValue)

    def __init__(self):
        self.catalog = None
        self.descriptors, self.properties, self.function_children = {}, {}, {}
        self.observations = {}

    def refresh(self):
        self.catalog = capture()
        self.descriptors, self.properties, self.function_children = {}, {}, {}
        self.observations = {}
        self._struct_class = self.catalog.find_class('Struct').index
        self._function_class = self.catalog.find_class('Function').index
        for obj in self.catalog.objects:
            if self._function_class in self.catalog.ancestors(obj.class_index):
                self.function_children.setdefault(obj.outer_index, []).append(obj)

    def clear(self):
        self.catalog = None
        self.descriptors.clear(); self.properties.clear(); self.function_children.clear()
        self.observations.clear()

    def wrap(self, obj):
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

    def __init__(self):
        self._owner = threading.get_ident()
        self._backend = _Backend()
        self._explorer = Explorer(self._backend)
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
        self._running = True
        try:
            if request['op'] not in ('status', 'diff'):
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
                result['argument_types'] = []
                result['parity_complete'] = False
                result['limitations'] = ['Value reads cover stored bool/byte/int32/uint16/float/double/name/string/object references; recursive types pending',
                    'Writes, invocation, traces and agent bridge pending',
                    'Object-class, map/set and delegate type references pending',
                    'Function pages use registry identity order within each declaring class']
                result['execution'] = 'external Python owner thread; read-only native catalog'
            return result
        finally:
            self._backend.clear()
            self._running = False

    def close(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Harness cleanup must run on the owning Python thread')
        if self._running:
            raise RuntimeError('Cannot close during a harness request')
        self._explorer.close()
        self._backend.clear()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
