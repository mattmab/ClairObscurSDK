"""Experimental fixed twenty-second Lune/Maelle scene; isolated backend only."""
import secrets
import struct
import time
from expedition33._scope import SessionScope
from expedition33.assets import load_asset
from expedition33.catalog import capture_matching
from expedition33.values import read_object_reference
from expedition33.cinematics.original_game_action import controller_context
from expedition33.management import Action, ModDefinition
from expedition33._runtime_cinematic_wire import validate_request

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
STATES={0:'idle',1:'prepared',2:'playing',3:'cleanup_pending',4:'finished',5:'interrupted',6:'failed'}


def one(rows):
    rows=tuple(rows)
    if len(rows)!=1:raise RuntimeError('Expected one current cinematic dependency')
    return rows[0]


class Mod:
    def __init__(self):
        self.session=self.scope=None
        self.owner=secrets.randbits(64) or 1
        self.last=dict(state='idle',live_success=False)
        self.next_poll=0.
        self.uncertain=False

    def management(self):
        return ModDefinition('experimental.runtime-cinematic','Runtime Cinematic Demo',version='0.2-experimental',
            description='Twenty-second staged Lune/Maelle attacks against a temporary target, orbiting camera and quiet sound; isolated backend required.',
            actions=(Action('start','Run experimental twenty-second scene',self.start),
                     Action('stop','Interrupt and clean up',self.stop),Action('status','Demo status',self.status)))

    def enable(self,session):
        self.session=session
        session.console.expose('runtime_cinematic',self)
        def command(argument):
            operation=argument.strip() or 'status'
            if operation not in ('start','stop','status'):raise ValueError('cine.demo start|stop|status')
            print(getattr(self,operation)())
        session.console.register('cine.demo',command,owner=self)

    def _command(self,op,ids=()):
        transport=self.session._session._transport
        if getattr(transport,'runtime_cinematic_protocol',0)!=2:
            raise RuntimeError('Use the isolated runtime-cinematic candidate; installed backend is unchanged')
        if self.uncertain:raise RuntimeError('Unknown native outcome; native backend teardown owns cleanup')
        packet=bytearray(SIZE);HEADER.pack_into(packet,0,3,op,0,0,self.owner)
        if op==70 and len(ids)!=57:raise ValueError('Exact cinematic input count required')
        if op!=70 and ids:raise ValueError('Only prepare accepts identities')
        for i,obj in enumerate(ids):IDENTITY.pack_into(packet,88+16*i,obj.index,obj.serial,obj.address)
        validate_request(bytes(packet))
        self.uncertain=True
        raw=bytes.fromhex(transport.command('mesh',bytes(packet))['mesh_packet'])
        if len(raw)!=SIZE or raw[:8]!=packet[:8] or raw[16:24]!=packet[16:24] or raw[88:20976]!=packet[88:20976]:
            raise RuntimeError('Cinematic acknowledgement mismatch; no retry')
        _,_,error,state,_=HEADER.unpack_from(raw)
        if state not in STATES:raise RuntimeError('Unknown cinematic state; no retry')
        self.uncertain=False
        active,poses=struct.unpack_from('<II',raw,20976)
        mask=struct.unpack_from('<I',raw,84)[0]
        elapsed,animation_at,audio_at=struct.unpack_from('<3d',raw,56)
        self.last=dict(state=STATES[state],error=error,step=struct.unpack_from('<I',raw,80)[0],
            elapsed=elapsed,animation_at=animation_at,audio_at=audio_at,camera_updates=poses,
            private_leases=active,animation_dispatched=bool(mask&1),audio_dispatched=bool(mask&2),audio_cues_dispatched=(mask>>8)&255,effects_spawned=(mask>>16)&255,
            live_success=False,requires_visual_audio_confirmation=True)
        if error and error!=407:raise RuntimeError('Native cinematic rejected/failed: '+str(self.last))
        return self.last

    def _inputs(self):
        context=controller_context(self.session)
        # Reuse SDK asset ownership; native owner acquires its own leases before
        # these Python leases can be released. No saved/world asset is changed.
        paths=(MESH,ANIMATION,SOUND)+EXTRA_ASSETS
        assets=[load_asset(self.scope,path).return_value for path in paths]
        effects=[load_asset(self.scope,path).return_value for path in EFFECTS]
        names={name for _,name in REUSED+ADDITIONAL}
        names.update(('Default__GameplayStatics','CameraActor','SkeletalMeshActor',
            'SkeletalMeshComponent','CameraComponent','Skeleton'))
        names.update(path.rsplit('.',1)[1] for path in paths)
        names.update(path.rsplit('.',1)[1] for path in EFFECTS)
        names.update(('Default__NiagaraFunctionLibrary','NiagaraFunctionLibrary','SpawnSystemAtLocation'))
        c=capture_matching(self.session.pid,names=sorted(names),classes=('LocalPlayer',))
        local=one(o for o in c.select('LocalPlayer') if not o.object_flags&0x30)
        player,c=read_object_reference(c,local,c.by_index[c.find_class('Player').index],'PlayerController')
        if player is None:raise RuntimeError('Current player controller unavailable')
        pawn,c=read_object_reference(c,player,c.by_index[c.find_class('Controller').index],'Pawn')
        if pawn is None or pawn.class_name not in ('BP_jRPG_Character_World_C','BP_jRPG_Character_WorldMap_pawn_C'):
            raise RuntimeError('Dismount and use normal exploration gameplay')
        if context!=controller_context(self.session):raise RuntimeError('World/controller changed during preparation')
        def cls(name):return c.by_index[c.find_class(name).index]
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
        return result

    def start(self,_=None):
        if self.scope is not None:raise RuntimeError('Stop the previous demo first')
        if getattr(self.session._session._transport,'runtime_cinematic_protocol',0)!=2:
            raise RuntimeError('Demo requires the isolated runtime-cinematic candidate')
        self.scope=SessionScope(self.session)
        try:
            self._command(70,self._inputs())
            self._command(71)
        except BaseException:
            if not self.uncertain:self.stop()
            raise
        return self.status()

    def stop(self,_=None):
        if self.scope is None:return self.status()
        self._command(72)
        if self.last['private_leases']==0:
            self.scope.close();self.scope=None
        return self.status()

    def poll(self):
        if self.scope is None or self.uncertain or time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+.1
        self._command(73)
        if self.last['private_leases']==0:
            self.scope.close();self.scope=None

    def status(self,_=None):
        return dict(self.last,uncertain=self.uncertain,duration_seconds=20,characters=['Lune','Maelle'],
            assets=dict(mesh=MESH,animation=ANIMATION,sound=SOUND))

    def disable(self):
        if self.scope is not None:
            self.stop()
            if self.scope is not None:raise RuntimeError('Native cinematic cleanup is still pending')
        self.session=None
