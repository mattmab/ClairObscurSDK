"""Private candidate copy/cleanup protocol; no arbitrary struct codec."""
import struct
SIZE=20984
OPERATIONS={124:3,125:3,126:0,127:4,128:6,129:6,130:6,160:0}
ERRORS=frozenset((407,408,*range(3050,3073),*range(3661,3665)))

class ParameterOperationError(RuntimeError):
    def __init__(self,operation,error):
        self.operation=operation;self.native_error=error
        super().__init__(f'Original battle parameter operation {operation} rejected: {error}; not replayed')

def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:raise ValueError('Expected exact parameter packet')
    version,operation,error,state,owner=struct.unpack_from('<4IQ',packet)
    if version!=3 or operation not in OPERATIONS or error or state or not owner:
        raise ValueError('Invalid parameter request header')
    expected=bytearray(SIZE);struct.pack_into('<4IQ',expected,0,version,operation,0,0,owner)
    if 127<=operation<=130:
        mode=struct.unpack_from('<I',packet,32)[0];anchor_owner=struct.unpack_from('<Q',packet,40)[0]
        if mode>2 or not anchor_owner:raise ValueError('Invalid owned actor policy proof')
        if operation==130 and mode not in (1,2):raise ValueError('Candidate dispatch requires isolated policy')
        expected[32:36]=packet[32:36];expected[40:48]=packet[40:48]
    if 129<=operation<=130:
        if struct.unpack_from('<I',packet,36)[0]>1:raise ValueError('Invalid arena binding policy')
        expected[36:40]=packet[36:40]
    if operation==130:
        track=struct.unpack_from('<I',packet,48)[0]
        if track not in (0,1):raise ValueError('Explicit completion tracking flag required')
        expected[48:52]=packet[48:52]
    for at in range(OPERATIONS[operation]):
        offset=88+at*16;index,serial,address=struct.unpack_from('<iiQ',packet,offset)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff:
            raise ValueError('Invalid exact parameter identity')
        expected[offset:offset+16]=packet[offset:offset+16]
    if bytes(expected)!=packet:raise ValueError('Unexpected parameter request bytes')
    return True

def build_request(owner,operation,identities=(),*,mode=None,anchor_owner=None,arena_policy=None,track_completion=False):
    if type(owner) is not int or not 0<owner<2**64 or type(operation) is not int or operation not in OPERATIONS:
        raise ValueError('Invalid parameter operation or owner')
    identities=tuple(identities)
    if len(identities)!=OPERATIONS[operation]:raise ValueError('Incorrect parameter identity count')
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,operation,0,0,owner)
    if 127<=operation<=130:
        if type(mode) is not int or mode not in (0,1,2) or type(anchor_owner) is not int or not 0<anchor_owner<2**64:
            raise ValueError('Expected exact policy mode and actor-owner token')
        struct.pack_into('<I',packet,32,mode);struct.pack_into('<Q',packet,40,anchor_owner)
    elif mode is not None or anchor_owner is not None:raise ValueError('Unexpected policy arguments')
    if 129<=operation<=130:
        if arena_policy is None:arena_policy=0
        if type(arena_policy) is not int or arena_policy not in (0,1):raise ValueError('Explicit arena policy must be 0 or 1')
        struct.pack_into('<I',packet,36,arena_policy)
    elif arena_policy is not None:raise ValueError('Unexpected arena policy')
    if type(track_completion) is not bool or (track_completion and operation!=130):
        raise ValueError('Completion tracking requires an original entry dispatch')
    if operation==130:struct.pack_into('<I',packet,48,int(track_completion))
    for at,obj in enumerate(identities):
        values=(obj.index,obj.serial,obj.address)
        if any(type(v) is not int for v in values):raise ValueError('Identity fields must be integers')
        struct.pack_into('<iiQ',packet,88+16*at,*values)
    result=bytes(packet);validate_request(result);return result

def validate_response(request,response):
    validate_request(request)
    if type(response) is not bytes or len(response)!=SIZE:raise RuntimeError('Unknown parameter acknowledgement')
    version,operation,error,state,owner=struct.unpack_from('<4IQ',response)
    if (version,operation,owner)!=struct.unpack_from('<II',request)+(struct.unpack_from('<Q',request,16)[0],):
        raise RuntimeError('Parameter acknowledgement identity changed')
    expected=bytearray(request)
    if error:
        if error not in ERRORS or state:raise RuntimeError('Unknown parameter error acknowledgement')
        struct.pack_into('<I',expected,8,error)
    else:
        if state!=1:raise RuntimeError('Missing parameter completion acknowledgement')
        struct.pack_into('<I',expected,12,1)
        if operation==160:
            from ._battle_completion import decode
            decode(response[4096:4192],owner=owner)
            expected[4096:4192]=response[4096:4192]
        elif operation!=126:
            flags=(1,0,0) if operation==124 else (1,1,1)
            if struct.unpack_from('<3I',response,4096)!=flags:raise RuntimeError('Parameter lifecycle result did not verify')
            expected[4096:4108]=response[4096:4108]
        if 127<=operation<=130:
            mode,before,after,verified=struct.unpack_from('<4I',response,4108)
            if (mode!=struct.unpack_from('<I',request,32)[0] or not 0<=before<=64 or
                after!=(0 if mode==1 else before) or verified!=1):
                raise RuntimeError('Owned policy readback did not verify')
            expected[4108:4124]=response[4108:4124]
        if 128<=operation<=130:
            flags=(1,1,1) if operation==130 else (1,0,0)
            if struct.unpack_from('<3I',response,4124)!=flags:raise RuntimeError('Entry acknowledgement did not verify')
            expected[4124:4136]=response[4124:4136]
        if 129<=operation<=130:
            if struct.unpack_from('<3I',response,4136)!=(1,1,1):raise RuntimeError('Owned arena acknowledgement did not verify')
            expected[4136:4148]=response[4136:4148]
    if bytes(expected)!=response:raise RuntimeError('Parameter acknowledgement changed input or reserved bytes')
    if error:raise ParameterOperationError(operation,error)
    return True
