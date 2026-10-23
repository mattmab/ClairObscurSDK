"""Exact owned-enemy adapter packets. Independent of reflection value codecs."""
import math
import struct

class EnemyOperationError(RuntimeError):
    def __init__(self,operation,native_error):
        self.operation=operation;self.native_error=native_error
        reasons={
            3030:'Owned original class-default retention, identity stabilization or release failed; cleanup remains owned',
            3020:'Authored route class or actual encounter table identity failed preflight',
            3021:'Original encounter table accessor bytes did not match',
            3022:'Original encounter row structure schema did not match',
            3023:'Exact authored row was absent, ambiguous or unstable in the live sparse map',
            3024:'Authored override transaction could not begin',
            3025:'Original class default object identity/name failed preflight',
            3026:'Original private/default encounter array schema failed preflight',
            3027:'Private array isolation, table or original default row failed preflight',
            3028:'Preconstruction selected encounter or mutation readback did not match',
            3010:'Authored encounter requires an owned prepared uninitialized world enemy; no replay',
            3011:'Authored instance route, exact live table row or private array did not verify; cleanup required',
            3012:'Authored encounter was not preserved by original initialization or activation; actor retained for cleanup',
            3013:'Original campaign instance actions are not verified for this authored route; isolated mode only',
            2993:'Owned original helper lookup context or exact original engine function could not be verified',
            2994:'The original class lookup did not select the owned helper',
            3000:'Added combatant, active owned encounter or inactive movement context could not be verified',
            3001:'This combat position was already attempted; no replay',
            3002:'Original combat home-refresh function or property schemas could not be verified',
            3003:'Combat placement context changed after movement; outcome remains journaled',
            3004:'Original combat home position did not match the placed actor; outcome remains journaled',
            2980:'Extra positions require an initialized owned enemy',
            2983:'Original arena, component classes, schemas or available leases failed preflight',
            2984:'Extra position creation failed; partial ownership remains journaled for cleanup',
            2985:'Original child-actor lookup did not verify all required positions',
            2987:'Extra position cleanup remains pending',
            2988:'Owned enemy world/controller/pawn prerequisites changed',
            2989:'Owned enemy has no verified arena binding',
            2990:'An extra-position transaction already has pending native work',
            2991:'An extra-position prerequisite identity changed',
            2992:'Requested arena differs from the owned enemy bound arena',
            2952:'Owned arena binding prerequisites could not be verified',
            2953:'Authored data-layer dependencies need validation; no layers were cleared',
            2956:'The assigned arena reference did not verify',
            2957:'Native soft-reference temporary cleanup remains pending',
            2960:'Current world/controller/pawn clearance context could not be verified',
            2961:'Clearance query or volume validation failed',
            2970:'Prepared enemy components or placement function schemas could not be verified',
            2971:'Measured capsule or mesh bounds are invalid',
            2972:'Ground support could not be verified across all footprint samples',
            2973:'Ground height varies by more than 100 cm across the capsule footprint',
            2974:'The capsule volume is blocked or clearance could not be verified',
            2975:'Placement readback or owned initial-transform rebasing failed',
            2976:'Prepared enemy placement, arena binding or activation is incomplete',
        }
        reason='; '+reasons[native_error] if native_error in reasons else ''
        super().__init__(f'Owned-enemy adapter rejected/partially failed: error={native_error}{reason}; not retried')


class EnemyCleanupDeferred(EnemyOperationError):
    """Acknowledged cleanup observation deferral; native ownership remains held."""


SIZE=20984
OPERATIONS={110:12,111:0,112:2,113:1,114:1,115:7,116:14,117:5,118:4,119:6,120:13,121:9,122:8,123:7,131:1,132:8,133:15}


def validate_request(packet):
    if type(packet) is not bytes or len(packet)!=SIZE:
        raise ValueError('Expected an exact owned-enemy packet')
    version,operation,error,state,owner=struct.unpack_from('<4IQ',packet)
    if version!=3 or operation not in OPERATIONS or error or state or not owner:
        raise ValueError('Invalid owned-enemy request header')
    canonical=bytearray(SIZE)
    struct.pack_into('<4IQ',canonical,0,version,operation,0,0,owner)
    for i in range(OPERATIONS[operation]):
        offset=88+i*16
        index,serial,address=struct.unpack_from('<iiQ',packet,offset)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff:
            raise ValueError('Invalid observed enemy identity')
        canonical[offset:offset+16]=packet[offset:offset+16]
    if operation==133:
        route=struct.unpack_from('<I',packet,32)[0]
        if route not in (1,2,3,4,5,6,7,8,9,10,11,12):raise ValueError('Unknown authored instance route')
        struct.pack_into('<I',canonical,32,route)
    if operation in (110,120,133):
        pose=struct.unpack_from('<12d',packet,2000)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in pose):
            raise ValueError('Invalid enemy spawn transform')
        if not .999<=sum(v*v for v in pose[:4])<=1.001 or pose[7]!=0 or pose[11]!=0 or pose[8:11]!=(1.,1.,1.):
            raise ValueError('Enemy spawn requires a normalized rotation and original unit scale')
        canonical[2000:2096]=packet[2000:2096]
    elif operation==123:
        destination=struct.unpack_from('<3d',packet,2000)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in destination):
            raise ValueError('Invalid experimental combat destination')
        canonical[2000:2024]=packet[2000:2024]
    elif operation==119:
        probe=struct.unpack_from('<6d',packet,2000)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in probe) or any(v<=0 or v>1e5 for v in probe[3:]):
            raise ValueError('Invalid enemy clearance volume')
        canonical[2000:2048]=packet[2000:2048]
    elif operation==122:
        total=struct.unpack_from('<I',packet,32)[0]
        if not 5<=total<=10:raise ValueError('Experimental battle position count must be 5..10')
        struct.pack_into('<I',canonical,32,total)
    elif operation==112:
        mode=struct.unpack_from('<I',packet,32)[0]
        if mode not in (0,1):raise ValueError('Unknown encounter policy')
        struct.pack_into('<I',canonical,32,mode)
    if bytes(canonical)!=packet:
        raise ValueError('Nonzero reserved or response bytes in enemy request')
    return True


def validate_response(request, response):
    """Accept only the adapter's documented response fields; never retry."""
    validate_request(request)
    if type(response) is not bytes or len(response)!=SIZE:
        raise RuntimeError('Owned-enemy acknowledgement has an invalid size; not retried')
    version,operation,error,state,owner=struct.unpack_from('<4IQ',response)
    if (version,operation,owner)!=(3,struct.unpack_from('<I',request,4)[0],struct.unpack_from('<Q',request,16)[0]):
        raise RuntimeError('Owned-enemy acknowledgement identity mismatch; not retried')
    if error:
        if operation in (115,132) and (error,struct.unpack_from('<d',response,4096)[0]) in ((2933,122),(2934,129)):
            values=struct.unpack_from('<24d',response,4096)
            expected=bytearray(request);struct.pack_into('<I',expected,8,error)
            expected[4096:4288]=response[4096:4288]
            if (bytes(expected)!=response or any(not math.isfinite(v) or abs(v)>1e8 for v in values)
                or (error==2933 and (values[1] not in range(9) or values[2] not in (1,3)))
                or (error==2934 and (values[1:3]!=(9.,4.) or values[23]-values[22]<=250))):
                raise RuntimeError('Invalid ground failure diagnostic; not retried')
            failure=EnemyOperationError(operation,error)
            failure.diagnostic=dict(sample_index=int(values[1]),result=int(values[2]),start=values[3:6],end=values[6:9],
                assembly_extent=values[9:12],assembly_center=values[12:15],pawn_location=values[15:18],
                footprint_center=values[18:20],distance=values[20],radius=values[21],ground_min=values[22],ground_max=values[23])
            raise failure
        if operation==111 and error==407:
            deferred=bytearray(request);struct.pack_into('<I',deferred,8,407)
            if bytes(deferred)!=response:
                raise RuntimeError('Invalid deferred enemy cleanup acknowledgement; not retried')
            raise EnemyCleanupDeferred(operation,error)
        raise EnemyOperationError(operation,error)
    if state!=(0 if operation==111 else 1):
        raise RuntimeError('Owned-enemy acknowledgement state mismatch; not retried')
    canonical=bytearray(request)
    struct.pack_into('<II',canonical,8,0,state)
    if operation in (110,112,120,131,133):
        index,serial,address=struct.unpack_from('<iiQ',response,4096)
        if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff:
            raise RuntimeError('Owned-enemy acknowledgement actor identity invalid; not retried')
        canonical[4096:4112]=response[4096:4112]
    elif operation==123:
        values=struct.unpack_from('<12d',response,4096)
        destination=struct.unpack_from('<3d',request,2000)
        if (any(not math.isfinite(v) or abs(v)>1e8 for v in values) or
            math.dist(values[6:8],destination[:2])>1 or not -1<=values[8]-destination[2]<=20 or
            math.dist(values[:3],values[6:9])>2020 or
            any(abs(math.remainder(math.remainder(a,360)-math.remainder(b,360),360))>1e-3
                for a,b in zip(values[3:6],values[9:12]))):
            raise RuntimeError('Combat position or preserved rotation did not verify; not retried')
        canonical[4096:4192]=response[4096:4192]
    elif operation==122:
        total=struct.unpack_from('<I',request,32)[0]
        if struct.unpack_from('<Q',response,4096)[0]!=(1<<total)-1:
            raise RuntimeError('Extra battle positions did not acknowledge the required slot mask; not retried')
        canonical[4096:4104]=response[4096:4104]
    elif operation==114:
        before=struct.unpack_from('<I',response,4096)[0]
        if before>4:raise RuntimeError('Invalid original visual tick policy; not retried')
        canonical[4096:4100]=response[4096:4100]
    elif operation in (115,132):
        values=struct.unpack_from('<24d',response,4096)
        if any(not math.isfinite(v) or abs(v)>1e8 for v in values):
            raise RuntimeError('Invalid visual placement result; not retried')
        canonical[4096:4288]=response[4096:4288]
    elif operation==121:
        values=struct.unpack_from('<30d',response,4096)
        if any(not math.isfinite(v) or abs(v)>1e8 for v in values) or values[28]!=9 or values[29]!=1:
            raise RuntimeError('Invalid grounded placement acknowledgement; not retried')
        canonical[4096:4336]=response[4096:4336]
    elif operation==119:
        blocked=struct.unpack_from('<I',response,4096)[0]
        if blocked>1:raise RuntimeError('Invalid clearance observation; not retried')
        canonical[4096:4100]=response[4096:4100]
    elif operation==118:
        for offset in (4096,4112):
            index,serial,address=struct.unpack_from('<iiQ',response,offset)
            if index<0 or serial<0 or not 0x10000<=address<=0x7fffffffffff:
                raise RuntimeError('Invalid arena binding acknowledgement identity; not retried')
        canonical[4096:4128]=response[4096:4128]
    elif operation==117:
        enemy_mask,party_mask,slots,enabled,transforms,reserved=struct.unpack_from('<2Q4I',response,4096)
        if slots!=7 or enabled>1 or transforms!=17 or reserved or enemy_mask.bit_count()!=4 or party_mask.bit_count()!=3:
            raise RuntimeError('Invalid arena assembly observation; not retried')
        canonical[4096:4128]=response[4096:4128]
    elif operation==116:
        values=struct.unpack_from('<6d',response,4096)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in values):
            raise RuntimeError('Invalid pawn pose result; not retried')
        canonical[4096:4144]=response[4096:4144]
    if bytes(canonical)!=response:
        raise RuntimeError('Owned-enemy acknowledgement changed reserved or input bytes; not retried')
    return True


def exchange(transport, request):
    """Use normal SDK transport and validate its acknowledgement exactly once."""
    validate_request(request)
    reply=transport.command('mesh',request)
    try:
        response=bytes.fromhex(reply['mesh_packet'])
    except (KeyError,TypeError,ValueError) as error:
        raise RuntimeError('Malformed owned-enemy acknowledgement; not retried') from error
    validate_response(request,response)
    return response


def build_request(owner, operation, identities=(), pose=(), policy=0, *, total_count=None, authored_route=None):
    """Build the exact native request, rejecting ignored or truncated inputs.

    Identities are observed objects exposing index, serial and address. This
    internal wire helper neither discovers actors nor changes their ownership.
    """
    if type(owner) is not int or not 0 < owner < 2**64:
        raise ValueError('Expected a nonzero unsigned owner ID')
    if type(operation) is not int or operation not in OPERATIONS:
        raise ValueError('Unknown owned-enemy operation')
    if operation==133:
        if type(authored_route) is not int or authored_route not in (1,2,3,4,5,6,7,8,9,10,11,12):raise ValueError('Unknown authored instance route')
    elif authored_route is not None:raise ValueError('Unexpected authored instance route')
    if operation==122:
        if type(total_count) is not int or not 5<=total_count<=10:raise ValueError('Experimental battle position count must be 5..10')
    elif total_count is not None:raise ValueError('Unexpected battle position count')
    identities, pose = tuple(identities), tuple(pose)
    if len(identities) != OPERATIONS[operation]:
        raise ValueError('Incorrect observed identity count')
    if type(policy) is not int or policy not in (0, 1) or (operation != 112 and policy):
        raise ValueError('Unexpected encounter policy')
    if len(pose) != (12 if operation in (110,120,133) else 6 if operation == 119 else 3 if operation==123 else 0):
        raise ValueError('Unexpected spawn transform')
    packet = bytearray(SIZE)
    struct.pack_into('<4IQ', packet, 0, 3, operation, 0, 0, owner)
    if operation==133:struct.pack_into('<I',packet,32,authored_route)
    try:
        for i, identity in enumerate(identities):
            values = (identity.index, identity.serial, identity.address)
            if any(type(value) is not int for value in values):
                raise ValueError('Identity fields must be integers')
            struct.pack_into('<iiQ', packet, 88 + i * 16, *values)
        if pose:
            if any(type(value) not in (int, float) for value in pose):
                raise ValueError('Transform fields must be numbers')
            struct.pack_into('<'+str(len(pose))+'d', packet, 2000, *pose)
        if operation == 122:
            struct.pack_into('<I', packet, 32, total_count)
        if operation == 112:
            struct.pack_into('<I', packet, 32, policy)
    except (AttributeError, struct.error, OverflowError) as error:
        raise ValueError('Invalid owned-enemy request fields') from error
    result = bytes(packet)
    validate_request(result)
    return result
