"""Plan typed invocation arguments and decode copied, non-owning results.

Plans are immutable observations, not authority to call an address. The native
game-thread backend must revalidate every identity and layout, materialize object
patches, route through the target's dispatcher, and report execution explicitly.
Opaque/native-owned types require constructors and destructors before support.
"""
from dataclasses import dataclass
import math
import struct

from types import MappingProxyType
from . import ObjectSnapshot, RuntimeQueryError
from .reflection import describe
from . import _pod_values
from .enums import EnumValue, describe_enums, enum_sentinel

PARM, OUT, RETURN, REFERENCE = 0x80, 0x100, 0x400, 0x8000000


class UnsupportedInvocation(ValueError):
    pass


class InvocationError(RuntimeQueryError):
    """Failure with an explicit dispatch outcome. Never retry automatically."""
    def __init__(self, message, *, outcome, native_error=None):
        super().__init__(f'{message} [outcome={outcome}; do not retry automatically]')
        self.outcome, self.native_error = outcome, native_error


@dataclass(frozen=True)
class InvocationResult:
    return_value: object
    outputs: object
    outcome: str = 'dispatch_returned'


def decode_result(plan, reply, catalog, *, texts=()):
    """Decode copied results using a fresh catalog; references are not retained."""
    if reply.outcome != 'dispatch_returned' or reply.error:
        raise InvocationError(f'Native invocation rejected or incomplete ({reply.error})',
                              outcome=reply.outcome, native_error=reply.error)
    try:
        text_values = dict(texts)
        expected_texts = {i for i, p in enumerate(plan.parameters) if p.kind == 'TextProperty'}
        if len(text_values) != len(texts) or set(text_values) != expected_texts:
            raise ValueError('Copied text results do not match parameter identities')
        if expected_texts:
            from ._text_wire import encode_units
            for copied in text_values.values():
                encode_units(copied)
        if catalog.pid != plan.target.pid or len(reply.data) != plan.parameter_size:
            raise ValueError('Result process or parameter extent changed')
        references = {}
        for offset, index, serial, address in reply.objects:
            if offset in references:
                raise ValueError('Duplicate result reference')
            observed = catalog.by_index.get(index)
            if observed is None or observed.serial != serial or observed.address != address:
                raise ValueError('Returned object no longer matches the live registry')
            references[offset] = observed
        value, outputs = None, {}
        valid_slots = set()
        for field_index, parameter in enumerate(plan.parameters):
            values = []
            for element in range(parameter.dimension):
                at = parameter.offset + element * parameter.width
                if parameter.kind in ('ObjectProperty', 'ClassProperty'):
                    valid_slots.add(at)
                    if any(reply.data[at:at + 8]):
                        raise ValueError('Raw pointer in result buffer')
                    item = references.get(at)
                    constraint = catalog.resolve(parameter.constraint)
                    if item is not None:
                        cls = item.index if parameter.kind == 'ClassProperty' else item.class_index
                        if parameter.kind == 'ClassProperty' and cls not in catalog.classes:
                            raise ValueError('Class result is not a class object')
                        if constraint.index not in catalog.ancestors(cls):
                            raise ValueError('Returned object violates its class constraint')
                elif parameter.kind == 'BoolProperty':
                    encoding = parameter.boolean_encoding
                    bits = reply.data[at + ((encoding >> 8) & 255)] & (encoding >> 24)
                    if bits not in (0, (encoding >> 16) & 255):
                        raise ValueError('Invalid result bool encoding')
                    item = bool(bits)
                elif parameter.kind == 'TextProperty':
                    if parameter.width != 16 or parameter.dimension != 1 or any(reply.data[at:at+16]):
                        raise ValueError('Invalid native text result storage')
                    item = text_values[field_index]
                elif parameter.kind == 'StructProperty':
                    item = _pod_values.decode(parameter.pod_profile, reply.data[at:at + parameter.width])
                elif parameter.kind == 'EnumProperty':
                    enum = catalog.resolve(parameter.constraint)
                    number = reply.data[at]
                    matches = [m for m in parameter.enum_members if m.value == number]
                    if parameter.width != 1 or not matches:
                        raise ValueError('Enum result is outside the observed member set')
                    item = EnumValue(enum, matches[0].name, number)
                else:
                    item = struct.unpack_from('<' + _FORMATS[parameter.kind][0], reply.data, at)[0]
                values.append(item)
            decoded = tuple(values) if parameter.dimension > 1 else values[0]
            if parameter.flags & RETURN:
                value = decoded
            elif parameter.flags & OUT:
                outputs[parameter.name] = decoded
        if set(references) - valid_slots:
            raise ValueError('Unexpected result reference slot')
        return InvocationResult(value, MappingProxyType(outputs))
    except (ValueError, KeyError, IndexError, struct.error, RuntimeQueryError) as error:
        raise InvocationError(f'Dispatch returned but result validation failed: {error}',
                              outcome='dispatch_returned') from error


@dataclass(frozen=True)
class Parameter:
    name: str
    kind: str
    offset: int
    width: int
    dimension: int
    flags: int
    boolean_encoding: int | None = None
    constraint: object = None
    pod_profile: str | None = None
    enum_members: tuple = ()

    @property
    def input(self):
        return not self.flags & RETURN and (not self.flags & OUT or bool(self.flags & REFERENCE))


@dataclass(frozen=True)
class ObjectPatch:
    offset: int
    object: ObjectSnapshot


@dataclass(frozen=True)
class CallPlan:
    target: ObjectSnapshot
    function: ObjectSnapshot
    function_flags: int
    entry_rva: int
    parameter_size: int
    allocation_extent: int
    return_offset: int
    parameters: tuple
    data: bytes
    objects: tuple
    wire_version: int = 1
    texts: tuple = ()  # Immutable (parameter name, copied str) input pairs.


_FORMATS = {'ByteProperty': ('B', 1, 0, 255), 'UInt16Property': ('H', 2, 0, 65535),
            'IntProperty': ('i', 4, -2147483648, 2147483647),
            'FloatProperty': ('f', 4, None, None), 'DoubleProperty': ('d', 8, None, None)}


def prepare_call(catalog, target, function, arguments, *, pod_values=False, text_values=False, enum_values=False,
                 _trace_plan=None):
    """Describe a current UFunction and prepare named arguments without executing it.

Zeroed object slots have separate identity patches; caller-supplied integer
addresses are never accepted. All inputs are explicit, with no guessed defaults.
Output/return types must also be supported before a plan can be built.
"""
    if any(type(flag) is not bool for flag in (pod_values, text_values, enum_values)):
        raise ValueError('Value capability flags must be bool')
    pod_values = pod_values or text_values or enum_values
    target, function = catalog.resolve(target), catalog.resolve(function)
    if catalog.find_class('Function').index not in catalog.ancestors(function.class_index):
        raise ValueError('Expected a reflected Function identity')
    if function.outer_index not in catalog.ancestors(target.class_index):
        raise ValueError('Function owner is not in the target class hierarchy')
    if _trace_plan is None:
        descriptor = describe(catalog, (function,))[function.index]
    else:
        # Registered observers retain pre-install metadata because the external
        # reader rejects our DLL thunk as an out-of-image native entry. This is
        # an old observation, not dispatch authority; native validation remains.
        if catalog.resolve(_trace_plan.function) != function:
            raise ValueError('Trace plan belongs to a different function')
        descriptor = _trace_plan.descriptor
    return _prepare(catalog, target, function, descriptor, arguments, pod_values=pod_values, text_values=text_values, enum_values=enum_values)


def _struct_reference(catalog, row):
    obj = catalog.by_index[row['struct_index']]
    if obj.serial != row['struct_serial'] or obj.name != row['struct_name']:
        raise ValueError('POD struct reference changed')
    if obj.class_name != 'ScriptStruct' or catalog.path_name(obj) not in _pod_values.PROFILES:
        raise UnsupportedInvocation('Struct requires an additional verified codec/lifetime contract')
    return obj


def _observed_pod_profile(catalog, row, descriptors):
    obj = _struct_reference(catalog, row)
    pending = {obj.index: obj}
    # Only Anchors -> Vector2D nesting is allowed. Bound metadata acquisition;
    # validate_profile below enforces the actual shape, not just type names.
    for _ in range(2):
        pending = {index: value for index, value in pending.items() if index not in descriptors}
        if not pending:
            break
        current = describe(catalog, pending.values())
        descriptors.update(current)
        nested = [_struct_reference(catalog, field) for d in current.values()
                  for field in d.properties if field['type'] == 'StructProperty']
        pending = {child.index: child for child in nested}
    profile = _pod_values.validate_profile(catalog, descriptors[obj.index], descriptors)
    return obj, profile


def _parameter_schema(catalog, function, descriptor, *, pod_values=False, text_values=False, enum_values=False):
    info = descriptor.function
    if info is None or not descriptor.owners or descriptor.owners[0]['index'] != function.index:
        raise ValueError('Function metadata is missing or inconsistent')
    size, extent, returned = info['params_size'], descriptor.owners[0]['size'], info['return_offset']
    if (type(size) is not int or type(extent) is not int or not 0 <= size <= extent <= 65536 or
            type(returned) is not int or not (returned == 65535 or 0 <= returned < size)):
        raise ValueError('Invalid parameter size, extent or return offset')
    parameters, occupied, names, pod_descriptors = [], set(), set(), {}
    for row in descriptor.properties:
        if not row['flags'] & PARM:
            continue  # Function locals are initialized by the engine dispatcher.
        name, kind = row['name'], row['type']
        offset, width, dimension = row['offset'], row['element_size'], row['dimension']
        if (name in names or type(name) is not str or not name or row['owner_index'] != function.index or
                any(type(value) is not int for value in (offset, width, dimension)) or
                offset < 0 or width <= 0 or not 1 <= dimension <= 64 or offset + width * dimension > size):
            raise ValueError('Invalid or duplicate parameter layout')
        names.add(name)
        if len(names) > 128:
            raise ValueError('Parameter count exceeds 128')
        encoding, constraint, pod_profile = None, None, None
        enum_members = ()
        if kind == 'BoolProperty':
            encoding = int(row['bool_encoding'], 16)
            byte_offset, field_mask = (encoding >> 8) & 255, (encoding >> 24) & 255
            byte_mask, storage_size = (encoding >> 16) & 255, encoding & 255
            if (not 0 < encoding <= 0xffffffff or not field_mask or byte_offset >= width or
                    storage_size != width or byte_mask == 0 or byte_mask & ~field_mask or
                    byte_mask & (byte_mask - 1)):
                raise ValueError('Unsupported bool storage encoding')
            locations = {(offset + element * width + byte_offset, bit)
                         for element in range(dimension) for bit in range(8) if field_mask & (1 << bit)}
        else:
            expected = _FORMATS[kind][1] if kind in _FORMATS else 8 if kind in ('ObjectProperty', 'ClassProperty') else None
            if kind == 'StructProperty' and pod_values:
                constraint, profile = _observed_pod_profile(catalog, row, pod_descriptors)
                pod_profile, expected = profile.path, profile.width
            if kind == 'TextProperty' and text_values:
                if dimension != 1:
                    raise UnsupportedInvocation('TextProperty arrays require a separate ownership contract')
                expected = 16
            if kind == 'EnumProperty' and enum_values:
                if dimension != 1 or row.get('inner_type') != 'ByteProperty' or row.get('inner_element_size') != 1:
                    raise UnsupportedInvocation('Enum invocation currently requires scalar byte-backed storage')
                constraint = catalog.by_index[row['enum_index']]
                if constraint.serial != row['enum_serial'] or constraint.name != row['enum_name']:
                    raise ValueError('Enum parameter identity changed')
                enum_members = describe_enums(catalog, [constraint])[constraint.index].members
                expected = 1
            if expected is None:
                raise UnsupportedInvocation(f'{name}: {kind} needs an additional verified codec/lifetime contract')
            if width != expected:
                raise ValueError('Parameter storage width does not match its codec')
            locations = {(byte, bit) for byte in range(offset, offset + width * dimension) for bit in range(8)}
            if kind in ('ObjectProperty', 'ClassProperty'):
                prefix = 'meta_class' if kind == 'ClassProperty' else 'property_class'
                constraint = catalog.by_index[row[prefix + '_index']]
                if (constraint.serial != row[prefix + '_serial'] or constraint.name != row[prefix + '_name'] or
                        constraint.address != int(row[prefix + '_address'], 16) or constraint.index not in catalog.classes):
                    raise ValueError('Parameter class constraint changed')
        if occupied & locations:
            raise ValueError('Parameter storage overlaps')
        occupied.update(locations)
        parameters.append(Parameter(name, kind, offset, width, dimension, row['flags'], encoding, constraint, pod_profile, enum_members))
    returns = [parameter for parameter in parameters if parameter.flags & RETURN]
    if (len(returns) > 1 or (returned == 65535) != (len(returns) == 0) or
            (returns and (returns[0].offset != returned or returns[0].dimension != 1))):
        raise ValueError('Return property does not match function metadata')
    return size, extent, returned, tuple(parameters)


def _prepare(catalog, target, function, descriptor, arguments, *, pod_values=False, text_values=False, enum_values=False):
    if type(arguments) is not dict or any(type(key) is not str for key in arguments):
        raise ValueError('Arguments must be a dictionary of parameter names')
    size, extent, returned, parameters = _parameter_schema(
        catalog, function, descriptor, pod_values=pod_values, text_values=text_values, enum_values=enum_values)
    info = descriptor.function
    expected_inputs = {parameter.name for parameter in parameters if parameter.input}
    if set(arguments) != expected_inputs:
        raise ValueError(f'Argument names mismatch; missing={sorted(expected_inputs - arguments.keys())}, extra={sorted(arguments.keys() - expected_inputs)}')
    text_fields = [p for p in parameters if p.kind == 'TextProperty']
    enum_fields = [p for p in parameters if p.kind == 'EnumProperty']
    if text_fields and enum_fields:
        raise UnsupportedInvocation('Mixed text/enum transport is not connected yet')
    if len(text_fields) > 8:
        raise UnsupportedInvocation('Text calls support at most eight text fields')
    data, patches, texts = bytearray(size), [], []
    for parameter in parameters:
        if not parameter.input:
            continue
        value = arguments[parameter.name]
        values = value if parameter.dimension > 1 else (value,)
        if type(values) not in (tuple, list) or len(values) != parameter.dimension:
            raise ValueError(f'{parameter.name}: expected exactly {parameter.dimension} elements')
        for index, item in enumerate(values):
            at = parameter.offset + index * parameter.width
            if parameter.kind == 'BoolProperty':
                if type(item) is not bool: raise ValueError(f'{parameter.name}: expected bool')
                if item:
                    data[at + ((parameter.boolean_encoding >> 8) & 255)] |= (parameter.boolean_encoding >> 16) & 255
            elif parameter.kind == 'TextProperty':
                from ._text_wire import encode_units
                encode_units(item)
                texts.append((parameter.name, item))
            elif parameter.kind == 'StructProperty':
                data[at:at + parameter.width] = _pod_values.encode(parameter.pod_profile, item)
            elif parameter.kind == 'EnumProperty':
                if not isinstance(item, EnumValue) or catalog.resolve(item.enum) != parameter.constraint:
                    raise ValueError('Enum argument requires a value of the exact observed enum identity')
                if (type(item.value) is not int or not 0 <= item.value <= 255 or
                        type(item.name) is not str or enum_sentinel(item.name) or
                        any(enum_sentinel(m.name) and m.value == item.value for m in parameter.enum_members) or
                        not any(m.name == item.name and m.value == item.value for m in parameter.enum_members)):
                    raise ValueError('Enum argument is invalid, stale, out of range or a sentinel')
                data[at] = item.value
            elif parameter.kind in ('ObjectProperty', 'ClassProperty'):
                if item is None: continue
                if not isinstance(item, ObjectSnapshot): raise ValueError('Object arguments require observed identities, not addresses')
                item = catalog.resolve(item)
                if parameter.kind == 'ClassProperty' and item.index not in catalog.classes:
                    raise ValueError(f'{parameter.name}: expected a class object')
                class_index = item.index if parameter.kind == 'ClassProperty' else item.class_index
                if parameter.constraint.index not in catalog.ancestors(class_index):
                    raise ValueError(f'{parameter.name}: object violates class constraint')
                patches.append(ObjectPatch(at, item))
            else:
                fmt, _, low, high = _FORMATS[parameter.kind]
                if low is None:
                    try: finite = type(item) in (int, float) and math.isfinite(item)
                    except OverflowError: finite = False
                    if not finite:
                        raise ValueError(f'{parameter.name}: expected finite number')
                elif type(item) is not int or not low <= item <= high:
                    raise ValueError(f'{parameter.name}: integer outside storage range')
                try: struct.pack_into('<' + fmt, data, at, item)
                except (OverflowError, struct.error) as error: raise ValueError(f'{parameter.name}: value cannot fit storage') from error
    return CallPlan(target, function, info['flags'], int(info['entry_rva'], 16), size, extent, returned,
                    tuple(parameters), bytes(data), tuple(patches), 4 if enum_fields else 3 if text_fields else 2 if pod_values else 1,
                    tuple(texts))
