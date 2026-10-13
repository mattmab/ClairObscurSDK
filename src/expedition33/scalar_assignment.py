"""Identity-checked, game-thread compare-and-set for four observed scalar types."""
import math
import struct
from . import _query, RuntimeQueryError
from .catalog import capture_selected
from .assignment import AssignmentResult
from .invocation import InvocationError
from . import _assignment_wire as wire

PROFILES = {'BoolProperty': (1, 1, 0x6e119b0), 'IntProperty': (2, 4, 0x6e10a98),
            'FloatProperty': (3, 4, 0x6e11560), 'DoubleProperty': (4, 8, 0x6e11788)}

def bits(kind, value):
    if kind == 1:
        if type(value) is not bool: raise ValueError('Expected a boolean')
        return int(value)
    if kind == 2:
        if type(value) is not int or not -(2**31) <= value < 2**31:
            raise ValueError('Expected a signed 32-bit integer')
        return value & 0xffffffff
    if type(value) not in (int, float):
        raise ValueError('Expected a finite number')
    try: finite = math.isfinite(value)
    except OverflowError: finite = False
    if not finite: raise ValueError('Expected a finite number')
    try: packed = struct.pack('<f' if kind == 3 else '<d', value)
    except (OverflowError, struct.error): raise ValueError('Number exceeds property range') from None
    if not math.isfinite(struct.unpack('<f' if kind == 3 else '<d', packed)[0]):
        raise ValueError('Number exceeds property range')
    return int.from_bytes(packed, 'little')

def packet(obj, owner, metadata, expected, value, token):
    kind, width, table = PROFILES[metadata['type']]
    if metadata['dimension'] != 1 or metadata['element_size'] != width or int(metadata['vtable_rva'],16) != table:
        raise ValueError('Unsupported scalar descriptor')
    flags = int(metadata['flags'],16) if isinstance(metadata['flags'],str) else metadata['flags']
    if flags & (0x80 | 0x20000 | 0x20): raise ValueError('Parameter, edit-constant or replicated property is not editable')
    name = metadata['name'].encode('ascii')
    if not 0 < len(name) < 96 or b'\0' in name: raise ValueError('Invalid property name')
    result = bytearray(232)
    struct.pack_into('<IIQ', result, 0, 2, 0, token)
    for offset, ref in ((32, obj),(48, owner)):
        struct.pack_into('<iiQ', result, offset, ref.index, ref.serial, ref.address)
    struct.pack_into('<IIQQQ', result, 64, kind, width, table, bits(kind,expected), bits(kind,value))
    if kind == 1:
        encoding = metadata['bool_encoding']
        struct.pack_into('<I',result,96,int(encoding,16) if isinstance(encoding,str) else encoding)
    struct.pack_into('<QIII96s', result,112,flags,metadata['offset'],1,0,name)
    return bytes(result)

def assign(session, obj, name, value, *, expected, allow_mutation, catalog=None):
    if allow_mutation is not True: raise ValueError('Scalar assignment requires allow_mutation=True')
    if not session.supports_scalar_assignment: raise ValueError('Runtime does not support scalar assignment')
    if obj.pid != session.pid: raise ValueError('Target belongs to a different process')
    if type(name) is not str or not name or any(c in name for c in ';|\r\n\t\0'):
        raise ValueError('Invalid property name')
    catalog = catalog or capture_selected(obj.pid, ((obj.index,obj.serial,obj.address),))
    obj = catalog.resolve(obj)
    selector=f'{obj.index}:{obj.serial}:{obj.address:x};{name}'
    start, rows = _query(['--read-values',str(obj.pid),selector])
    if start['pid'] != obj.pid: raise ValueError('Process changed')
    matches=[r for r in rows if r.get('event')=='property_metadata' and r.get('name')==name]
    if len(matches)!=1: raise ValueError('Property missing or ambiguous')
    metadata=matches[0]
    if metadata['type'] not in PROFILES: raise ValueError('Only bool, int32, float32 and float64 are editable')
    owner=catalog.by_index[metadata['owner_index']]
    packet(obj,owner,metadata,expected,value,1) # Reject input before retention.
    lease=session.retain(obj)
    try:
        sent=packet(obj,owner,metadata,expected,value,lease._token)
        try:
            reply=session._transport.command('object-assign',sent)
            error,outcome=wire.decode(sent,reply['assignment_packet'])
        except (RuntimeQueryError, ValueError, KeyError) as error:
            session._abort_ownership()
            raise InvocationError('Scalar assignment acknowledgement unavailable',outcome='unknown') from error
        if outcome=='unknown': session._abort_ownership()
        if error: raise InvocationError('Native scalar assignment rejected',outcome=outcome,native_error=error)
        return AssignmentResult(obj,owner,name,0,expected,value)
    finally:
        if lease.active: lease.release()
