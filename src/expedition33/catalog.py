"""Read-only ownership/inheritance observations from the independent native reader.

Catalogs do not pin objects or form a GC-atomic snapshot. Refresh before an
operation, then revalidate in the native operation itself. A serial of zero is
an observed registry value, not a lifetime guarantee.
"""
from dataclasses import dataclass
from types import MappingProxyType

from . import ObjectSnapshot, RuntimeQueryError, _query


@dataclass(frozen=True)
class CatalogObject(ObjectSnapshot):
    outer_index: int
    outer_serial: int
    object_flags: int
    item_flags: int


@dataclass(frozen=True)
class ClassRelation:
    index: int
    serial: int
    name: str
    super_index: int
    size: int


class Catalog:
    def __init__(self, pid, objects, classes):
        self.pid = pid
        self.objects = tuple(objects)
        self.by_index = MappingProxyType({obj.index: obj for obj in self.objects})
        self.classes = MappingProxyType({cls.index: cls for cls in classes})
        if len(self.by_index) != len(self.objects) or len(self.classes) != len(classes):
            raise RuntimeQueryError('Duplicate catalog identity')
        self._ancestors = {}
        self._classes_by_name = {}
        self._paths = {}
        for cls in self.classes.values():
            self._classes_by_name.setdefault(cls.name, []).append(cls)
        for obj in self.objects:
            if obj.pid != pid:
                raise RuntimeQueryError('Catalog process mismatch')
            cls = self.classes.get(obj.class_index)
            if cls is None or cls.name != obj.class_name:
                raise RuntimeQueryError('Catalog class identity missing or changed')
            if obj.outer_index != -1:
                outer = self.by_index.get(obj.outer_index)
                if outer is None or outer.serial != obj.outer_serial:
                    raise RuntimeQueryError('Catalog outer missing or changed; refresh required')
        for cls in self.classes.values():
            obj = self.by_index.get(cls.index)
            if obj is None or obj.serial != cls.serial or obj.name != cls.name:
                raise RuntimeQueryError('Class descriptor identity changed; refresh required')
            self.ancestors(cls.index)

    def ancestors(self, class_index):
        """Class identities from most-derived to root, with cycle/bounds checks."""
        if class_index in self._ancestors:
            return self._ancestors[class_index]
        result = []
        current = class_index
        while current != -1:
            if current in result or len(result) >= 128:
                raise RuntimeQueryError('Catalog inheritance cycle or depth limit')
            try:
                cls = self.classes[current]
            except KeyError:
                raise RuntimeQueryError('Catalog superclass missing') from None
            result.append(current)
            current = cls.super_index
        self._ancestors[class_index] = tuple(result)
        return self._ancestors[class_index]

    def find_class(self, name):
        """Resolve a unique observed class name; ambiguity is an error."""
        matches = self._classes_by_name.get(name, ())
        if len(matches) != 1:
            raise RuntimeQueryError(f'Expected one class {name!r}; found {len(matches)}')
        return matches[0]

    def select(self, class_name='Object', *, exact=False):
        """Filter by verified superclass identities, including Blueprint classes."""
        target = self.find_class(class_name).index
        return tuple(obj for obj in self.objects if
                     (obj.class_index == target if exact else
                      target in self.ancestors(obj.class_index)))

    def resolve(self, observed):
        """Match a previous observation against this catalog; never use an address."""
        current = self.by_index.get(observed.index)
        keys = ('pid', 'index', 'serial', 'address', 'name', 'class_index')
        if current is None or any(getattr(current, key) != getattr(observed, key) for key in keys):
            raise RuntimeQueryError('Object identity changed or belongs to another process')
        return current

    def outer_chain(self, observed):
        """Root-first ownership chain. No unverified Unreal path punctuation."""
        current = self.resolve(observed)
        seen, result = set(), []
        while True:
            if current.index in seen or len(seen) >= 128:
                raise RuntimeQueryError('Catalog ownership cycle or depth limit')
            seen.add(current.index)
            result.append(current)
            if current.outer_index == -1:
                return tuple(reversed(result))
            current = self.by_index[current.outer_index]

    def path_name(self, observed):
        """Target-derived UObject path, with the package/subobject separator rule.

        Shipping GetPathName thunk 14384f9c0 calls 1413b2910; recursive
        1413b2aa0 uses ':' only when outer is not Package and outer's outer
        is Package, otherwise '.'. Package identity getter is 1413400c0.
        """
        current = self.resolve(observed)
        if current.index in self._paths:
            return self._paths[current.index]
        chain = self.outer_chain(current)
        package = self.find_class('Package').index
        result = chain[0].name
        for index in range(1, len(chain)):
            outer = chain[index - 1]
            colon = (outer.class_index != package and index >= 2 and
                     chain[index - 2].class_index == package)
            result += (':' if colon else '.') + chain[index].name
        self._paths[current.index] = result
        return result

    def find_path(self, path, class_name='Object'):
        """Resolve an exact target-derived path; ambiguous references fail."""
        matches = [obj for obj in self.select(class_name) if self.path_name(obj) == path]
        if len(matches) != 1:
            raise RuntimeQueryError(f'Expected one object at {path!r}; found {len(matches)}')
        return matches[0]


def capture():
    """Capture fresh live ownership and superclass observations; no saved-dump fallback."""
    start, rows = _query(['--catalog'])
    objects, classes = [], []
    try:
        for row in rows:
            if row['event'] == 'object':
                objects.append(CatalogObject(
                    pid=start['pid'], address=int(row['address'], 16),
                    object_flags=int(row['object_flags'], 16), item_flags=int(row['item_flags'], 16),
                    **{key: row[key] for key in ('index', 'serial', 'name', 'class_name',
                        'metaclass_name', 'class_index', 'outer_index', 'outer_serial')}))
            elif row['event'] == 'class_relation':
                classes.append(ClassRelation(**{key: row[key] for key in
                    ('index', 'serial', 'name', 'super_index', 'size')}))
            else:
                raise ValueError('Unexpected catalog event')
        return Catalog(start['pid'], objects, classes)
    except (KeyError, ValueError, TypeError) as error:
        raise RuntimeQueryError(f'Invalid catalog response: {error}') from error
