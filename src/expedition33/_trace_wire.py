"""Candidate trace protocol. Encoding alone never installs an observer."""
from dataclasses import dataclass
import struct
from types import SimpleNamespace
from . import _invocation_wire as call

HEADER = struct.Struct('<IIQQ4IiiQ')
OUTPUT = struct.Struct('<6IQ')
EVENT = struct.Struct('<QQIIiiI')
SCHEMA_AT, OUTPUT_AT, EVENTS_AT = 56, 24704, 24736
EVENT_SIZE, SIZE, CAPACITY = 4132, 57792, 8
OPERATIONS = {'start': 1, 'stop': 2, 'drain': 3, 'status': 4, 'forget': 5}


def encode_request(operation, owner, registration=0, *, plan=None, exemplar=None,
                   target=None, duration_ms=10000, limit=100):
    op = OPERATIONS[operation]
    if type(owner) is not int or not 0 < owner < 2**64:
        raise ValueError('Trace owner must be a nonzero uint64')
    if type(registration) is not int or not 0 <= registration < 2**64:
        raise ValueError('Invalid trace registration')
    packet = bytearray(SIZE)
    filter_id = (-1, 0, 0)
    if op == 1:
        if (registration or plan is None or exemplar is None or
                type(duration_ms) is not int or not 1 <= duration_ms <= 300000 or
                type(limit) is not int or not 1 <= limit <= 1000):
            raise ValueError('Invalid trace start parameters')
        if exemplar.pid != plan.function.pid or (target is not None and target.pid != exemplar.pid):
            raise ValueError('Trace identities must belong to the same process')
        if target is not None:
            filter_id = call._identity(target)
            if target.serial < 0 or target.address < 0x10000 or target.address & 7:
                raise ValueError('Invalid trace target identity')
        if any(p.kind not in call.KINDS[:6] for p in plan.parameters):
            raise ValueError('Unsupported trace codec')
        schema = call.encode_plan(SimpleNamespace(
            **{name: getattr(plan, name) for name in ('function', 'parameter_size',
                'allocation_extent', 'return_offset', 'function_flags', 'entry_rva', 'parameters')},
            target=exemplar, objects=(), data=bytes(plan.parameter_size), wire_version=1))
        packet[SCHEMA_AT:OUTPUT_AT] = schema
    else:
        if not registration or plan is not None or exemplar is not None or target is not None:
            raise ValueError('Trace control requires only an existing registration')
        duration_ms = limit = 0
    HEADER.pack_into(packet, 0, 1, op, owner, registration, duration_ms, limit,
                     int(target is not None), 0, *filter_id)
    return bytes(packet)


@dataclass(frozen=True)
class TraceEvent:
    sequence: int
    monotonic_ms: int
    thread: int
    pid: int
    index: int
    serial: int
    data: bytes


@dataclass(frozen=True)
class TraceReply:
    registration: int
    error: int
    state: int
    cleanup: int
    observed: int
    dropped: int
    rejected: int
    events: tuple


def decode_reply(request, encoded, *, expected_pid):
    if type(request) is not bytes or len(request) != SIZE:
        raise ValueError('Invalid trace request size')
    if type(encoded) is not str or len(encoded) != SIZE * 2:
        raise ValueError('Invalid trace reply size')
    reply = bytes.fromhex(encoded)
    if len(reply) != SIZE:
        raise ValueError('Invalid trace reply encoding')
    sent, got = HEADER.unpack_from(request), HEADER.unpack_from(reply)
    if got[:3] != sent[:3] or got[4:] != sent[4:] or reply[SCHEMA_AT:OUTPUT_AT] != request[SCHEMA_AT:OUTPUT_AT]:
        raise ValueError('Trace reply does not match its request')
    error, state, cleanup, count, observed, dropped, rejected = OUTPUT.unpack_from(reply, OUTPUT_AT)
    if (state > 5 or cleanup > 4 or count > CAPACITY or observed > 1000 or dropped > observed or
            (count and sent[1] != 3) or (error and count)):
        raise ValueError('Invalid trace reply counters or state')
    if sent[1] == 1:
        if bool(got[3]) != (error == 0):
            raise ValueError('Invalid trace start registration')
    elif got[3] != sent[3]:
        raise ValueError('Trace registration changed')
    events, previous = [], 0
    for i in range(count):
        at = EVENTS_AT + i * EVENT_SIZE
        sequence, time, thread, pid, index, serial, size = EVENT.unpack_from(reply, at)
        if (not previous < sequence <= observed or not thread or pid != expected_pid or
                not pid or index < 0 or serial < 0 or size > call.MAX_BYTES):
            raise ValueError('Invalid trace event identity or extent')
        start = at + EVENT.size
        if any(reply[start + size:at + EVENT_SIZE]):
            raise ValueError('Nonzero trace event tail')
        events.append(TraceEvent(sequence, time, thread, pid, index, serial, reply[start:start + size]))
        previous = sequence
    if any(reply[EVENTS_AT + count * EVENT_SIZE:]):
        raise ValueError('Unexpected unused trace events')
    return TraceReply(got[3], error, state, cleanup, observed, dropped, rejected, tuple(events))
