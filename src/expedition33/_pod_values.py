"""Copied codecs for four target-verified, pointer-free reflected structs.

The opt-in v11 dispatcher independently validates the schema on the game thread.
No arbitrary struct serialization or native-owned value construction.
"""
from dataclasses import dataclass
from collections.abc import Mapping
import math
import struct
from types import MappingProxyType


@dataclass(frozen=True)
class Profile:
    path: str
    width: int
    fields: tuple  # name, byte offset, primitive kind or nested profile path


VECTOR = '/Script/CoreUObject.Vector2D'
COLOR = '/Script/CoreUObject.LinearColor'
MARGIN = '/Script/SlateCore.Margin'
ANCHORS = '/Script/Slate.Anchors'
PROFILES = MappingProxyType({
    VECTOR: Profile(VECTOR, 16, (('X', 0, 'DoubleProperty'), ('Y', 8, 'DoubleProperty'))),
    COLOR: Profile(COLOR, 16, tuple((name, i * 4, 'FloatProperty') for i, name in enumerate('RGBA'))),
    MARGIN: Profile(MARGIN, 16, tuple((name, i * 4, 'FloatProperty')
                                    for i, name in enumerate(('Left', 'Top', 'Right', 'Bottom')))),
    ANCHORS: Profile(ANCHORS, 32, (('Minimum', 0, VECTOR), ('Maximum', 16, VECTOR))),
})
_FLOAT_MAX = float.fromhex('0x1.fffffep+127')


@dataclass(frozen=True, eq=False)
class NumericStructValue(Mapping):
    """Immutable numeric field copies with their exact supported struct path.

    This owns no native allocation or UObject. Calls still revalidate the current
    parameter schema; retaining this value retains only Python numbers.
    """
    path: str
    _fields: object

    def __post_init__(self):
        fields = dict(self._fields)
        encode(self.path, fields)
        for name, _, kind in PROFILES[self.path].fields:
            if kind in PROFILES:
                fields[name] = decode(kind, encode(kind, fields[name]))
        object.__setattr__(self, '_fields', MappingProxyType(fields))

    def __getitem__(self, key):
        return self._fields[key]

    def __iter__(self):
        return iter(self._fields)

    def __len__(self):
        return len(self._fields)


def validate_profile(catalog, descriptor, descriptors):
    """Validate observations only; native game-thread revalidation is still required."""
    observed = catalog.resolve(descriptor.object)
    path = catalog.path_name(observed)
    if observed.class_name != 'ScriptStruct' or path not in PROFILES:
        raise ValueError('Unsupported POD struct identity')
    profile = PROFILES[path]
    if (len(descriptor.owners) != 1 or descriptor.owners[0]['index'] != observed.index or
            descriptor.owners[0]['size'] != profile.width or int(descriptor.owners[0]['super'], 16)):
        raise ValueError('POD struct owner, extent or inheritance changed')
    rows = descriptor.properties
    if len(rows) != len(profile.fields):
        raise ValueError('POD struct field count changed')
    for row, (name, offset, kind) in zip(rows, profile.fields):
        nested = kind in PROFILES
        width = PROFILES[kind].width if nested else 8 if kind == 'DoubleProperty' else 4
        if (row['owner_index'] != observed.index or row['name'] != name or
                row['offset'] != offset or row['element_size'] != width or row['dimension'] != 1 or
                row['type'] != ('StructProperty' if nested else kind)):
            raise ValueError('POD struct field layout changed')
        if nested:
            child = catalog.by_index[row['struct_index']]
            if (child.serial != row['struct_serial'] or child.name != row['struct_name'] or
                    catalog.path_name(child) != kind):
                raise ValueError('Nested POD struct identity changed')
            child_descriptor = descriptors[child.index]
            if catalog.resolve(child_descriptor.object) != child:
                raise ValueError('Nested POD descriptor does not match its identity')
            validate_profile(catalog, child_descriptor, descriptors)
    return profile


def encode(path, value):
    """Copy exact named fields; constrain numbers to the verified UI conversion range."""
    profile = PROFILES[path]
    if type(value) is NumericStructValue:
        if value.path != path:
            raise ValueError('Numeric struct type does not match the parameter profile')
        value = dict(value)
    if type(value) is not dict or set(value) != {name for name, _, _ in profile.fields}:
        raise ValueError('POD arguments require exactly the named fields')
    output = bytearray(profile.width)
    for name, offset, kind in profile.fields:
        item = value[name]
        if kind in PROFILES:
            encoded = encode(kind, item)
            output[offset:offset + len(encoded)] = encoded
        else:
            try:
                valid = type(item) in (int, float) and math.isfinite(item) and abs(item) <= _FLOAT_MAX
            except OverflowError:
                valid = False
            if not valid:
                raise ValueError('POD component must be finite and fit the target UI float range')
            struct.pack_into('<d' if kind == 'DoubleProperty' else '<f', output, offset, item)
    return bytes(output)


def decode(path, data):
    """Return immutable copied fields; raw pointers and owned values are unsupported."""
    profile = PROFILES[path]
    if type(data) is not bytes or len(data) != profile.width:
        raise ValueError('POD result extent changed')
    result = {}
    for name, offset, kind in profile.fields:
        if kind in PROFILES:
            item = decode(kind, data[offset:offset + PROFILES[kind].width])
        else:
            item = struct.unpack_from('<d' if kind == 'DoubleProperty' else '<f', data, offset)[0]
            if not math.isfinite(item) or abs(item) > _FLOAT_MAX:
                raise ValueError('POD result has an invalid numeric component')
        result[name] = item
    return NumericStructValue(path, result)
