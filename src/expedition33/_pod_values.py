"""Copied codecs for target-verified, pointer-free reflected structs.

The opt-in v11 dispatcher independently validates the schema on the game thread.
Vector requires the experimental vector-values runtime. No arbitrary struct
serialization or native-owned value construction.
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


GUID = '/Script/CoreUObject.Guid'
VECTOR = '/Script/CoreUObject.Vector2D'
COLOR = '/Script/CoreUObject.LinearColor'
MARGIN = '/Script/SlateCore.Margin'
ANCHORS = '/Script/Slate.Anchors'
VECTOR3 = '/Script/CoreUObject.Vector'
FRAME_NUMBER = '/Script/CoreUObject.FrameNumber'
FRAME_TIME = '/Script/CoreUObject.FrameTime'
FRAME_RATE = '/Script/CoreUObject.FrameRate'
QUALIFIED_FRAME_TIME = '/Script/CoreUObject.QualifiedFrameTime'
TIMESPAN = '/Script/CoreUObject.Timespan'
FRAME_PROFILES = (FRAME_NUMBER, FRAME_TIME, FRAME_RATE, QUALIFIED_FRAME_TIME)
PROFILES = MappingProxyType({
    GUID: Profile(GUID, 16, tuple((name, i*4, 'IntProperty') for i,name in enumerate('ABCD'))),
    TIMESPAN: Profile(TIMESPAN, 8, ()),
    FRAME_NUMBER: Profile(FRAME_NUMBER, 4, (('Value', 0, 'IntProperty'),)),
    FRAME_TIME: Profile(FRAME_TIME, 8, (('FrameNumber', 0, FRAME_NUMBER), ('SubFrame', 4, 'FloatProperty'))),
    FRAME_RATE: Profile(FRAME_RATE, 8, (('Numerator', 0, 'IntProperty'), ('Denominator', 4, 'IntProperty'))),
    QUALIFIED_FRAME_TIME: Profile(QUALIFIED_FRAME_TIME, 16, (('Time', 0, FRAME_TIME), ('Rate', 8, FRAME_RATE))),
    VECTOR3: Profile(VECTOR3, 24, tuple((name, i * 8, 'DoubleProperty') for i, name in enumerate('XYZ'))),
    VECTOR: Profile(VECTOR, 16, (('X', 0, 'DoubleProperty'), ('Y', 8, 'DoubleProperty'))),
    COLOR: Profile(COLOR, 16, tuple((name, i * 4, 'FloatProperty') for i, name in enumerate('RGBA'))),
    MARGIN: Profile(MARGIN, 16, tuple((name, i * 4, 'FloatProperty')
                                    for i, name in enumerate(('Left', 'Top', 'Right', 'Bottom')))),
    ANCHORS: Profile(ANCHORS, 32, (('Minimum', 0, VECTOR), ('Maximum', 16, VECTOR))),
})
_FRAME_FLAGS = {
    FRAME_NUMBER: (6755469234274821,),
    FRAME_RATE: (6755469234274821, 6755469234274821),
    FRAME_TIME: (6755468160532484, 20266268116386308),
    QUALIFIED_FRAME_TIME: (6755468160532484, 6755469234274820),
}
_FLOAT_MAX = float.fromhex('0x1.fffffep+127')


@dataclass(frozen=True)
class TimespanValue:
    """Copied signed64 media timing value; this build uses 10,000,000 ticks/second."""
    ticks: int

    def __post_init__(self):
        if type(self.ticks) is not int or not -(1 << 63) <= self.ticks < (1 << 63):
            raise ValueError('Timespan return must be a signed int64')

    @property
    def seconds(self):
        # GetTotalSeconds thunk0x3852de0 multiplies signed ticks by1e-7.
        # Preserve sentinel values; callers decide whether timing is usable.
        return self.ticks / 10_000_000.0


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
    for field_index, (row, (name, offset, kind)) in enumerate(zip(rows, profile.fields)):
        nested = kind in PROFILES
        width = PROFILES[kind].width if nested else 8 if kind == 'DoubleProperty' else 4
        if (row['owner_index'] != observed.index or row['name'] != name or
                row['offset'] != offset or row['element_size'] != width or row['dimension'] != 1 or
                row['type'] != ('StructProperty' if nested else kind)):
            raise ValueError('POD struct field layout changed')
        if path == GUID and (row['flags'] != 6755469251052033 or int(row['vtable_rva'],16) != 0x6e10a98):
            raise ValueError('Guid field flags or native type changed')
        if path in FRAME_PROFILES:
            table = 0x6e136a0 if nested else 0x6e10a98 if kind == 'IntProperty' else 0x6e11560
            if row['flags'] != _FRAME_FLAGS[path][field_index] or int(row['vtable_rva'], 16) != table:
                raise ValueError('Frame timing field flags or native property type changed')
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
    if path == TIMESPAN:
        raise ValueError('Timespan is return-only')
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
        elif kind == 'IntProperty':
            if type(item) is not int or not -(1 << 31) <= item < (1 << 31):
                raise ValueError('Frame integer must be a signed int32')
            struct.pack_into('<i', output, offset, item)
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
    if path == TIMESPAN:
        return TimespanValue(struct.unpack('<q', data)[0])
    result = {}
    for name, offset, kind in profile.fields:
        if kind in PROFILES:
            item = decode(kind, data[offset:offset + PROFILES[kind].width])
        elif kind == 'IntProperty':
            item = struct.unpack_from('<i', data, offset)[0]
        else:
            item = struct.unpack_from('<d' if kind == 'DoubleProperty' else '<f', data, offset)[0]
            if not math.isfinite(item) or abs(item) > _FLOAT_MAX:
                raise ValueError('POD result has an invalid numeric component')
        result[name] = item
    return NumericStructValue(path, result)
