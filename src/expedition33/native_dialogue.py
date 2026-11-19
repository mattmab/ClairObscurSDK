"""Owned copied-text calls into the original dialogue system (runtime 267+)."""
import secrets
from . import RuntimeQueryError
from . import _native_dialogue_wire as wire


class NativeDialogueError(RuntimeQueryError):
    def __init__(self,code):
        self.code=code
        super().__init__('Original dialogue dispatch rejected ('+str(code)+')')


def decode(sent,reply):
    import struct
    if type(reply) is not bytes or len(reply)!=wire.SIZE or reply[:8]!=sent[:8] or reply[16:]!=sent[16:]:
        raise RuntimeQueryError('Native dialogue acknowledgement differs from request')
    error,state=struct.unpack_from('<II',reply,8)
    if error:
        if state:raise RuntimeQueryError('Rejected dialogue has an invalid state')
        raise NativeDialogueError(error)
    if state!=1:raise RuntimeQueryError('Native dialogue dispatch was not acknowledged')


class NativeDialogueText:
    def __init__(self,parent,system,dialogue):
        parent._check()
        capability=getattr(parent._session._transport,'native_dialogue_text_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeQueryError('Original dialogue text runtime required')
        from ._scope import SessionScope
        from ._stable_lease import acquire_stable
        from .catalog import capture_matching
        self.scope=SessionScope(parent);self.unknown=False;self.closed=False;self._nonce=0
        self.participants=();self.participant_nonce=0;self.participant_update=None;self.participants_active=False
        self.camera_packet=None
        try:
            self.system_held,_=acquire_stable(self.scope,system);self.system=self.system_held.object
            self.held,_=acquire_stable(self.scope,dialogue);self.dialogue=self.held.object
            catalog=self._metadata(('StartDialogLines','StartChoice','EndDialogue'))
            prefix='/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:'
            self.functions=[]
            for name in ('StartDialogLines','StartChoice','EndDialogue'):
                held=self._hold_function(catalog.find_path(prefix+name));self.functions.append(held.object)
            self.speakers={}
        except BaseException:
            self.scope.close();raise

    def _metadata(self,names):
        from .catalog import capture_matching
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        if prepared is not None and all(any(o.name==name for o in prepared.metadata) for name in names):
            return prepared.catalog(self.scope,names)
        return capture_matching(self.scope.pid,names=names)

    def _hold_function(self,function):
        """Reuse an exact immutable function already owned by process warmup.

        Dialogue/system/actor/speaker references stay owned by this live call.
        Only the explicit construction metadata list can use the shared lease.
        """
        from ._stable_lease import acquire_stable
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        if (prepared is not None and function.class_name=='Function' and
                any((value.index,value.serial,value.address)==(function.index,function.serial,function.address)
                    for value in prepared.metadata)):
            if prepared.session is not self.scope._session:raise RuntimeQueryError('Dialogue function resources belong to another session')
            prepared.scope._check()
            held=prepared.resources.hold(function)
            if not held.active:raise RuntimeQueryError('Dialogue function resource lease expired')
            self._function_resources=prepared
            return held
        return acquire_stable(self.scope,function)[0]

    def _check_functions(self):
        prepared=getattr(self,'_function_resources',None)
        if prepared is not None:
            if prepared.session is not self.scope._session:raise RuntimeQueryError('Dialogue function session changed')
            prepared.scope._check()

    def _send(self,texts,speaker=None,*,finish=False):
        if self.closed or self.unknown:raise RuntimeQueryError('Native dialogue text owner is not available')
        self.scope._check()
        self._check_functions()
        if finish:
            capability=getattr(self.scope._session._transport,'native_dialogue_end_protocol',0)
            if type(capability) is not int or capability!=1:raise RuntimeQueryError('Original dialogue end runtime required')
        if speaker is not None:
            from ._stable_lease import acquire_stable
            key=(speaker.index,speaker.serial,speaker.address)
            if key not in self.speakers:
                held,_=acquire_stable(self.scope,speaker);self.speakers[key]=held
            speaker=self.speakers[key].object
        nonce=secrets.randbits(64) or 1
        while nonce==self._nonce:nonce=secrets.randbits(64) or 1
        self._nonce=nonce
        packet=wire.encode(nonce,self.held._token,self.system,self.dialogue,self.functions[2 if finish else int(speaker is None)],texts,speaker=speaker,finish=finish)
        try:
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            decode(packet,bytes.fromhex(response['mesh_packet']))
        except NativeDialogueError as error:
            if error.code==3862:self.unknown=True
            raise
        except BaseException:
            self.unknown=True;raise
        return nonce

    def register_participants(self,npcs):
        if self.participants_active or self.participants:raise RuntimeError('Dialogue participants already prepared')
        if getattr(self.scope._session._transport,'story_dialogue_participants_protocol',0)!=1:
            raise RuntimeQueryError('Multiple story speakers require the native participant runtime')
        from ._stable_lease import acquire_stable
        from .catalog import capture_matching
        c=self._metadata(('UpdateAllSpeakerActors',))
        update=c.find_path('/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:UpdateAllSpeakerActors')
        held=self._hold_function(update);self.participant_update=held.object
        rows=[]
        for npc in npcs:
            held,_=acquire_stable(self.scope,npc.npc)
            rows.append((npc.actor.owner._owner,held._token,held.object))
        self.participants=tuple(rows);self.participant_nonce=secrets.randbits(64) or 1
        self._send_participants(remove=False);self.participants_active=True

    def _send_participants(self,*,remove):
        self._check_functions()
        from . import _story_participants_wire as participant_wire
        import struct
        packet=participant_wire.encode(self.participant_nonce,self.held._token,self.system,self.dialogue,
            self.participant_update,self.participants,remove=remove)
        try:
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            reply=bytes.fromhex(response['mesh_packet'])
            if len(reply)!=len(packet) or reply[:8]!=packet[:8] or reply[16:]!=packet[16:]:
                self.unknown=True;raise RuntimeQueryError('Dialogue participant acknowledgement changed')
            error,state=struct.unpack_from('<II',reply,8)
            if error or state!=1:
                if error!=3900 or remove:self.unknown=True
                raise RuntimeQueryError('Native dialogue participant operation failed ('+str(error)+')')
        except BaseException:
            # A clean preflight rejection remains distinguishable; all other
            # failures retain this call's leases for explicit recovery.
            if 'reply' not in locals():self.unknown=True
            raise

    def lines(self,speaker,texts):return self._send(texts,speaker)
    def frame_speaker(self,npc,camera_npc):
        capability=getattr(self.scope._session._transport,'story_dialogue_camera_protocol',0)
        if type(capability) is not int or capability not in (1,2,3,4):return False
        if self.closed or self.unknown:raise RuntimeQueryError('Native dialogue owner is unavailable')
        self._check_functions()
        from . import _story_camera_wire as camera_wire
        from ._stable_lease import acquire_stable
        from .catalog import capture_matching
        import struct
        if not hasattr(self,'camera_functions'):
            camera_handler='ActivateCameraComponentByType' if capability>=3 else 'HandleCameraType'
            c=self._metadata(('SetDialogueParameters',camera_handler))
            paths=('/Game/Gameplay/DialogueSystem/BP_Dialogue.BP_Dialogue_C:SetDialogueParameters',
                '/Game/Gameplay/DialogueSystem/BP_DialogueSystemComponent.BP_DialogueSystemComponent_C:'+camera_handler)
            self.camera_functions=tuple(self._hold_function(c.find_path(path)) for path in paths)
            self.camera_actors={}
            self.camera_pose_functions=()
            self.camera_view_functions=()
            if capability>=2:
                c=self._metadata(('K2_SetRelativeTransform','GetRelativeTransform'))
                self.camera_pose_functions=tuple(self._hold_function(c.find_path(
                    '/Script/Engine.SceneComponent:'+name)) for name in ('K2_SetRelativeTransform','GetRelativeTransform'))
            if capability>=3:
                c=self._metadata(('GetViewTarget','SetViewTargetWithBlend'))
                self.camera_view_functions=tuple(self._hold_function(c.find_path(path)) for path in (
                    '/Script/Engine.Controller:GetViewTarget','/Script/Engine.PlayerController:SetViewTargetWithBlend'))
        for actor in (npc,camera_npc):
            key=tuple(actor.identity)
            if key not in self.camera_actors:self.camera_actors[key]=acquire_stable(self.scope,actor.npc)[0]
        packet=camera_wire.encode(secrets.randbits(64) or 1,npc.actor.owner._owner,camera_npc.actor.owner._owner,
            self.held._token,self.system,self.dialogue,self.camera_actors[tuple(npc.identity)].object,
            self.camera_actors[tuple(camera_npc.identity)].object,*(held.object for held in self.camera_functions),
            pose_functions=tuple(held.object for held in self.camera_pose_functions),
            view_functions=tuple(held.object for held in self.camera_view_functions))
        try:
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            reply=bytes.fromhex(response['mesh_packet'])
            if len(reply)!=len(packet) or reply[:8]!=packet[:8] or reply[16:]!=packet[16:]:
                self.unknown=True;raise RuntimeQueryError('Dialogue camera acknowledgement changed')
            error,state=struct.unpack_from('<II',reply,8)
            if error or state!=1:
                if error!=3910:self.unknown=True
                failure=RuntimeQueryError('Native dialogue camera operation failed ('+str(error)+')')
                failure.native_error=error
                failure.native_reason=state if state>=100 else None
                failure.outcome='not_dispatched' if error==3910 else 'unknown'
                raise failure
        except BaseException:
            if 'reply' not in locals():self.unknown=True
            raise
        self.camera_packet=packet
        return True

    def retire_camera_world(self):
        """Acknowledge old-world camera collector release before scope release.

        This never restores a camera or invokes methods on the old controller.
        A pending/same-world proof keeps the entire dialogue scope reachable.
        """
        if self.unknown:return False
        previous=getattr(self,'camera_packet',None)
        if previous is None:return True
        capability=getattr(self.scope._session._transport,'story_dialogue_camera_protocol',0)
        if type(capability) is not int or capability<4:return False
        from . import _story_camera_wire as camera_wire
        import struct
        packet=camera_wire.retire(previous,secrets.randbits(64) or 1)
        try:
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            reply=bytes.fromhex(response['mesh_packet'])
            if len(reply)!=len(packet) or reply[:8]!=packet[:8] or reply[16:]!=packet[16:]:
                self.unknown=True;raise RuntimeQueryError('Dialogue camera retirement acknowledgement changed')
            error,state=struct.unpack_from('<II',reply,8)
            if error==3910 and state==0:return False
            if error or state!=1:
                self.unknown=True;raise RuntimeQueryError('Dialogue camera retirement failed ('+str(error)+')')
        except BaseException:
            self.unknown=True;raise
        self.camera_packet=None
        return True

    def choices(self,texts):return self._send(texts)
    def end(self):
        result=self._send((),finish=True)
        self.camera_packet=None
        if self.participants_active:
            self._send_participants(remove=True);self.participants_active=False
        return result

    def close(self):
        if self.closed:return True
        if self.unknown:return False
        if getattr(self,'camera_packet',None) is not None:return False
        if self.participants_active:
            try:self._send_participants(remove=True)
            except Exception:return False
            self.participants_active=False
        self.scope.close();self.closed=True;return True
