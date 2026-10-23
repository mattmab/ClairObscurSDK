"""Owned playback client for the validated milestone-one scene plan."""
import secrets
import struct
import time
from expedition33._scope import SessionScope
from expedition33.assets import load_asset
from expedition33.catalog import capture_matching,capture_selected
from expedition33.values import read_object_reference
from expedition33.cinematics.original_game_action import controller_context
from expedition33.management import Action, ModDefinition
from expedition33._runtime_scene_wire import validate_request
from .scene import encode,validate,PLAN
from .palette import CHARACTERS,ANIMATIONS,BODY_SKELETON
from .registry import Registry

MESH = '/Game/Characters/Heros/Lune/SK_Lune_Placeholder.SK_Lune_Placeholder'
ANIMATION = '/Game/Characters/Heros/Lune/Animations/Skills/Lune_Thunder_Kick_IP.Lune_Thunder_Kick_IP'
EXTRA_ASSETS = (
    '/Game/MetaHumans/Lune/Face/Lune_FaceMesh.Lune_FaceMesh',
    '/Game/Characters/Hair/Heroes/Lune/Hair_Lune_2_skl.Hair_Lune_2_skl',
    '/Game/Characters/Heros/Maelle/Customization/Skin/SK_Maelle_ActeIII.SK_Maelle_ActeIII',
    '/Game/Characters/Heros/Maelle/Animations/Skills/Maelle_Skill_DancingFury_B_Inplace.Maelle_Skill_DancingFury_B_Inplace',
    '/Game/MetaHumans/Maelle_v2/Face/Maelle_v2_FaceMesh.Maelle_v2_FaceMesh',
    '/Game/Characters/Hair/Heroes/Maelle/Maelle_Hair_V3_Metahumanskl.Maelle_Hair_V3_Metahumanskl',
    '/Game/Characters/Enemies/Petank/SK_Petank.SK_Petank',
    '/Game/Characters/Heros/Maelle/Sword/SK_Sword_Maelle.SK_Sword_Maelle',
    '/Game/Animations/AnimPacks/Idles/MC_Idles_Pack/Shift/Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5.Pack_MCIdlesPack_am_Stand_Idle_ShiftL_Loop_01_UE5',
)
SOUND = '/Game/Audio/WAV/00_Placeholders/UI/Menu/Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu.Smart_UI_Interface_Click_An_Ants_Whip_1_Whoosh_Crack_Short_Menu'
EFFECTS=tuple(p+'.'+p.rsplit('/',1)[1] for p in (
    '/Game/FX/FX_Leo/Fx/Lune/Thunder_Fall/Systems/NS_Impact_Electric1',
    '/Game/FX/FX_Leo/Fx/Maelle/FX_FlowerPetalsBurst',
    '/Game/FX/FX_Leo/Fx/Maelle/FX_MaelleSword',
    '/Game/FX/FX_Leo/Fx/Lune/FX_LuneTrail'))
REUSED = (('GameplayStatics','BeginDeferredActorSpawnFromClass'),('GameplayStatics','FinishSpawningActor'),
    ('Actor','K2_DestroyActor'),('Actor','K2_GetActorLocation'),('Actor','K2_GetActorRotation'),
    ('PlayerController','SetViewTargetWithBlend'),('Controller','GetViewTarget'),
    ('Controller','SetIgnoreMoveInput'),('PlayerCameraManager','GetCameraLocation'),
    ('PlayerCameraManager','GetCameraRotation'),('SceneComponent','SetMobility'),
    ('Controller','K2_GetPawn'),('GameplayStatics','IsGamePaused'),
    ('Actor','SetActorEnableCollision'),('Actor','K2_TeleportTo'))
ADDITIONAL = (('Actor','GetComponentByClass'),('SkeletalMeshComponent','SetSkeletalMeshAsset'),
    ('SkeletalMeshComponent','PlayAnimation'),('SkeletalMeshComponent','Stop'),
    ('GameplayStatics','CreateSound2D'),('AudioComponent','Play'),('AudioComponent','Stop'),
    ('ActorComponent','K2_DestroyComponent'),('Controller','SetIgnoreLookInput'),('CameraComponent','SetFieldOfView'),
    ('SkinnedMeshComponent','SetLeaderPoseComponent'),('SceneComponent','K2_AttachToComponent'),
    ('SkinnedMeshComponent','GetNumBones'),('SkinnedMeshComponent','GetBoneName'),
    ('SceneComponent','K2_SetRelativeTransform'))
SIZE=20984
HEADER=struct.Struct('<4IQ')
IDENTITY=struct.Struct('<iiQ')
STATES={0:'idle',1:'prepared',2:'playing',3:'cleanup_pending',4:'finished',5:'interrupted',6:'failed',7:'authoring',8:'timeline_playing'}


def one(rows):
    rows=tuple(rows)
    if len(rows)!=1:raise RuntimeError('Expected one current cinematic dependency')
    return rows[0]


class Runtime:
    def __init__(self):
        self.session=self.scope=None
        self.owner=secrets.randbits(64) or 1
        self.last=dict(state='idle',live_success=False)
        self.next_poll=0.
        self.uncertain=False
        self.photo_mode=False;self.photo_rotation=None;self.photo_ticks=()
        self.registry=Registry(self);self.author_plan=None
        self.audio_slots={};self.audio_event_slots={};self.animation_slots={};self.audio_load_scope=None;self.preview_scope=None;self.music_components=0

    @property
    def authoring(self):return self.scope is not None and self.last['state'] in ('authoring','timeline_playing')

    def _command(self,op,ids=(),payload=b''):
        transport=self.session._session._transport
        if getattr(transport,'runtime_scene_protocol',0)!=7:
            raise RuntimeError('Use the isolated Scene Editor candidate; installed backend is unchanged')
        if self.uncertain:raise RuntimeError('Unknown native outcome; native backend teardown owns cleanup')
        packet=bytearray(SIZE);HEADER.pack_into(packet,0,7,op,0,0,self.owner)
        if op==70 and len(ids)!=134:raise ValueError('Exact scene input count required')
        if op!=70 and ids:raise ValueError('Only prepare accepts identities')
        for i,obj in enumerate(ids):IDENTITY.pack_into(packet,88+16*i,obj.index,obj.serial,obj.address)
        if payload:packet[88:88+len(payload)]=payload
        validate_request(bytes(packet),protocol=7)
        self.uncertain=True
        raw=bytes.fromhex(transport.command('mesh',bytes(packet))['mesh_packet'])
        author_reply=len(raw)==SIZE and struct.unpack_from('<I',raw,12)[0] in (7,8)
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:24]!=packet[16:24] or (raw[88+PLAN.size:20976]!=packet[88+PLAN.size:20976] if author_reply else raw[88:20976]!=packet[88:20976]):
            raise RuntimeError('Cinematic acknowledgement mismatch; no retry')
        _,_,error,state,_=HEADER.unpack_from(raw)
        if state not in STATES:raise RuntimeError('Unknown cinematic state; no retry')
        if author_reply:
            proof=bytearray(SIZE);HEADER.pack_into(proof,0,7,74,0,0,self.owner);proof[88:88+PLAN.size]=raw[88:88+PLAN.size];validate_request(bytes(proof),protocol=7)
            self.author_plan=PLAN.unpack_from(raw,88)[2:]
        self.uncertain=False
        active,poses=struct.unpack_from('<II',raw,20976)
        mask=struct.unpack_from('<I',raw,84)[0]
        elapsed,animation_at,audio_at=struct.unpack_from('<3d',raw,56)
        self.last=dict(state=STATES[state],error=error,step=struct.unpack_from('<I',raw,80)[0],
            elapsed=elapsed,animation_at=animation_at,audio_at=audio_at,camera_updates=poses,
            private_leases=active,animation_dispatched=bool(mask&1),audio_dispatched=bool(mask&2),audio_cues_dispatched=(mask>>8)&255,effects_spawned=(mask>>16)&255,
            live_success=False,requires_visual_audio_confirmation=True,game_music_muted=bool(mask&(1<<29)),camera_selected=bool(mask&(1<<30)),cursor_held=bool(mask&(1<<31)))
        if author_reply:self.last.update(selected=int(audio_at),selected_camera=((mask>>24)&31)-1,selected_clip=int(animation_at),playhead=elapsed,anchor=list(self.author_plan[142:146]),editor_camera=list(self.author_plan[146:152]))
        if error and error!=407:raise RuntimeError('Native cinematic rejected/failed: '+str(self.last))
        return self.last

    def camera_view(self,view=None):
        import math
        if not self.authoring or self.uncertain:raise ValueError('Camera transfer requires an owned authoring scene')
        if view is not None and (len(view)!=7 or not self.photo_mode):raise ValueError('Camera restore requires the photo rig and seven values')
        packet=bytearray(SIZE);HEADER.pack_into(packet,0,7,92,0,0,self.owner)
        struct.pack_into('<8d',packet,88,int(view is not None),*(view if view is not None else [0.]*7))
        validate_request(bytes(packet),protocol=7);self.uncertain=True
        raw=bytes.fromhex(self.session._session._transport.command('mesh',bytes(packet))['mesh_packet'])
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:88]!=packet[16:88] or raw[152:]!=packet[152:]:raise RuntimeError('Camera transfer acknowledgement mismatch; no retry')
        _,_,error,state,_=HEADER.unpack_from(raw)
        action,*actual=struct.unpack_from('<8d',raw,88)
        if error:
            self.uncertain=False
            raise RuntimeError('Scene camera adapter rejected request: '+str(error))
        if state not in (7,8) or action!=int(view is not None) or any(not math.isfinite(v) for v in actual) or any(abs(v)>(1.e8 if i<3 else 360) for i,v in enumerate(actual[:6])) or not 20<=actual[6]<=120:raise RuntimeError('Invalid camera acknowledgement; no retry')
        self.uncertain=False
        return actual

    def enter_photo_mode(self):
        if self.scope is not None:raise ValueError('Release flight editing before entering Photo mode')
        self.check_host(False)
        c=capture_matching(self.session.pid,names=('BP_jRPG_GI_Custom_C','EnterPhotoMode'),classes=('LocalPlayer','BP_jRPG_GI_Custom_C'))
        local=one(o for o in c.select('LocalPlayer') if not o.object_flags&0x30)
        gi=one(o for o in c.select('BP_jRPG_GI_Custom_C') if not o.object_flags&0x30 and o.outer_index==local.outer_index)
        cls=c.find_class('BP_jRPG_GI_Custom_C').index
        fn=one(o for o in c.objects if o.class_name=='Function' and o.name=='EnterPhotoMode' and o.outer_index==cls)
        scope=SessionScope(self.session)
        try:
            gi=scope.retain(gi).object;fn=scope.retain(fn).object
            self.registry.command(91,((88,self.registry.identity(gi)),(104,self.registry.identity(fn))))
        finally:scope.close()

    def check_host(self,photo_mode):
        c=capture_matching(self.session.pid,names=('Player','Controller'),classes=('LocalPlayer',))
        local=one(o for o in c.select('LocalPlayer') if not o.object_flags&0x30)
        player,c=read_object_reference(c,local,c.by_index[c.find_class('Player').index],'PlayerController')
        if player is None:raise ValueError('Player controller is not ready')
        pawn,c=read_object_reference(c,player,c.by_index[c.find_class('Controller').index],'Pawn')
        if pawn is None or pawn.class_name not in (('BP_PhotoModePawn_C',) if photo_mode else ('BP_jRPG_Character_World_C','BP_jRPG_Character_WorldMap_pawn_C')):
            raise ValueError('Photo timeline needs the game photo camera. Close this menu, open Photo mode from the game pause menu, then press Insert and choose Photo mode / timeline.' if photo_mode else 'Flight timeline needs normal exploration. Leave game Photo mode first.')

    def character_skeleton(self,role):
        # Known assembled bodies were inspected for the catalog. Raw meshes need
        # their own skeleton observation; never infer a body rig from its name.
        if CHARACTERS[role].get('skeleton'):return CHARACTERS[role]['skeleton']
        if not CHARACTERS[role].get('raw'):return BODY_SKELETON
        path=CHARACTERS[role]['parts'][0]['path']
        cache=getattr(self,'character_skeletons',{})
        if path in cache:return cache[path]
        if self.session is None:return None
        scope=SessionScope(self.session);loading=False
        try:
            c=capture_matching(self.session.pid,names=(path.rsplit('.',1)[-1],'SkeletalMesh'))
            rows=[o for o in c.select('SkeletalMesh') if c.path_name(o)==path and not o.object_flags&0x40000000]
            if len(rows)==1:obj=scope.retain(rows[0]).object
            else:
                if self.authoring:raise ValueError('Selected scene mesh is unavailable')
                loading=True;obj=self.registry.load(scope,path,0)
                c=capture_matching(self.session.pid,names=(path.rsplit('.',1)[-1],'SkeletalMesh'))
            c=capture_selected(self.session.pid,((obj.index,obj.serial,obj.address),));obj=c.by_index[obj.index]
            skeleton,c=read_object_reference(c,obj,c.by_index[c.find_class('SkeletalMesh').index],'Skeleton')
            value=c.path_name(skeleton) if skeleton else None
            cache[path]=value;self.character_skeletons=cache
            return value
        finally:
            if not self.uncertain:
                if loading:self.registry.release_loading()
                scope.close()

    def incompatible_animations(self,scene):
        actors={a['id']:a for a in scene['actors']};issues=[]
        for event in scene['events']:
            if event['type']!='animation' or event['params']['asset']=='bind_pose':continue
            actor=actors[event['target']];clip=event['params']['asset']
            if self.character_skeleton(actor['assembly'])!=ANIMATIONS[clip]['skeleton']:issues.append((actor,event))
        return issues

    def validate_animations(self,scene):
        issues=self.incompatible_animations(scene)
        if issues:
            actor,event=issues[0]
            raise ValueError(actor['name']+' cannot use '+ANIMATIONS[event['params']['asset']]['label']+' (different skeletons). Open its animation menu and choose Clear incompatible clips, then choose a compatible set or keep Bind pose.')

    def _inputs(self,scene):
        context=controller_context(self.session)
        # Reuse SDK asset ownership; native owner acquires its own leases before
        # these Python leases can be released. No saved/world asset is changed.
        paths=(MESH,ANIMATION,SOUND)+EXTRA_ASSETS
        selected=[];events={e['id']:e for e in scene['events']}
        for actor in scene['actors']:
            selected.extend(p['path'] or MESH for p in CHARACTERS[actor['assembly']]['parts'])
            clip=events.get('anim-'+actor['id'],dict(params=dict(asset='bind_pose')))['params']['asset']
            selected.append(ANIMATION if clip=='bind_pose' else ANIMATIONS[clip]['path'])
        selected.extend([MESH]*(42-len(selected)))
        extra=[ANIMATION if e['params']['asset']=='bind_pose' else ANIMATIONS[e['params']['asset']]['path'] for e in scene['events'] if e['id'].startswith('useranim-')]
        extra.extend([ANIMATION]*(24-len(extra)))
        all_paths=tuple(dict.fromkeys((*paths,*EFFECTS,*selected,*extra)))
        observed=capture_matching(self.session.pid,names=sorted({p.rsplit('.',1)[1] for p in all_paths}))
        by_path={observed.path_name(o):o for o in observed.objects if not o.object_flags&0x40000000}
        loaded={}
        animation_paths={ANIMATION,EXTRA_ASSETS[3],EXTRA_ASSETS[-1]}|{a['path'] for a in ANIMATIONS.values()}
        mesh_paths=(set(paths)|set(selected))-{SOUND}-animation_paths
        for path in all_paths:
            # Retain validates current identities natively; observations are not cached.
            if path in by_path:loaded[path]=self.scope.retain(by_path[path]).object
            elif path in animation_paths:loaded[path]=self.registry.load(self.scope,path,1)
            elif path in mesh_paths:loaded[path]=self.registry.load(self.scope,path,0)
            else:loaded[path]=load_asset(self.scope,path).return_value
        assets=[loaded[path] for path in paths];effects=[loaded[path] for path in EFFECTS]
        names={name for _,name in REUSED+ADDITIONAL};names.update(('SetTickableWhenPaused','SetComponentTickEnabled','SetControlRotation','SetPosition','StaticMeshActor','StaticMeshComponent','Cube','SetStaticMesh','M_DebugEmissive1','SetMaterial','GetMaterial','GetNumMaterials','GetInputMouseDelta','SetVolumeMultiplier'))
        names.update(('Default__GameplayStatics','CameraActor','SkeletalMeshActor',
            'SkeletalMeshComponent','CameraComponent','Skeleton'))
        names.update(path.rsplit('.',1)[1] for path in paths)
        names.update(path.rsplit('.',1)[1] for path in EFFECTS)
        names.update(path.rsplit('.',1)[1] for path in (*selected,*extra))
        names.update(('Default__NiagaraFunctionLibrary','NiagaraFunctionLibrary','SpawnSystemAtLocation'))
        c=capture_matching(self.session.pid,names=sorted(names),classes=('LocalPlayer',))
        local=one(o for o in c.select('LocalPlayer') if not o.object_flags&0x30)
        player,c=read_object_reference(c,local,c.by_index[c.find_class('Player').index],'PlayerController')
        if player is None:raise RuntimeError('Current player controller unavailable')
        pawn,c=read_object_reference(c,player,c.by_index[c.find_class('Controller').index],'Pawn')
        if pawn is None or pawn.class_name not in (('BP_PhotoModePawn_C',) if self.photo_mode else ('BP_jRPG_Character_World_C','BP_jRPG_Character_WorldMap_pawn_C')):
            raise RuntimeError('Open game photo mode first' if self.photo_mode else 'Use normal exploration for flight editing, or choose Photo mode / timeline')
        if context!=controller_context(self.session):raise RuntimeError('World/controller changed during preparation')
        def cls(name):return c.by_index[c.find_class(name).index]
        self.photo_rotation=one(o for o in c.objects if o.name=='SetControlRotation' and o.class_name=='Function' and o.outer_index==cls('Controller').index) if self.photo_mode else None
        self.photo_ticks=tuple(one(o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==cls('ActorComponent').index) for name in ('SetTickableWhenPaused','SetComponentTickEnabled')) if self.photo_mode else ()
        result=[local,player,pawn,one(o for o in c.objects if o.name=='Default__GameplayStatics'),
            cls('CameraActor'),cls('SkeletalMeshActor'),cls('SkeletalMeshComponent'),
            *(c.resolve(o) for o in assets[:3]),cls('Skeleton'),cls('CameraComponent'),
            *(c.resolve(o) for o in assets[3:])]
        for owner,name in REUSED+ADDITIONAL:
            result.append(one(o for o in c.objects if o.name==name and o.class_name=='Function'
                and o.outer_index==cls(owner).index))
        result.append(one(o for o in c.objects if o.name=='Default__NiagaraFunctionLibrary'))
        result.extend(c.resolve(o) for o in effects)
        for owner,name in (('NiagaraFunctionLibrary','SpawnSystemAtLocation'),):
            result.append(one(o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==cls(owner).index))
        result.extend(c.resolve(loaded[path]) for path in selected)
        result.append(one(o for o in c.objects if o.name=='SetPosition' and o.class_name=='Function' and o.outer_index==cls('SkeletalMeshComponent').index))
        result.extend((cls('StaticMeshActor'),cls('StaticMeshComponent'),c.find_path('/Engine/BasicShapes/Cube.Cube','StaticMesh'),one(o for o in c.objects if o.name=='SetStaticMesh' and o.class_name=='Function' and o.outer_index==cls('StaticMeshComponent').index)))
        result.append(c.find_path('/Game/LevelTools/FreeAimTargets/M_DebugEmissive1.M_DebugEmissive1'))
        for owner,name in (('PrimitiveComponent','SetMaterial'),('PrimitiveComponent','GetMaterial'),('PrimitiveComponent','GetNumMaterials'),('PlayerController','GetInputMouseDelta')):
            result.append(one(o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==cls(owner).index))
        result.extend(c.resolve(loaded[path]) for path in extra)
        result.append(one(o for o in c.objects if o.name=='SetVolumeMultiplier' and o.class_name=='Function' and o.outer_index==cls('AudioComponent').index))
        return result

    def start(self,scene,*,authoring=False,editor_camera=None,photo_mode=False):
        scene=validate(scene)
        if controller_context(self.session)['world_path']!=scene['target_map']:raise ValueError('Load the scene target map before previewing')
        self.scene_duration=scene['duration']
        self.scene_characters=[a['name'] for a in scene['actors']]
        if self.scope is not None:raise RuntimeError('Stop the previous demo first')
        if getattr(self.session._session._transport,'runtime_scene_protocol',0)!=7:
            raise RuntimeError('Scene Editor requires its isolated native candidate')
        if photo_mode and not authoring:raise ValueError('Photo mode is an authoring host')
        self.validate_animations(scene)
        self.photo_mode=bool(photo_mode)
        self.scope=SessionScope(self.session)
        try:
            if any(e['id'].startswith('useraudio-') and e['params']['asset']!='sound' for e in scene['events']):self.registry.catalog(2)
            self._command(74,payload=self._encode(scene,editor_camera,reset=True))
            self._command(70,self._inputs(scene))
            self.configure_audio(scene)
            self.registry.release_loading()
            if scene.get('mute_game_music',False):self.set_music_quiet(True)
            self._command(75 if authoring else 71,payload=b''.join(IDENTITY.pack(o.index,o.serial,o.address) for o in (self.photo_rotation,*self.photo_ticks)) if self.photo_mode else b'')
        except BaseException:
            if not self.uncertain:
                self.registry.release_loading();self.stop()
            raise
        return self.status()

    def insert_animation(self,scene,event_id):
        if not self.authoring:raise ValueError('Enter live authoring first')
        self.validate_animations(scene);self.editor_control(0)
        self._slots(scene);event=next(e for e in scene['events'] if e['id']==event_id)
        scope=SessionScope(self.session)
        try:
            asset=self.registry.load(scope,ANIMATIONS[event['params']['asset']]['path'],1)
            raw=self.registry.command(98,((88,self.registry.identity(asset)),(104,struct.pack('<I',self.animation_slots[event_id])),(112,self._encode(scene,self.last['editor_camera']))))
            self._command(73)
        finally:
            if not self.uncertain:self.registry.release_loading();scope.close()
        return self.status()

    def apply(self,scene):
        if not self.authoring:raise ValueError('Enter live authoring first')
        self.validate_animations(scene)
        old_audio=dict(self.audio_event_slots);old_animation=dict(self.animation_slots)
        try:return self._command(76,payload=self._encode(scene,self.last['editor_camera']))
        except BaseException:
            self.audio_event_slots=old_audio;self.animation_slots=old_animation;raise

    def _slots(self,scene,reset=False):
        for prefix,field,limit in (('useraudio-','audio_event_slots',23),('useranim-','animation_slots',24)):
            events=[e['id'] for e in scene['events'] if e['id'].startswith(prefix)]
            previous={} if reset else getattr(self,field)
            slots={key:slot for key,slot in previous.items() if key in events}
            for key in events:
                if key not in slots:slots[key]=next(i for i in range(limit) if i not in slots.values())
            setattr(self,field,slots)
    def _encode(self,scene,camera=None,reset=False):
        self._slots(scene,reset)
        return encode(scene,camera,audio_slots=self.audio_event_slots,animation_slots=self.animation_slots)
    def configure_audio(self,scene):
        self._slots(scene)
        for event in (e for e in scene['events'] if e['id'].startswith('useraudio-')):
            slot=self.audio_event_slots[event['id']];path=event['params']['asset']
            if path=='sound':continue
            if self.audio_slots.get(slot)==path:continue
            if slot in self.audio_slots:raise ValueError('Remove the clip before changing its sound')
            kind=self.registry.audio_kind(path);rows=self.registry.catalog(kind)
            self.audio_load_scope=SessionScope(self.session)
            try:
                source=self.registry.load(self.audio_load_scope,path,kind)
                self.registry.command(83,((88,self.registry.identity(source)),(104,struct.pack('<III',slot,rows.index(path),kind))))
                self.audio_slots[slot]=path
                self.registry.release_loading()
            finally:
                if not self.uncertain:
                    self.registry.release_loading();self.audio_load_scope.close();self.audio_load_scope=None
        self.registry.release_loading()
    def drop_audio(self,slot):
        self.registry.command(86,((88,struct.pack('<2d',slot,0)),))
        self.audio_slots.pop(slot,None)
    def set_music_quiet(self,enabled):
        payload=[(88,struct.pack('<d',int(enabled)))]
        if enabled:
            c=capture_matching(self.session.pid,names=('Default__AudioComponent','SetPaused'),classes=('BP_jRPG_GI_Custom_C',))
            gi=one(o for o in c.select('BP_jRPG_GI_Custom_C') if not o.object_flags&0x30)
            original,c=read_object_reference(c,gi,c.by_index[gi.class_index],'InteractiveMusicSystem')
            if original is None:raise ValueError('Game interactive music system is unavailable')
            audio=c.by_index[c.find_class('AudioComponent').index]
            default=one(o for o in c.objects if o.name=='Default__AudioComponent' and o.class_index==audio.index)
            function=one(o for o in c.objects if o.name=='SetPaused' and o.class_name=='Function' and o.outer_index==audio.index)
            payload.extend((96+16*i,self.registry.identity(obj)) for i,obj in enumerate((original,audio,default,function)))
        raw=self.registry.command(87,tuple(payload))
        if enabled:self.music_components=struct.unpack_from('<I',raw,20976)[0]
        self.last['game_music_muted']=bool(enabled)

    def preview_audio(self,path):
        if not self.authoring:raise ValueError('Enter live editing first')
        from .scene import sound_path
        sound_path(path);kind=self.registry.audio_kind(path);rows=self.registry.catalog(kind)
        if path not in rows:raise ValueError('Choose a sound from the game library')
        self.editor_control(0);self.stop_audio_preview()
        self.preview_scope=SessionScope(self.session)
        try:
            source=self.registry.load(self.preview_scope,path,kind)
            self.registry.command(84,((88,self.registry.identity(source)),(104,struct.pack('<III',23,rows.index(path),kind))))
            self.registry.release_loading()
        except BaseException:
            if not self.uncertain:self.stop_audio_preview()
            raise

    def stop_audio_preview(self):
        if self.scope is not None:self.registry.command(85,())
        if self.preview_scope is not None:self.preview_scope.close();self.preview_scope=None

    def photo_settings_open(self):
        if not self.photo_mode:return False
        now=time.monotonic()
        if now>=getattr(self,'next_photo_settings',0.):
            self.photo_settings_cached=bool(self.registry.command(90,())[104]);self.next_photo_settings=now+.1
        return self.photo_settings_cached

    def timeline_owner(self, panel, keep, shortcuts=True):
        binding=getattr(panel,'scene_binding',None)
        if binding is None:
            c=capture_matching(self.session.pid,names=('AddToViewport','UserWidget'))
            cls=c.by_index[c.find_class('UserWidget').index]
            function=one(o for o in c.objects if o.class_name=='Function' and o.name=='AddToViewport' and o.outer_index==cls.index)
            binding=(panel.widget,panel.scope.retain(function).object)
            panel.scene_binding=binding
        widget,function=binding
        self.registry.command(88,((88,self.registry.identity(widget)),(104,self.registry.identity(function)),(120,struct.pack('<I',int(keep)|int(shortcuts)*2))))

    def audition(self,slot,play=True):
        return self._command(77,payload=struct.pack('<2d',slot,int(play)))

    def seek(self,seconds):return self._command(78,payload=struct.pack('<2d',seconds,0))
    def editor_control(self,action,option=0):
        if action==1 and self.preview_scope is not None:self.stop_audio_preview()
        return self._command(79,payload=struct.pack('<2d',action,option))

    def sync_document(self,scene):
        if not self.authoring or self.author_plan is None:return scene
        import copy
        result=copy.deepcopy(scene);result['anchor']=list(self.author_plan[142:146])
        for i,actor in enumerate(result['actors']):
            pose=self.author_plan[8+9*i:17+9*i];actor['transform']=dict(position=list(pose[:3]),rotation=list(pose[3:6]),scale=list(pose[6:9]))
            event=next((e for e in result['events'] if e['id']=='anim-'+actor['id']),None)
            if event is not None:event['at']=self.author_plan[62+i]
        by_id={e['id']:e for e in result['events']}
        audio_events=[e for e in result['events'] if e['id'].startswith('useraudio-')]
        audio_slots=self.audio_event_slots or {e['id']:i for i,e in enumerate(audio_events)}
        audio=[(i,by_id.get('audio-'+str(i))) for i in range(9)]+[(9+audio_slots[e['id']],e) for e in audio_events]
        for i,event in audio:
            if event is not None:
                if self.author_plan[83+i]>=0:event['at']=self.author_plan[83+i]
                event['params']['volume']=self.author_plan[380+i]
        extra=[e for e in result['events'] if e['id'].startswith('useranim-')]
        animation_slots=self.animation_slots or {e['id']:i for i,e in enumerate(extra)}
        if max((animation_slots[e['id']]+1 for e in extra),default=0)!=int(self.author_plan[283]):raise RuntimeError('Animation clip list changed outside the scene owner')
        for event in extra:event['at']=self.author_plan[285+4*animation_slots[event['id']]]
        keys=result.get('camera_keys',[])
        count=int(self.author_plan[154])
        if count==len(keys)+1:
            import uuid
            native_times=[self.author_plan[155+8*i] for i in range(count)]
            inserted=[i for i,t in enumerate(native_times) if not any(abs(k['at']-t)<.00001 for k in keys)]
            if len(inserted)!=1:raise RuntimeError('Ambiguous camera key insertion')
            keys.insert(inserted[0],dict(id='camera-'+uuid.uuid4().hex[:12]))
            result['camera_keys']=keys
        if len(keys)!=count:raise RuntimeError('Camera key list changed outside the current scene owner')
        for i,key in enumerate(keys):
            at=155+8*i;row=self.author_plan[at:at+8]
            key.update(at=row[0],position=list(row[1:4]),rotation=list(row[4:7]),fov=row[7])
        return validate(result)

    def stop(self,_=None):
        if self.scope is None:return self.status()
        if self.preview_scope is not None:self.stop_audio_preview()
        self._command(72)
        if self.last['private_leases']==0:
            if self.audio_load_scope is not None:self.audio_load_scope.close();self.audio_load_scope=None
            self.scope.close();self.scope=None;self.audio_slots={};self.audio_event_slots={};self.animation_slots={}
        return self.status()

    def poll(self):
        if self.scope is None or self.uncertain or time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+.1
        self._command(73)
        if self.last['private_leases']==0:
            if self.preview_scope is not None:self.preview_scope.close();self.preview_scope=None
            if self.audio_load_scope is not None:self.audio_load_scope.close();self.audio_load_scope=None
            self.scope.close();self.scope=None
            self.audio_slots={};self.audio_event_slots={};self.animation_slots={}

    def status(self,_=None):
        return dict(self.last,uncertain=self.uncertain,game_music_components=self.music_components,duration_seconds=getattr(self,'scene_duration',20),characters=getattr(self,'scene_characters',['Lune','Maelle']),
            assets=dict(mesh=MESH,animation=ANIMATION,sound=SOUND))

    def disable(self):
        if self.scope is not None:
            self.stop()
            if self.scope is not None:raise RuntimeError('Native cinematic cleanup is still pending')
        self.session=None
