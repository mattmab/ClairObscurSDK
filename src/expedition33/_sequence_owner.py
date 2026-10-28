"""Native owner prepared before a no-autoplay sequence factory call."""
import secrets
import struct
from dataclasses import replace
from . import _invocation_wire as call
from . import _sequence_binding_query as binding_query
from . import _sequence_origin as origin
from . import _sequence_seek as seek
from . import _authored_binding_diagnostic as authored_diagnostic

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
    if version!=1 or op not in (1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17) or not owner or reserved or error or state:
        raise ValueError('Sequence owner header')
    if op==16:
        from ._authored_binding_diagnostic import SIZE as diagnostic_size,validate_request as validate_diagnostic
        validate_diagnostic(data[32:32+diagnostic_size])
        if any(data[32+diagnostic_size:]):raise ValueError('Unexpected authored binding diagnostic tail')
    if op==17 and any(data[32:]):raise ValueError('Unexpected authored binding release payload')
    if op in (10,11,12,13):
        from ._sequence_flight import validate
        validate(op,data[32:]);return
    if op in (2,3,7) and any(data[HEADER.size:]): raise ValueError('Unexpected sequence owner payload')
    if op==4 and (any(data[HEADER.size:HEADER.size+call.SIZE]) or
                  not any(data[HEADER.size+call.SIZE:])):
        raise ValueError('Camera arm requires only a restoration setter')
    if op==5:
        binding_query.validate_request(data[32:96])
        if any(data[96:]): raise ValueError('Unexpected sequence binding query tail')
    if op==6:
        origin.validate_request(data[32:64])
        if any(data[64:]): raise ValueError('Unexpected sequence origin tail')
    if op==14:
        origin.validate_transform_request(data[32:72])
        if any(data[72:]):raise ValueError('Unexpected sequence origin transform tail')
    if op==8:
        seek.validate_request(data[32:96])
        if any(data[96:]):raise ValueError('Unexpected sequence seek tail')
    if op in (9,15):
        at=32+call.SIZE
        size=32 if op==9 else 40
        (origin.validate_request if op==9 else origin.validate_transform_request)(data[at:at+size])
        if any(data[at+size:]):raise ValueError('Unexpected origin update tail')
        version,size,extent,returned,_,_,fields,objects,outcome,native_error=call.HEADER.unpack_from(data,32)
        kind,offset,width,dimension,_,_,name,*_=call.FIELD.unpack_from(data,32+call.FIELDS_AT)
        if ((version,size,extent,returned,fields,objects,outcome,native_error)!=(1,1,1,0,1,0,0,0) or
                (kind,offset,width,dimension)!=(1,0,1,1) or name.rstrip(b'\0')!=b'ReturnValue'):
            raise ValueError('Origin update requires one native boolean status query')

class NativeSequenceOwner:
    def __init__(self,scope):
        self.scope=scope
        self.owner=secrets.randbits(64) or 1
        self.state='new'
        self.cleanup_diagnostics=None
        self.binding_diagnostics=None
        self.binding_error=None
        self.authored_binding_diagnostics=None
        self.authored_binding_error=None
        self._authored_query_active=False
        self.origin_error=None
        self.retirement_error=None
        self.seek_error=None
        self._retiring=False
        self._retirement_ack=False

    def _send(self,op,plans=(),query=None,translation=None,position=None,yaw=None):
        session=self.scope._session
        session._check()
        if self.state=='unknown': raise RuntimeError('Unknown sequence ownership outcome')
        if self.state=='cleanup_pending' and op not in (2,7,17):
            raise RuntimeError('Only sequence cleanup may run while composite cleanup is pending')
        if self._authored_query_active and op not in (2,3,7,17):
            raise RuntimeError('Release the retained authored binding query before further sequence operations')
        request=HEADER.pack(1,op,self.owner,0,0,0)
        if op==8:
            if plans or query is not None or translation is not None:raise ValueError('Seek requires position only')
            seek.validate_request(position)
            request+=position+bytes(SIZE-96)
        elif op in (9,15):
            if len(plans)!=1 or query is not None or position is not None:raise ValueError('Origin update requires status query and translation')
            encoded=origin.encode(translation) if op==9 else origin.encode_transform(translation,yaw)
            request+=call.encode_plan(replace(plans[0],wire_version=1))+encoded+bytes(call.SIZE-len(encoded))
        elif op in (6,14):
            if plans or query is not None: raise ValueError('Sequence origin requires translation only')
            encoded=origin.encode(translation) if op==6 else origin.encode_transform(translation,yaw)
            request+=encoded+bytes(SIZE-32-len(encoded))
        elif op==5:
            if plans or query is None: raise ValueError('Sequence binding query payload required')
            binding_query.validate_request(query)
            request+=query+bytes(SIZE-96)
        elif op==16:
            if plans or query is None:raise ValueError('Authored binding diagnostic payload required')
            authored_diagnostic.validate_request(query)
            request+=query+bytes(SIZE-32-authored_diagnostic.SIZE)
        elif op==17:
            if plans or query is not None:raise ValueError('Authored binding release takes no payload')
            request+=bytes(2*call.SIZE)
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
            if op in (9,15):
                error,state=HEADER.unpack_from(data)[4:]
                at=32+call.SIZE
                if data[at:]!=request[at:]:raise ValueError('Origin update acknowledgement mismatch')
                unchanged=data[32:at]==request[32:at]
                status=None if unchanged else call.decode_reply(request[32:at],data[32:at].hex())
                if error==1591 and state==1 and (unchanged or status.outcome in ('not_dispatched','dispatch_returned')):
                    self.origin_error=error;self.state='armed';return False
                if (error or state!=1 or status is None or status.outcome!='dispatch_returned' or
                        status.data!=b'\0' or status.objects):
                    raise RuntimeError(f'Native sequence origin update rejected ({error}, {state})')
            elif op==8:
                if any(data[96:]):raise ValueError('Unexpected sequence seek reply tail')
                seek_outcome=seek.decode(position,data[32:96])
                if seek_outcome==2:raise RuntimeError('Unknown native sequence seek outcome')
            elif op==5:
                if any(data[96:]): raise ValueError('Unexpected sequence binding query tail')
                self.binding_diagnostics=binding_query.decode(request[32:96],data[32:96])
                if self.binding_diagnostics['outcome']==2:
                    raise RuntimeError('Unknown native sequence binding query outcome')
            elif op==16:
                end=32+authored_diagnostic.SIZE
                if any(data[end:]):raise ValueError('Unexpected authored binding diagnostic tail')
                self.authored_binding_diagnostics=authored_diagnostic.decode(query,data[32:end])
                if self.authored_binding_diagnostics['outcome']==2:
                    raise RuntimeError('Unknown native authored binding query outcome')
            elif diagnostic_reply:
                if any(data[96:]):
                    raise ValueError('Unexpected sequence cleanup diagnostic tail')
                # Preserve a validated snapshot before a native error causes
                # normal ownership abort. Never retain malformed observations.
                self.cleanup_diagnostics=decode_cleanup_diagnostics(data[32:96])
            elif data[32:]!=request[32:]:
                raise ValueError('Sequence ownership acknowledgement mismatch')
            error,state=HEADER.unpack_from(data)[4:]
            if op==16:
                outcome=self.authored_binding_diagnostics['outcome']
                if state==1 and outcome==0 and (error in (1581,407) or 1601<=error<=1604 or 1611<=error<=1617 or 1701<=error<=1723):
                    # A rejected diagnostic may still own an empty native
                    # operation. Require explicit release before another query.
                    self._authored_query_active=True;self.authored_binding_error=error;self.state='armed';return False
                if error or state!=1 or outcome!=1:
                    raise RuntimeError(f'Native authored binding query rejected ({error}, {state}, {outcome})')
                self._authored_query_active=True;self.authored_binding_error=None;self.state='armed';return True
            if op==17:
                if state==1 and error in (407,1581):
                    self.authored_binding_error=error;self.state='cleanup_pending';return False
                if error or state!=1:raise RuntimeError(f'Native authored binding release rejected ({error}, {state})')
                self._authored_query_active=False;self.authored_binding_error=None;self.state='armed';return True
            if op==8:
                if state==1 and seek_outcome==0 and error in (1691,1595,407):
                    self.seek_error=error;self.state='armed';return False
                if error or state!=1 or seek_outcome!=1:
                    raise RuntimeError(f'Native sequence seek rejected ({error}, {state}, {seek_outcome})')
            if op==7:
                if error in (407,1595) and state in (0,1,3):
                    self.retirement_error=error
                    self.state='cleanup_pending'
                    return False
                if error or state!=0:
                    raise RuntimeError(f'Native retired sequence rejected ({error}, {state})')
                self._retirement_ack=True
            if op in (6,14):
                if state!=1:
                    raise ValueError('Sequence origin acknowledgement requires an armed owner')
                if error==1591:
                    self.origin_error=error
                    self.state='cleanup_pending'
                    return False
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
            if op in (2,7) and state==0:self._authored_query_active=False
            return True
        except BaseException as error:
            if op==7:
                # Retain this owner without collapsing unrelated SDK services.
                # No automatic retry after a lost retirement acknowledgement.
                self.state='unknown'
                raise
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

    def seek_frame(self,function,frame,subframe=0.):
        if self.state!='armed':raise RuntimeError('Seek requires an armed native sequence owner')
        capability=getattr(self.scope._session._transport,'sequence_seek_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Verified owned sequence seek capability required')
        if not self._send(8,position=seek.encode(function,frame,subframe)):
            raise RuntimeError(f'Native sequence seek rejected before dispatch ({self.seek_error})')
        self.seek_error=None
        return True

    def configure_origin(self, translation):
        """Configure private native-owned instance data before any evaluation.

        This grants no binding, asset-safety, or Play permission. The runtime
        independently rejects evaluated owners and verifies private ownership.
        """
        if self.state!='armed':
            raise RuntimeError('Origin requires a created native-owned sequence')
        if getattr(self.scope._session._transport,'sequence_origin_protocol',0)!=1:
            raise RuntimeError('Verified native sequence origin capability required')
        origin.encode(translation)
        if not self._send(6,translation=translation):
            raise RuntimeError(f'Native sequence origin rejected ({self.origin_error}); close required')
        return True

    def update_origin(self,translation,status):
        if self.state!='armed':raise RuntimeError('Origin update requires an armed sequence')
        capability=getattr(self.scope._session._transport,'sequence_origin_update_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Native live sequence placement capability required')
        if status.function.name!='IsPlaying':raise ValueError('Sequence status query required')
        if not self._send(9,(status,),translation=translation):
            raise RuntimeError('Sequence must be idle in its original owned world before moving')
        self.origin_error=None;return True

    def configure_origin_transform(self,translation,yaw):
        if self.state!='armed':raise RuntimeError('Origin requires a created native-owned sequence')
        if getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)!=1:
            raise RuntimeError('Verified native sequence origin transform capability required')
        origin.encode_transform(translation,yaw)
        if not self._send(14,translation=translation,yaw=yaw):
            raise RuntimeError(f'Native sequence origin transform rejected ({self.origin_error}); close required')
        return True

    def update_origin_transform(self,translation,yaw,status):
        if self.state!='armed':raise RuntimeError('Origin update requires an armed sequence')
        if getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)!=1:
            raise RuntimeError('Native sequence origin transform capability required')
        origin.encode_transform(translation,yaw)
        if status.function.name!='IsPlaying':raise ValueError('Sequence status query required')
        if not self._send(15,(status,),translation=translation,yaw=yaw):
            raise RuntimeError('Sequence must be idle in its original owned world before moving')
        self.origin_error=None;return True

    def query_authored_bindings(self, profile, function):
        """Inspect a finite authored profile; never starts sequence playback."""
        if self.state!='armed':
            raise RuntimeError('Binding query requires a created native-owned sequence')
        if getattr(self.scope._session._transport,'sequence_binding_query_protocol',0)!=1:
            raise RuntimeError('Verified native sequence binding query capability required')
        if not self._send(5,query=binding_query.encode(profile,function)):
            raise RuntimeError(f'Native binding query rejected before completion ({self.binding_error}); close required')
        return dict(self.binding_diagnostics)

    def query_authored_component(self, query):
        """Retain one engine-bound object result until explicit release.

        Results identify bindings, not animation or skeleton compatibility.
        Keep all request leases alive and release this diagnostic before other
        player operations or closing the containing scope.
        """
        if self.state!='armed':raise RuntimeError('Binding diagnostic requires an armed sequence owner')
        capability=getattr(self.scope._session._transport,'sequence_authored_binding_diagnostic_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Native authored binding diagnostic unavailable')
        if not self._send(16,query=query):return None
        return dict(self.authored_binding_diagnostics)

    def release_authored_component(self):
        if not self._authored_query_active:return True
        if self.state not in ('armed','cleanup_pending'):return False
        return self._send(17)

    def close(self):
        if self.state in ('new','closed'): return True
        if self._retiring:return self.retire_world()
        return self._send(2)

    def retire_world(self):
        """Release owned holds only after native positive World replacement.

        This never issues Stop, DestroyActor or old-world camera restoration.
        False is a known no-dispatch/deferred result; uncertainty retains owner.
        """
        if self.state in ('new','closed'):return True
        capability=getattr(self.scope._session._transport,'sequence_retirement_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Verified native sequence retirement capability required')
        self._retiring=True
        return self._send(7)
