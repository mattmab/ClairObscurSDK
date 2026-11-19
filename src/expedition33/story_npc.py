"""Original E-interaction NPC, configured before its collision is enabled.

Only the native-owned reviewed carrier can be configured by this protocol. The
original NPC then creates BP_Dialogue with its own cameras, input and completion.
"""
from . import RuntimeQueryError
from . import _story_npc_wire as wire

# Audited original carrier: CapsuleHalfHeight=88, Mesh.RelativeLocation.Z=-88.
# Story placements describe feet; native dialogue camera/player markers are
# relative to the capsule center, whereas cinematic Blueprint poses use feet.
def carrier_pose(pose):
    from .cinematics.blueprint_actor import transform
    pose=list(transform(pose));pose[6]+=88.
    return transform(pose)


CHARACTER_VISUAL_PROFILES=frozenset(('sophie','clea-spirit','renoir-spirit'))


def visual_pose(pose,profile=None):
    """Cinematic rigs face local +Y; placements use the carrier's +X."""
    import math
    from .cinematics.blueprint_actor import transform
    pose=list(transform(pose))
    if profile in CHARACTER_VISUAL_PROFILES:
        # These reviewed original NPC Blueprints use capsule-center origins
        # and already include the Character mesh's local facing correction.
        pose[6]+=88.
        return transform(pose)
    x,y,z,w=pose[:4];c=math.sqrt(.5);s=-c
    pose[:4]=(x*c+y*s,y*c-x*s,z*c+w*s,w*c-z*s)
    return transform(pose)


def decode(sent,reply):
    import struct
    if type(reply) is not bytes or len(reply)!=wire.SIZE or reply[:8]!=sent[:8] or reply[16:]!=sent[16:]:
        raise RuntimeQueryError('Story NPC acknowledgement differs from request')
    error,state=struct.unpack_from('<II',reply,8)
    if error or state!=1:raise RuntimeQueryError('Original story NPC configuration failed ('+str(error)+')')


class StoryNpc:
    def __init__(self,parent):
        parent._check()
        capability=getattr(parent._session._transport,'story_npc_blueprint_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeQueryError('Original story NPC runtime required')
        from .cinematics.blueprint_actor import BlueprintActor
        self.actor=BlueprintActor(parent);self.scope=self.actor.scope
        self.visual=None;self.state='new';self.speaker=None;self.dialogue_class=None;self.definitions=None;self.system_cdo=None;self._speaker_unknown=False

    @property
    def identity(self):return self.actor.identity

    def set_interaction_enabled(self,enabled):
        """Gate the owned carrier before native dialogue can release input."""
        if type(enabled) is not bool:raise TypeError('Boolean interaction gate required')
        if self.state!='visible':raise RuntimeError('Visible story NPC required')
        if enabled and getattr(self,'_presentation_only_reveal',False):raise RuntimeError('Presentation carrier cannot enable interaction')
        if getattr(self,'_interaction_enabled',True)==enabled:return
        from .catalog import capture_matching,capture_selected
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        c=(prepared.catalog(self.scope,('SetActorEnableCollision',)) if prepared is not None
            else capture_matching(self.scope.pid,names=('SetActorEnableCollision',)))
        c=c.with_observations(capture_selected(self.scope.pid,(self.identity,)))
        with (prepared.movement_planner(self.scope,c) if prepared is not None
                else self.scope.invocation_planner(catalog=c,selected_results=True)) as planner:
            with planner.prepare(c.by_index[self.identity[0]],c.find_path('/Script/Engine.Actor:SetActorEnableCollision'),bNewActorEnableCollision=enabled).invoke():pass
        self._interaction_enabled=enabled

    def set_visual_visible(self,visible):
        if self.visual is None:return
        if visible and self.visual.state=='prepared':
            self.visual.reveal()
            return
        from .catalog import capture_matching,capture_selected
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        c=(prepared.catalog(self.scope,('SetActorHiddenInGame',)) if prepared is not None
            else capture_matching(self.scope.pid,names=('SetActorHiddenInGame',)))
        c=c.with_observations(capture_selected(self.scope.pid,(self.visual.identity,)))
        with (prepared.movement_planner(self.scope,c) if prepared is not None
                else self.scope.invocation_planner(catalog=c,selected_results=True)) as planner:
            with planner.prepare(c.by_index[self.visual.identity[0]],c.find_path('/Script/Engine.Actor:SetActorHiddenInGame'),bNewHidden=not visible).invoke():pass

    def prepare(self,transform,speaker_asset,*,visual_profile='faceless-boy',speaker_name=None):
        if self.state!='new':raise RuntimeError('Story NPC construction is never replayed')
        if speaker_name is not None and getattr(self.scope._session._transport,'story_speaker_name_protocol',0)!=1:
            raise RuntimeQueryError('Named story NPCs require the owned speaker runtime')
        self.state='preparing'
        self._visual_transform=tuple(transform)
        try:
            from .assets import load_asset
            from .picto_class_load import load_class
            from .catalog import capture_matching,capture_selected
            prepared=getattr(self.scope._session,'_story_construction_resources',None)
            self.speaker=prepared.resources.load(speaker_asset) if prepared is not None else load_asset(self.scope,speaker_asset).return_value
            if self.speaker is None or self.speaker.class_name!='BP_DataAsset_DialogueCharacter_C':
                raise ValueError('Select a native dialogue speaker profile')
            path='/Game/Gameplay/DialogueSystem/BP_Dialogue.BP_Dialogue_C'
            self.dialogue_class=prepared.resources.load(path,cls=True) if prepared is not None else load_class(self.scope,path).return_value
            if self.dialogue_class is None:raise RuntimeError('Original base dialogue class did not load')
            names=('Default__KismetSystemLibrary','SetClassPropertyByName','SetObjectPropertyByName','SetBoolPropertyByName','SetActorEnableCollision')
            catalog=prepared.catalog(self.scope,names) if prepared is not None else capture_matching(self.scope.pid,names=names)
            self.system_cdo=catalog.find_path('/Script/Engine.Default__KismetSystemLibrary')
            self.definitions=tuple(catalog.find_path('/Script/Engine.'+owner+':'+name) for owner,name in (
                ('KismetSystemLibrary','SetClassPropertyByName'),('KismetSystemLibrary','SetObjectPropertyByName'),
                ('KismetSystemLibrary','SetBoolPropertyByName'),('Actor','SetActorEnableCollision')))
            self.actor.prepare_story_npc(carrier_pose(transform))
            # BlueprintActor just validated this exact result together with the
            # post-spawn world/controller proof. Native configuration below
            # validates its live owned actor again; no second reader roundtrip.
            self.npc=self.actor.prepared_actor
            if self.npc is None or (self.npc.index,self.npc.serial,self.npc.address)!=self.identity:
                raise RuntimeError('Story carrier construction result is unavailable')
            if speaker_name is not None:self._create_speaker(speaker_name)
            self._configure(False)
            # The original Empty NPC is the native interaction/camera carrier;
            # its audited default Mesh is None. Construct the reviewed original
            # cinematic Blueprint for presentation, with the same authored pose.
            if visual_profile is not None:
                from .cinematics.blueprint_actor import BlueprintActor
                self.visual=BlueprintActor(self.scope)
                self.visual.prepare(visual_profile,visual_pose(transform,visual_profile))
            self.state='prepared'
        except BaseException:
            self.state='failed';raise
        return self.identity

    def ensure_visual(self,profile):
        """Construct one hidden fallback for an already prepared empty carrier.

        A borrowed party actor does not need a duplicate visual. If that role
        later leaves, the caller may prepare its fallback pose before reveal.
        Failed/uncertain construction stays reachable and is never replayed.
        """
        if self.state not in ('prepared','visible'):
            raise RuntimeError('Prepared story carrier required for a fallback visual')
        if self.visual is not None:
            if self.visual.profile!=profile or self.visual.state not in ('prepared','visible'):
                raise RuntimeError('Existing story visual is different or unfinished; not replayed')
            return self.visual
        from .cinematics.blueprint_actor import BlueprintActor
        try:
            self.visual=BlueprintActor(self.scope)
            self.visual.prepare(profile,visual_pose(self._visual_transform,profile))
        except BaseException:self.state='failed';raise
        return self.visual

    def _spawn_speaker(self,catalog,cls):
        from .catalog import capture_selected
        library=catalog.find_path('/Script/Engine.Default__GameplayStatics')
        function=catalog.find_path('/Script/Engine.GameplayStatics:SpawnObject')
        # Factory results use a fresh selected closure: an unrelated map object
        # changing during a full catalog read must not invalidate this result.
        selected=capture_selected(self.scope.pid,tuple((o.index,o.serial,o.address)
            for o in (library,function,cls,self.npc)))
        prepared=getattr(getattr(self.scope,'_session',None),'_story_construction_resources',None)
        planner=(prepared.movement_planner(self.scope,selected) if prepared is not None
            else self.scope.invocation_planner(selected_results=True,catalog=selected))
        return planner.prepare(library,function,ObjectClass=cls,Outer=self.npc).invoke(fresh_results=True)

    def _create_speaker(self,name):
        from . import _story_speaker_wire as speaker_wire
        from ._stable_lease import acquire_stable
        from .catalog import capture_matching
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        names=('SpawnObject','Default__GameplayStatics','SetTextPropertyByName')
        c=prepared.catalog(self.scope,names) if prepared is not None else capture_matching(self.scope.pid,names=names)
        path='/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter.BP_DataAsset_DialogueCharacter_C'
        cls=prepared.resources.load(path,cls=True) if prepared is not None else capture_matching(self.scope.pid,names=('BP_DataAsset_DialogueCharacter_C',)).find_path(
            '/Game/Gameplay/DialogueSystem/BP_DataAsset_DialogueCharacter.BP_DataAsset_DialogueCharacter_C')
        created=self._spawn_speaker(c,cls)
        speaker=created.return_value
        if (speaker is None or speaker.class_name!='BP_DataAsset_DialogueCharacter_C' or
            speaker.outer_index!=self.npc.index or speaker.index==self.speaker.index):
            raise RuntimeQueryError('Story speaker construction returned another object')
        # SpawnObject already returned a native retained output in this scope.
        # Re-acquiring it adds another game-thread command but no ownership.
        # Keep the exact output lease; the name protocol checks its token,
        # current Outer, actor/world ownership and setter schema again.
        self._speaker_result=created
        held_outputs=[lease for lease in created._leases if lease.active and
            (lease.object.index,lease.object.serial,lease.object.address)==
            (speaker.index,speaker.serial,speaker.address)]
        if len(held_outputs)!=1:raise RuntimeQueryError('Story speaker requires one retained factory output')
        held=held_outputs[0]
        setter_object=c.find_path('/Script/Engine.KismetSystemLibrary:SetTextPropertyByName')
        if prepared is not None:
            # These exact metadata dependencies are already title-owned. The
            # process resource owner checks its scope and active leases; no
            # mutable actor/speaker state is shared between carriers.
            cdo=prepared.resources.hold(self.system_cdo)
            setter=prepared.resources.hold(setter_object)
        else:
            cdo,_=acquire_stable(self.scope,self.system_cdo)
            setter,_=acquire_stable(self.scope,setter_object)
        packet=speaker_wire.encode(self.actor.owner._owner,held._token,self.npc,held.object,cdo.object,setter.object,name)
        self._speaker_unknown=True
        with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
        reply=bytes.fromhex(response['mesh_packet'])
        if len(reply)!=len(packet) or reply[:8]!=packet[:8] or reply[16:]!=packet[16:]:
            raise RuntimeQueryError('Owned speaker acknowledgement changed')
        import struct
        error,state=struct.unpack_from('<II',reply,8)
        if error or state!=1:raise RuntimeQueryError('Owned story speaker configuration failed ('+str(error)+')')
        self._speaker_unknown=False;self.speaker=held.object

    def _configure(self,activate):
        packet=wire.encode(self.actor.owner._owner,self.npc,self.dialogue_class,self.speaker,self.system_cdo,self.definitions,activate=activate)
        with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
        decode(packet,bytes.fromhex(response['mesh_packet']))

    def _finalize(self,visual,interaction):
        from . import _story_npc_finalize_wire as final
        from ._timeline_actor_channel import TimelineActorOwner
        actors=(self.actor,)+((self.visual,) if visual and self.visual is not None else ())
        for actor in actors:
            actor.scope._check()
            if (actor.scope._session is not self.scope._session or actor.state!='prepared' or
                not isinstance(actor.owner,TimelineActorOwner) or actor.owner.phase!='spawned' or
                not actor.owner._timeline or not actor.owner.has_native_work):
                raise RuntimeError('Prepared owned timeline actor required for NPC finalization')
        shown=actors[1] if len(actors)==2 else None
        packet=final.encode(self.actor.owner._owner,self.npc,self.dialogue_class,self.speaker,self.system_cdo,self.definitions,
            interaction=interaction,visual_owner=shown.owner._owner if shown is not None else 0,
            visual=shown.identity if shown is not None else None)
        for actor in actors:actor.state='revealing';actor.owner.phase='dispatching'
        try:
            with self.scope._lease_context():response=self.scope._session._transport.command('mesh',packet)
            completed,attempted=final.decode(packet,response['mesh_packet'])
        except BaseException as error:
            # A verified prefix can describe a revealed actor, but never grants
            # permission to replay the unfinished transaction or activate it.
            for bit,actor in zip((1,2),actors):
                if isinstance(error,final.FinalizationError) and error.completed&bit:
                    actor.state='visible';actor.owner.phase='visible'
                elif isinstance(error,final.FinalizationError) and not error.attempted&bit:
                    actor.state='prepared';actor.owner.phase='spawned'
                else:actor.state='failed';actor.owner.phase='unknown'
            raise
        for actor in actors:actor.state='visible';actor.owner.phase='visible'
        self._interaction_enabled=interaction

    def reveal(self,*,visual=True,interaction=True):
        if type(visual) is not bool or type(interaction) is not bool:raise TypeError('Boolean visual and interaction gates required')
        if self.state!='prepared':raise RuntimeError('Prepared original story NPC required')
        self.state='activating'
        try:
            from ._story_npc_finalize_wire import available
            if available(self.scope):self._finalize(visual,interaction)
            else:
                self.actor.reveal()
                if self.visual is not None and visual:self.visual.reveal()
                self._configure(True)
                self._interaction_enabled=True
                if not interaction:
                    self.state='visible';self.set_interaction_enabled(False)
        except BaseException:
            self.state='failed';raise
        self.state='visible';return self.identity

    def reveal_presentation(self):
        """Prepare a camera/speaker carrier without ever enabling interaction.

        Initial configuration already set CanBeInteractedWith=False. Unlike
        reveal(), this path must not run the native interactive activation.
        Its visual remains hidden until the dialogue driver reveals its cast.
        """
        if self.state!='prepared':raise RuntimeError('Prepared original story NPC required')
        self.state='activating';self._presentation_only_reveal=True
        try:
            self.actor.reveal()
            # Original timeline reveal already acknowledged collision=False.
            self._interaction_enabled=False
            self.state='visible'
            self.set_interaction_enabled(False)
        except BaseException:
            self.state='failed';raise
        return self.identity

    def move(self,location,yaw,*,visual=True):
        if type(visual) is not bool:raise TypeError('Boolean visual placement required')
        if self.state!='visible':raise RuntimeError('Visible original story NPC required')
        self.state='moving'
        try:
            self.actor.move((location[0],location[1],location[2]+88.),yaw,placement=True)
            if self.visual is not None and visual:
                centered=self.visual.profile in CHARACTER_VISUAL_PROFILES
                self.visual.move((location[0],location[1],location[2]+(88. if centered else 0.)),yaw if centered else yaw-90.,placement=True)
        except BaseException:
            self.state='failed';raise
        self.state='visible'

    def retire_world(self):
        if getattr(self,'_speaker_unknown',False):return False
        if self.visual is not None and not self.visual.retire_world():return False
        if self.actor.retire_world():self.state='closed';return True
        return False

    def close(self):
        if getattr(self,'_speaker_unknown',False):return False
        if self.visual is not None and not self.visual.close():return False
        if self.actor.close():self.state='closed';return True
        return False
