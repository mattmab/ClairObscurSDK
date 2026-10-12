"""Observation-only trace schemas. No hooks are installed by this module.

Native registration must independently revalidate identities and every property,
resolve out records by property identity, and verify the supported frame path.
"""
from dataclasses import dataclass
import struct
from types import MappingProxyType

from .reflection import describe
from .invocation import _parameter_schema, _FORMATS, RETURN, OUT


@dataclass(frozen=True)
class TraceField:
    parameter: int
    element: int
    source: str
    source_offset: int
    destination_offset: int
    size: int
    boolean_mask: int = 0
    boolean_true: int = 0


@dataclass(frozen=True)
class TracePlan:
    function: object
    function_flags: int
    entry_rva: int
    parameter_size: int
    allocation_extent: int
    return_offset: int
    parameters: tuple
    fields: tuple
    capture_size: int
    descriptor: object
    phase: str = 'post'


@dataclass(frozen=True)
class ObservedObject:
    """Copied identity at event time; not a retained or dereferenceable UObject.

    Serial zero is allowed as an observation, never a lifetime guarantee.
    """
    session: int
    pid: int
    index: int
    serial: int
    address: int


@dataclass(frozen=True)
class TraceValues:
    arguments: object
    return_value: object


def decode_trace(plan, data, *, session=0):
    """Decode an owned scalar POST payload using its registration's trace plan.

    This does not validate a transport session or event identity. The transport
    must pair each payload with the exact retained registration plan first.
    Floating-point NaNs/infinities are observations and are not coerced.
    """
    if not isinstance(data, bytes) or len(data) != plan.capture_size:
        raise ValueError('Trace payload must be owned bytes of the planned extent')
    values = [[None] * parameter.dimension for parameter in plan.parameters]
    for field in plan.fields:
        parameter = plan.parameters[field.parameter]
        at = field.destination_offset
        if parameter.kind == 'BoolProperty':
            bits = data[at] & field.boolean_mask
            if bits not in (0, field.boolean_true):
                raise ValueError('Invalid trace bool encoding')
            value = bool(bits)
        elif parameter.kind == 'ObjectProperty' and plan.phase == 'entry':
            index, serial, address = struct.unpack_from('<iiQ', data, at)
            if index == -1 and serial == 0 and address == 0:
                value = None
            elif index < 0 or serial < 0 or address < 0x10000 or address & 7 or not 0 < session < 2**64:
                raise ValueError('Invalid observed object identity or session')
            else:
                value = ObservedObject(session, plan.function.pid, index, serial, address)
        else:
            value = struct.unpack_from('<' + _FORMATS[parameter.kind][0], data, at)[0]
        values[field.parameter][field.element] = value
    arguments, returned = {}, None
    for parameter, items in zip(plan.parameters, values):
        value = items[0] if parameter.dimension == 1 else tuple(items)
        if parameter.flags & RETURN:
            returned = value
        else:
            arguments[parameter.name] = value
    return TraceValues(MappingProxyType(arguments), returned)


def prepare_trace(catalog, function, *, blueprint=False):
    """Plan copied scalar POST fields for any described native function.

Object identities and owned-value codecs are not implemented for traces yet.
Their layouts must not silently fall back to copying pointer-bearing bytes.
"""
    function = catalog.resolve(function)
    if catalog.find_class('Function').index not in catalog.ancestors(function.class_index):
        raise ValueError('Expected a reflected Function identity')
    descriptor = describe(catalog, (function,))[function.index]
    size, extent, returned, parameters = _parameter_schema(catalog, function, descriptor)
    info = descriptor.function
    entry = int(info['entry_rva'], 16)
    is_blueprint = not info['flags'] & 0x400
    if is_blueprint:
        expected = (('TargetCharacter', 'ObjectProperty'), ('SourceCharacter', 'ObjectProperty'),
                    ('ReceivedDamages', 'DoubleProperty'), ('BattleDamages', 'ObjectProperty'))
        owner = catalog.by_index[function.outer_index]
        if not (blueprint and function.name == 'OnCharacterReceivedDamages' and
                owner.name == 'BP_BattleSummaryStatsManager_C' and info['flags'] == 0x0c020000 and
                entry == 0x13937a0 and size == 32 and returned == 65535 and
                tuple((p.name, p.kind) for p in parameters) == expected and
                all(p.offset == i*8 and p.width == 8 and p.dimension == 1 and not p.flags & (OUT | RETURN)
                    for i, p in enumerate(parameters))):
            raise ValueError('Bytecode-originated trace schemas require separate frame validation')
    if not 0 < entry < 166776832 or size > 4096:
        raise ValueError('Trace entry or parameter size exceeds this build profile')
    fields, destination = [], 0
    for index, parameter in enumerate(parameters):
        if parameter.kind not in _FORMATS and parameter.kind != 'BoolProperty' and not (is_blueprint and parameter.kind == 'ObjectProperty'):
            raise ValueError(parameter.kind + ' requires a trace-specific identity/value codec')
        source = 'return' if parameter.flags & RETURN else 'out' if parameter.flags & OUT else 'locals'
        base = parameter.offset if source == 'locals' else 0
        for element in range(parameter.dimension):
            offset = base + element * parameter.width
            width, mask, true = parameter.width, 0, 0
            if parameter.kind == 'BoolProperty':
                encoding = parameter.boolean_encoding
                offset += (encoding >> 8) & 255
                width, mask, true = 1, (encoding >> 24) & 255, (encoding >> 16) & 255
            elif parameter.kind == 'ObjectProperty':
                width = 16
            fields.append(TraceField(index, element, source, offset, destination, width, mask, true))
            destination += width
    if len(fields) > 128 or destination > 4096:
        raise ValueError('Trace normalized capture exceeds bounded capacity')
    return TracePlan(function, info['flags'], entry, size, extent, returned, parameters,
                     tuple(fields), destination, descriptor, 'entry' if is_blueprint else 'post')
