"""Native owner prepared before a no-autoplay sequence factory call."""
import secrets
import struct
from dataclasses import replace
from . import _invocation_wire as call
from . import _sequence_binding_query as binding_query

HEADER=struct.Struct('<IIQQII')
SIZE=HEADER.size+2*call.SIZE
AUDIO_DIAGNOSTIC = struct.Struct('<16I')


def decode_cleanup_diagnostics(data):
    """Decode only the negotiated fixed response slice, never native memory."""
    if type(data) is not bytes or len(data) != 64:
        raise ValueError('Audio cleanup diagnostic size')
    magic, version, size, reserved, *fields = AUDIO_DIAGNOSTIC.unpack(data)
    if (magic, version, size, reserved) != (0x44413345, 1, 64, 0):
        raise ValueError('Audio cleanup diagnostic header')
    keys = ('phase', 'reason', 'native_error', 'outcome', 'owner_state', 'index', 'step',
            'owned_count', 'original_count', 'original_now_count', 'pause_error', 'pause_native_error')
    result = dict(zip(keys, fields))
    if (result['phase'] > 16 or result['outcome'] > 2 or result['owner_state'] > 3 or
            result['index'] > 64 or result['step'] > 1 or
            any(result[key] > 64 for key in ('owned_count', 'original_count', 'original_now_count'))):
        raise ValueError('Audio cleanup diagnostic bounds')
    return result

class SequenceCleanupDeferred(RuntimeError):
    """Native cleanup explicitly deferred before a safe retry boundary."""
    pass

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE: raise ValueError('Sequence owner size')
    version,op,owner,reserved,error,state=HEADER.unpack_from(data)
    if version!=1 or op not in (1,2,3,4,5) or not owner or reserved or error or state:
        raise ValueError('Sequence owner header')
    if op in (2,3) and any(data[HEADER.size:]): raise ValueError('Unexpected sequence owner payload')
    if op==4 and (any(data[HEADER.size:HEADER.size+call.SIZE]) or
                  not any(data[HEADER.size+call.SIZE:])):
        raise ValueError('Camera arm requires only a restoration setter')
    if op==5:
        binding_query.validate_request(data[32:96])
        if any(data[96:]): raise ValueError('Unexpected sequence binding query tail')

class NativeSequenceOwner:
    def __init__(self,scope):
        self.scope=scope
        self.owner=secrets.randbits(64) or 1
        self.state='new'
        self.cleanup_diagnostics=None
        self.binding_diagnostics=None
        self.binding_error=None

    def _send(self,op,plans=(),query=None):
        session=self.scope._session
        session._check()
        if self.state=='unknown': raise RuntimeError('Unknown sequence ownership outcome')
        if self.state=='cleanup_pending' and op!=2:
            raise RuntimeError('Only sequence cleanup may run while composite cleanup is pending')
        request=HEADER.pack(1,op,self.owner,0,0,0)
        if op==5:
            if plans or query is None: raise ValueError('Sequence binding query payload required')
            binding_query.validate_request(query)
            request+=query+bytes(SIZE-96)
        elif op==4:
            if len(plans)!=1: raise ValueError('Camera arm requires one restoration setter')
            request+=bytes(call.SIZE)+call.encode_plan(replace(plans[0],wire_version=1))
        else:
            request+=b''.join(call.encode_plan(replace(p,wire_version=1)) for p in plans) if plans else bytes(2*call.SIZE)
        validate_request(request)
        self.state='unknown'
        try:
            response=session._transport.command('sequence-owner',request)
            data=bytes.fromhex(response['sequence_owner_packet'])
            if len(data)!=SIZE or data[:24]!=request[:24]:
                raise ValueError('Sequence ownership acknowledgement mismatch')
            diagnostic_reply = op==2 and getattr(session._transport, 'audio_cleanup_diagnostics_protocol', 0)==1
            if op==5:
                if any(data[96:]): raise ValueError('Unexpected sequence binding query tail')
                self.binding_diagnostics=binding_query.decode(request[32:96],data[32:96])
                if self.binding_diagnostics['outcome']==2:
                    raise RuntimeError('Unknown native sequence binding query outcome')
            elif diagnostic_reply:
                if any(data[96:]):
                    raise ValueError('Unexpected sequence cleanup diagnostic tail')
                # Preserve a validated snapshot before a native error causes
                # normal ownership abort. Never retain malformed observations.
                self.cleanup_diagnostics=decode_cleanup_diagnostics(data[32:96])
            elif data[32:]!=request[32:]:
                raise ValueError('Sequence ownership acknowledgement mismatch')
            error,state=HEADER.unpack_from(data)[4:]
            if op==5 and state==1 and error in (1581,407):
                # Native reports a known rejection/defer with a closeable owner.
                # The validated diagnostic above already excludes uncertainty.
                # Never redispatch; let the caller close the retained context.
                self.binding_error=error
                self.state='cleanup_pending'
                return False
            camera_prepared = (state==3 and
                getattr(session._transport, 'sequence_camera_protocol', 0)==1)
            if op==2 and error==407 and (state in (0,1) or camera_prepared):
                # state0 means the sequence is already stopped/destroyed but
                # downstream widget/audio/reference cleanup is still draining.
                # state3 also permits opt-in pre-factory camera holds to drain.
                # Keep the owner until another explicit close acknowledges all.
                self.state='cleanup_pending'
                return False
            if error or state not in (0,1,3): raise RuntimeError(f'Native sequence rejected ({error}, {state})')
            if op==5 and (state!=1 or self.binding_diagnostics['outcome']!=1):
                raise ValueError('Sequence binding query did not confirm a returned owned query')
            if op==5 and self.binding_diagnostics['completed_queries']!=binding_query.PROFILE_LIMITS[binding_query.PACKET.unpack(query)[2]]:
                raise ValueError('Sequence binding query returned an incomplete successful batch')
            if op==5 and self.binding_diagnostics['private_active']!=4+self.binding_diagnostics['matched_bindings']:
                raise ValueError('Sequence binding query retained holder accounting mismatch')
            self.state={0:'closed',1:'armed',3:'prepared'}[state]
            return True
        except BaseException as error:
            try:
                session._abort_ownership()
            except BaseException as abort_error:
                error.add_note(f'Secondary ownership-abort failure: {abort_error!r}')
            raise

    def prepare(self,stop,destroy):
        if self.state!='new': raise RuntimeError('Sequence owner already used')
        if any(p.parameter_size or p.parameters or p.objects for p in (stop,destroy)):
            raise ValueError('Sequence cleanup requires empty parameter frames')
        return self._send(1,(stop,destroy))

    def arm_camera(self, restore):
        """Opt-in native capture before factory dispatch; grants no Play permission.

        The native owner validates/captures the original target and privately
        retains its identities. The caller must supply an exact zero-blend setter
        with a null placeholder, never a guessed target or a copied POV blob.
        """
        if self.state!='prepared':
            raise RuntimeError('Camera capture requires a prepared sequence owner')
        if getattr(self.scope._session._transport,'sequence_camera_protocol',0)!=1:
            raise RuntimeError('Verified native camera ownership capability required')
        shape = tuple((p.name,p.kind,p.offset,p.width,p.dimension) for p in restore.parameters)
        expected = (('NewViewTarget','ObjectProperty',0,8,1),
            ('BlendTime','FloatProperty',8,4,1),('blendFunc','ByteProperty',12,1,1),
            ('BlendExp','FloatProperty',16,4,1),('bLockOutgoing','BoolProperty',20,1,1))
        if (restore.function.name!='SetViewTargetWithBlend' or shape!=expected or
                restore.parameter_size!=21 or restore.allocation_extent!=24 or
                restore.return_offset!=65535 or restore.objects or restore.texts or
                len(restore.data) not in (21,24) or any(restore.data)):
            raise ValueError('Expected exact null-target zero-blend camera restoration plan')
        return self._send(4,(restore,))

    def status(self):
        if self.state=='cleanup_pending':
            return self.state
        self._send(3)
        return self.state

    def query_authored_bindings(self, profile, function):
        """Inspect a finite authored profile; never starts sequence playback."""
        if self.state!='armed':
            raise RuntimeError('Binding query requires a created native-owned sequence')
        if getattr(self.scope._session._transport,'sequence_binding_query_protocol',0)!=1:
            raise RuntimeError('Verified native sequence binding query capability required')
        if not self._send(5,query=binding_query.encode(profile,function)):
            raise RuntimeError(f'Native binding query rejected before completion ({self.binding_error}); close required')
        return dict(self.binding_diagnostics)

    def close(self):
        if self.state in ('new','closed'): return True
        return self._send(2)
