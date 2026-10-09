"""Candidate copied-text envelope. No transport capability or engine dispatch."""
from dataclasses import dataclass, replace
import struct
from . import _invocation_wire as call
from . import _retained_wire as retained

VERSION, KIND, MAX_SLOTS, MAX_UNITS = 3, 13, 8, 4096
HEADER, SLOT_HEADER = struct.Struct('<II'), struct.Struct('<II')
SLOT_SIZE = SLOT_HEADER.size + 2 * MAX_UNITS
SLOTS_AT = retained.SIZE + HEADER.size
SIZE = SLOTS_AT + MAX_SLOTS * SLOT_SIZE
assert SIZE == 91800


def encode_units(value):
    if type(value) is not str or '\0' in value:
        raise ValueError('Text arguments require str without embedded NUL')
    try:
        encoded = value.encode('utf-16-le') + b'\0\0'
    except UnicodeError as error:
        raise ValueError('Text contains an unpaired surrogate') from error
    if len(encoded) > MAX_UNITS * 2:
        raise ValueError('Text exceeds 4095 UTF-16 content units')
    return encoded


def encode_plan(plan, values):
    """Encode exact TextProperty inputs; zero native values are never pointers.

The public planner does not yet produce version3. This private codec is a
prerequisite for the next explicitly gated native capability.
"""
    if type(plan.wire_version) is not int or plan.wire_version != VERSION or type(values) is not dict:
        raise ValueError('Expected a candidate version3 plan and exact text inputs')
    fields = [(i,p) for i,p in enumerate(plan.parameters) if p.kind == 'TextProperty']
    if not 0 < len(fields) <= MAX_SLOTS:
        raise ValueError('Text calls require one through eight text fields')
    if set(values) != {p.name for _,p in fields if p.input}:
        raise ValueError('Missing or unexpected text arguments')
    normalized = list(plan.parameters)
    for i,p in fields:
        if (p.width != 16 or p.dimension != 1 or p.boolean_encoding or p.constraint is not None or
                p.pod_profile is not None or p.offset < 0 or p.offset+16 > plan.parameter_size or
                any(plan.data[p.offset:p.offset+16])):
            raise ValueError('Invalid TextProperty layout or nonzero native value')
        normalized[i] = replace(p,kind='UInt16Property',width=2,dimension=8)
    packet = bytearray(SIZE)
    packet[:retained.SIZE] = retained.encode_plan(replace(plan,parameters=tuple(normalized),wire_version=2))
    struct.pack_into('<I',packet,0,VERSION)
    HEADER.pack_into(packet,retained.SIZE,1,len(fields))
    for slot,(i,p) in enumerate(fields):
        at=call.FIELDS_AT+i*call.FIELD.size
        struct.pack_into('<4I',packet,at,KIND,p.offset,16,1)
        encoded=encode_units(values[p.name]) if p.input else b''
        at=SLOTS_AT+slot*SLOT_SIZE
        SLOT_HEADER.pack_into(packet,at,i,len(encoded)//2)
        packet[at+SLOT_HEADER.size:at+SLOT_HEADER.size+len(encoded)]=encoded
    return bytes(packet)


@dataclass(frozen=True)
class TextCallReply:
    call: object
    leases: tuple
    texts: tuple  # (field index, copied str); owns no native state.


def decode_reply(request, encoded):
    if type(request) is not bytes or len(request)!=SIZE or type(encoded) is not str or len(encoded)!=SIZE*2:
        raise ValueError('Invalid text reply extent')
    received=bytes.fromhex(encoded)
    if len(received)!=SIZE or call.HEADER.unpack_from(request)[0]!=VERSION:
        raise ValueError('Invalid text packet version or encoding')
    version,count=HEADER.unpack_from(request,retained.SIZE)
    if version!=1 or not 0<count<=MAX_SLOTS or HEADER.unpack_from(received,retained.SIZE)!=(version,count):
        raise ValueError('Text envelope does not match request')
    result,leases=retained.decode_reply(request[:retained.SIZE],received[:retained.SIZE].hex())
    if result.outcome!='dispatch_returned':
        return TextCallReply(result,leases,())
    field_count=call.HEADER.unpack_from(request)[6]
    expected=[]
    for i in range(field_count):
        kind,offset,width,dimension,flags,*_=call.FIELD.unpack_from(request,call.FIELDS_AT+i*call.FIELD.size)
        if kind==KIND:
            if width!=16 or dimension!=1 or offset+16>len(result.data) or any(result.data[offset:offset+16]):
                raise ValueError('Raw or malformed native text in result')
            expected.append((i,flags))
    if len(expected)!=count:
        raise ValueError('Text field count mismatch')
    texts=[]
    for slot,(index,flags) in enumerate(expected):
        at=SLOTS_AT+slot*SLOT_SIZE
        sent_index,_=SLOT_HEADER.unpack_from(request,at)
        field_index,units=SLOT_HEADER.unpack_from(received,at)
        if sent_index!=index or field_index!=index or not 0<units<=MAX_UNITS:
            raise ValueError('Invalid text result identity or length')
        data=received[at+SLOT_HEADER.size:at+SLOT_HEADER.size+units*2]
        if data[-2:]!=b'\0\0' or any(received[at+SLOT_HEADER.size+units*2:at+SLOT_SIZE]):
            raise ValueError('Malformed text result terminator or padding')
        try:
            value=data[:-2].decode('utf-16-le')
        except UnicodeError as error:
            raise ValueError('Invalid UTF-16 result') from error
        if '\0' in value:
            raise ValueError('Embedded NUL in result')
        if not flags & 0x500 and received[at:at+SLOT_SIZE]!=request[at:at+SLOT_SIZE]:
            raise ValueError('Input-only text unexpectedly changed')
        texts.append((index,value))
    if any(received[SLOTS_AT+count*SLOT_SIZE:]):
        raise ValueError('Unexpected unused text slots')
    return TextCallReply(result,leases,tuple(texts))
