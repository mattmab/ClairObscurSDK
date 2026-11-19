"""Owned original facial-expression/talking performance with explicit restoration."""
import time
from ._scope import SessionScope
from ._stable_lease import acquire_stable
from .catalog import capture_matching,capture_selected
from .reflection import describe_selected
from .values import capture_selected_values
from .story_dialogue import field,identity

HUMAN='/Game/MetaHumans/Common/Face/Face_AnimBP_HumanNPC.Face_AnimBP_HumanNPC_C'
MOUTH='/Game/Animations/Facial/RandomDialogue_Animation/RandomDialogueAnim_Face_2.RandomDialogueAnim_Face_2'
SKIN='/Game/Gameplay/CharacterCustomization/Blueprints/BP_CharacterSkinComponent.BP_CharacterSkinComponent_C:'
NPC='/Game/Characters/NPCs/Animations/BP_NPCAnimationComponent.BP_NPCAnimationComponent_C:'
FACE=HUMAN+':'

def current_skin(scope,actor):
    """Fresh actor-owned membership, without enumerating unrelated world objects."""
    from .values import StoredArray
    from .story_preflight import observe
    catalog,rows=observe(capture_selected_values,scope.pid,(tuple(actor),),
        fields=('BP_CharacterSkinComponent','BlueprintCreatedComponents','InstanceComponents'),references=True)
    value=rows[actor[0]]
    if value.errors or value.truncated:raise RuntimeError('Character component membership is incomplete')
    candidates={}
    for key,item in value.values.items():
        name=key[1]
        if name=='BP_CharacterSkinComponent':items=() if item is None else (item,)
        elif name in ('BlueprintCreatedComponents','InstanceComponents'):
            if not isinstance(item,StoredArray) or item.length!=len(item.items):
                raise RuntimeError('Character component membership is incomplete')
            items=item.items
        else:continue
        for component in items:
            if component is None:continue
            if component.class_name not in ('BP_CharacterSkinComponent_C','BP_CinematicCharacterSkinComponent_C'):continue
            if ((component.outer_index,component.outer_serial)!=tuple(actor[:2]) or component.object_flags&0x30):
                raise RuntimeError('Current skin component belongs to another actor or lifetime')
            candidates[identity(component)]=component
    if len(candidates)!=1:raise RuntimeError('One current player skin component required')
    return next(iter(candidates.values()))

class DialogueFacialPerformance:
    def __init__(self,parent,actor,*,owned=False):
        self._scope=parent;self.scope=SessionScope(parent);self.actor=tuple(actor)
        self.closed=False;self.unknown=False;self.prepared=False;self.planners=[];self.calls={}
        self._warm_planners={}
        self.face=None;self.instance=None;self.component=None;self.old={};self.changed_class=False
        self.montage=None;self.deadline=None;self.last=None;self.journal=[]
        self.owned=owned
        self.preflight_ready=False;self.preflight_face=None;self.preflight_skin=None;self.preflight_values=None
        self._face_results=[]
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def _closed(self):return self.closed
    def _hold(self,obj):return acquire_stable(self.scope,obj)[0].object
    def _values(self,obj,names):
        from .story_preflight import observe
        reader=observe if getattr(self,'_preflighting',False) else lambda fn,*a,**kw:fn(*a,**kw)
        _,rows=reader(capture_selected_values,self.scope.pid,(identity(obj),),fields=names,references=True)
        values=rows[obj.index]
        if values.errors or values.truncated:raise RuntimeError('Facial performance observation incomplete')
        return {name:field(values,name) for name in names}
    def _retain_face_result(self,result):
        # The original getter's output is already retained atomically by the
        # invocation backend and adopted into this exact scope. Keep that owner
        # through restoration instead of acquiring/releasing a duplicate lease.
        results=getattr(self,'_face_results',None)
        if results is None:results=[];self._face_results=results
        results.append(result)
        if (result.active is not True or result._scope is None or result._scope() is not self.scope or
                result._session() is not self.scope._session or len(result._leases)!=1):
            raise RuntimeError('Face getter result ownership is incomplete')
        face=result.outputs['Face'];lease=result._leases[0]
        if (face is None or (face.outer_index,face.outer_serial)!=self.actor[:2] or
                lease.active is not True or lease._scope is None or lease._scope() is not self.scope or
                lease._session() is not self.scope._session or not lease._token or
                identity(lease.object)!=identity(face) or face.serial<=0):
            raise RuntimeError('Face component belongs to another actor or result owner')
        return face
    def _matching_skeletons(self,mesh,clip):
        from .story_preflight import observe
        reader=observe if getattr(self,'_preflighting',False) else lambda fn,*a,**kw:fn(*a,**kw)
        catalog,rows=reader(capture_selected_values,self.scope.pid,(identity(mesh),identity(clip)),fields=('Skeleton',),references=True)
        for obj in (mesh,clip):
            current=catalog.by_index[obj.index];value=rows[obj.index]
            if identity(current)!=identity(obj) or current.object_flags&0x30 or value.errors or value.truncated:
                raise RuntimeError('Facial skeleton observation incomplete')
        skeleton=field(rows[mesh.index],'Skeleton')
        return skeleton is not None and identity(skeleton)==identity(field(rows[clip.index],'Skeleton'))
    def _prepare_call(self,obj,path,**arguments):
        key=(identity(obj),path)
        if key in self.calls:
            previous=self.calls[key];planner=previous._planner()
            if planner is None:raise RuntimeError('Facial invocation planner no longer exists')
            planner._check()
            if planner._catalog is None:raise RuntimeError('Refresh the facial planner before preparing calls')
            objects=[value for value in arguments.values() if hasattr(value,'class_index')]
            missing=[value for value in objects if value.index not in planner._catalog.by_index or identity(planner._catalog.by_index[value.index])!=identity(value)]
            if missing:
                planner.adopt_observations(capture_selected(self.scope.pid,tuple(identity(value) for value in missing)))
            # Adding a montage for Montage_Stop refreshes this shared planner
            # and revokes sibling calls, including the next speaking montage.
            # Rebuild from the current catalog; never invoke the revoked plan.
            if missing or previous._generation!=planner._generation:
                target=planner._catalog.by_index[obj.index]
                if identity(target)!=identity(obj):raise RuntimeError('Facial target changed during planner refresh')
                prepare=planner.prepare_blueprint if path.startswith('/Game/') else planner.prepare_dialogue_slot if path.endswith(':PlaySlotAnimationAsDynamicMontage') else planner.prepare
                call=prepare(target,planner._catalog.find_path(path),**arguments)
                self.calls[key]=call
            else:call=previous.bind(**arguments)
            return call
        warm=getattr(self.scope._session,'_story_performance_preflight',None)
        if warm is not None and path in warm.paths:
            planners=getattr(self,'_warm_planners',None)
            if planners is None:planners=self._warm_planners={}
            current=planners.get(identity(obj))
            if current is not None and current[0] is warm:
                planner=current[1]
                # A title-warmed observation set already includes every
                # performance function. Share its planner for this exact
                # retained target generation, as cached calls already do.
                # New object arguments still need observed identities; native
                # invocation continues to revalidate target/arguments/schema.
                objects=[value for value in arguments.values() if hasattr(value,'class_index')]
                missing=[value for value in objects if value.index not in planner._catalog.by_index or
                         identity(planner._catalog.by_index[value.index])!=identity(value)]
                if missing:
                    from .story_preflight import observe
                    reader=observe if getattr(self,'_preflighting',False) else lambda fn,*a,**kw:fn(*a,**kw)
                    planner.adopt_observations(reader(capture_selected,self.scope.pid,
                        tuple(dict.fromkeys(identity(value) for value in missing))))
            else:
                planner=warm.planner(self.scope,obj,path,arguments,defer_reads=getattr(self,'_preflighting',False))
                self.planners.append(planner);planners[identity(obj)]=(warm,planner)
            c=planner._catalog
        else:
            names=(path.rsplit(':',1)[-1],)
            prepared=getattr(self.scope._session,'_story_construction_resources',None)
            c=prepared.catalog(self.scope,names) if prepared is not None and any(o.name==names[0] for o in prepared.metadata) else capture_matching(self.scope.pid,names=names)
            if path.endswith((':GetRelativeTransform',':AddComponentByClass')):
                c=c.with_observations(capture_matching(self.scope.pid,names=('Transform','Quat','Vector')))
            ids=[identity(obj)]+[identity(a) for a in arguments.values() if hasattr(a,'class_index')]
            c=c.with_observations(capture_selected(self.scope.pid,ids))
            function=c.find_path(path)
            c=c.with_observations(describe_selected(self.scope.pid,(identity(function),)).catalog)
            planner=self.scope.invocation_planner(catalog=c,selected_results=True)
            self.planners.append(planner)
        prepare=planner.prepare_blueprint if path.startswith('/Game/') else planner.prepare_dialogue_slot if path.endswith(':PlaySlotAnimationAsDynamicMontage') else planner.prepare
        call=prepare(c.by_index[obj.index],c.find_path(path),**arguments)
        self.calls[key]=call
        return call
    def _call(self,obj,path,**arguments):
        call=self._prepare_call(obj,path,**arguments)
        self.unknown=True
        try:result=call.invoke()
        except Exception as error:
            if getattr(error,'outcome',None)=='not_dispatched':self.unknown=False
            raise
        self.unknown=False
        return result
    def _void(self,obj,path,**arguments):
        with self._call(obj,path,**arguments):pass
    def _prepare_face_plans(self):
        # These calls bind the currently qualified component, but do not invoke
        # it. Actual activation still snapshots fresh state and checks the
        # skin/mesh/class/instance before any of these plans can be used.
        for path,arguments in (
                ('/Script/Engine.ActorComponent:IsComponentTickEnabled',{}),
                ('/Script/Engine.SkeletalMeshComponent:SetAnimClass',{'NewClass':self.human}),
                ('/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',{'bInDisablePostProcess':False}),
                ('/Script/Engine.ActorComponent:SetComponentTickEnabled',{'bEnabled':True})):
            self._prepare_call(self.preflight_face,path,**arguments)
    def preflight(self,*,revalidate=False):
        """Read/retain targets and assets, without changing any face state."""
        self._preflighting=True
        try:return self._preflight(revalidate=revalidate)
        finally:self._preflighting=False
    def _preflight(self,*,revalidate=False):
        if self.closed or self.unknown:raise RuntimeError('Facial owner unavailable')
        if getattr(self,'preflight_ready',False) and not revalidate:
            if not self.prepared:self._prepare_face_plans()
            return
        if revalidate and self.prepared:raise RuntimeError('Cannot revalidate active facial playback')
        self.scope._check()
        if getattr(self.scope._session._transport,'dialogue_slot_protocol',0)!=1:raise RuntimeError('Qualified facial animation-slot SDK hook required')
        from .story_preflight import observe
        skin=current_skin(self.scope,self.actor)
        # Retained components are not proof of a current cosmetic binding.
        # Rediscover the exact actor's skin, ask its original getter, and read
        # the face signature fresh. Reuse only immutable asset qualification.
        if getattr(self,'preflight_ready',False) and identity(skin)==identity(self.preflight_skin):
            with self._call(skin,SKIN+'GetFaceSkeletalMesh') as result:current=result.outputs['Face']
            if identity(current)==identity(self.preflight_face):
                values=self._values(current,('AnimClass','AnimationMode','SkeletalMesh','AnimScriptInstance'))
                if values['AnimationMode']==self.preflight_values['AnimationMode'] and all(
                        identity(values[name])==identity(self.preflight_values[name]) for name in ('AnimClass','SkeletalMesh','AnimScriptInstance')):
                    self._prepare_face_plans()
                    return
        self.preflight_ready=False
        resources=self.scope._session._story_construction_resources.resources
        self.human=resources.load(HUMAN,cls=True);self.clip=resources.load(MOUTH)
        self.preflight_skin=self._hold(skin)
        self.preflight_face=self._retain_face_result(self._call(skin,SKIN+'GetFaceSkeletalMesh'))
        observed=self._values(self.preflight_face,('AnimClass','AnimationMode','SkeletalMesh','AnimScriptInstance'))
        if observed['AnimationMode']!=0:raise RuntimeError('Facial component requires its original animation blueprint')
        instance=observed['AnimScriptInstance']
        owned_cine=False
        if getattr(self,'owned',False) and instance is not None and instance.class_name=='ABP_Facial_Cine_Noah_C':
            actor=observe(capture_selected,self.scope.pid,(self.actor,)).by_index[self.actor[0]]
            owned_cine=actor.class_name=='BP_Cine_Noah_C'
        if instance is None or (instance.class_name not in ('Face_AnimBP_Companion_C','Face_AnimBP_HumanNPC_C') and not owned_cine):
            raise RuntimeError('Unqualified player face animation class')
        mesh=observed['SkeletalMesh']
        if not self._matching_skeletons(mesh,self.clip):raise RuntimeError('Facial clip skeleton differs from player face')
        self.preflight_values=observed;self.preflight_ready=True
        self._prepare_face_plans()

    def prepare(self):
        if self.closed or self.unknown:raise RuntimeError('Facial owner unavailable')
        if self.prepared:return
        self.preflight()
        # Re-read the actual skin binding and snapshot restoration state only
        # at dialogue activation. Cosmetics/party changes after warmup cannot
        # silently target an old face or restore an earlier gameplay state.
        with self._call(self.preflight_skin,SKIN+'GetFaceSkeletalMesh') as result:
            if identity(result.outputs['Face'])!=identity(self.preflight_face):
                raise RuntimeError('Conversation face changed after preflight')
        observed=self._values(self.preflight_face,('AnimClass','bPauseAnims','bDisablePostProcessBlueprint','AnimationMode','SkeletalMesh','AnimScriptInstance'))
        for name in ('AnimClass','SkeletalMesh','AnimScriptInstance'):
            if identity(observed[name])!=identity(self.preflight_values[name]):
                raise RuntimeError('Conversation facial binding changed after preflight: '+name)
        if observed['AnimationMode']!=0:raise RuntimeError('Conversation face entered a different animation mode')
        self.face=self.preflight_face;self.old=observed
        self.old['AnimClass']=self._hold(self.old['AnimClass'])
        instance=self.old['AnimScriptInstance']
        owned_cine=bool(self.owned and instance.class_name=='ABP_Facial_Cine_Noah_C')
        with self._call(self.face,'/Script/Engine.ActorComponent:IsComponentTickEnabled') as result:self.old['tick']=result.return_value
        if type(self.old['tick']) is not bool:raise RuntimeError('Face tick state unavailable')
        # Record state before changing anything; the original component API
        # forwards its expression/talking settings into the facial AnimInstance.
        if instance.class_name=='Face_AnimBP_Companion_C' or owned_cine:
            self._void(self.face,'/Script/Engine.SkeletalMeshComponent:SetAnimClass',NewClass=self.human)
            self.changed_class=True
        self.instance=self._hold(self._values(self.face,('AnimScriptInstance',))['AnimScriptInstance'])
        if self.instance.class_name!='Face_AnimBP_HumanNPC_C':raise RuntimeError('Original human facial class did not initialize')
        if owned_cine:self._void(self.instance,FACE+'BlueprintBeginPlay')
        self._void(self.instance,FACE+'SetPostProcessAnimation')
        state=self._values(self.instance,('AnimationComponentReference','ExpressionsBlendTime'))
        self.old['blend']=state['ExpressionsBlendTime'];self.component=state['AnimationComponentReference']
        if self.component is None and (owned_cine or self.changed_class):
            self.component=self._bind_owned_component()
        if self.component is None or (self.component.outer_index,self.component.outer_serial)!=self.actor[:2]:raise RuntimeError('Face animation component belongs to another player')
        self.component=self._hold(self.component)
        self.component_old=self._values(self.component,('FacialExpression','FacialExpressionStrength','EyesLook','IsTalking','IsInDialogue','EnvelopeVolume'))
        self._set_scalar(self.face,'bPauseAnims',False)
        self._void(self.face,'/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',bInDisablePostProcess=False)
        self._void(self.face,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=True)
        self.prepared=True
    def _set_scalar(self,obj,name,value):
        old=self._values(obj,(name,))[name]
        if old==value:return
        self.unknown=True
        try:self.scope.assign_scalar(obj,name,value,expected=old,allow_mutation=True)
        except ValueError:
            # Scalar assignment reports validation errors before dispatch;
            # acknowledgement/decode failures are InvocationError instead.
            self.unknown=False
            raise
        except Exception as error:
            if getattr(error,'outcome',None)=='not_dispatched':self.unknown=False
            raise
        self.unknown=False
    def _stop_mouth(self):
        if self.montage is None:return
        self._void(self.instance,'/Script/Engine.AnimInstance:Montage_Stop',InBlendOutTime=.15,Montage=self.montage)
        self.montage=None
    def _bind_owned_component(self):
        # Some cinematic Gustave instances have no NPC animation component.
        # A current-world borrowed Gustave companion also lacks this component.
        # Its temporary component is tracked and destroyed after face restore.
        c=capture_matching(self.scope.pid,classes=('BP_NPCAnimationComponent_C',))
        matches=[o for o in c.objects if o.class_name=='BP_NPCAnimationComponent_C' and
                 (o.outer_index,o.outer_serial)==self.actor[:2] and not o.object_flags&0x40000030]
        if len(matches)>1:raise RuntimeError('Ambiguous owned cinematic facial state components')
        if matches:component=self._hold(matches[0])
        else:
            catalog=capture_selected(self.scope.pid,(self.actor,));actor=catalog.by_index[self.actor[0]]
            companion=actor.class_name=='BP_Pawn_AICompanion_Noah_C'
            if companion:
                token=getattr(self.scope,'_world_binding_token',None)
                worlds=[o for o in catalog.outer_chain(actor) if o.class_name=='World']
                companion=bool(token and len(worlds)==1 and
                    token[0]==(self.scope.pid,worlds[0].index,worlds[0].serial,worlds[0].address))
            if not ((self.owned and actor.class_name=='BP_Cine_Noah_C') or companion):
                raise RuntimeError('A disposable cinematic Gustave is required for facial component construction')
            cls=self.scope._session._story_construction_resources.resources.load(NPC[:-1],cls=True)
            with self._call(self.face,'/Script/Engine.SceneComponent:GetRelativeTransform') as result:relative=result.return_value
            with self._call(actor,'/Script/Engine.Actor:AddComponentByClass',Class=cls,
                    bManualAttachment=False,RelativeTransform=relative,bDeferredFinish=False) as result:
                if result.return_value is None:raise RuntimeError('Owned cinematic facial component construction failed')
                component=self._hold(result.return_value)
                self.created_component=component
            if (component.outer_index,component.outer_serial)!=self.actor[:2]:
                raise RuntimeError('Constructed facial component belongs to another actor')
        c=capture_selected(self.scope.pid,(identity(self.instance),identity(component)))
        owner=c.by_index[self.instance.class_index]
        c=c.with_observations(describe_selected(self.scope.pid,(identity(owner),)).catalog)
        current=self._values(self.instance,('AnimationComponentReference',))['AnimationComponentReference']
        if current is None:
            self.scope.assign_object(self.instance,c.by_index[self.instance.class_index],
                'AnimationComponentReference',component,expected=None,allow_mutation=True,catalog=c)
        elif identity(current)!=identity(component):raise RuntimeError('Face bound to another animation component')
        return component
    def _apply(self,expression,talking):
        self._stop_mouth()
        self._set_scalar(self.instance,'ExpressionsBlendTime',.35)
        self._void(self.component,NPC+'SetFacialExpression',FacialExpression=expression,FacialExpressionStrength=.65,EyesLook=0)
        self._void(self.component,NPC+'SetIsTalking',IsTalking=talking)
        self._void(self.component,NPC+'SetIsInDialogue',IsInDialogue=True)
        self._void(self.component,NPC+'UpdateEnvelopeVolume',SoundWaveVolume=.12 if talking else 0.)
        if getattr(self,'owned',False):
            # A disposable cinematic rig can be offscreen during staging. Run
            # its original update event once so copied expression/talking data
            # is current before the first conversation camera renders it.
            self._void(self.instance,FACE+'BlueprintUpdateAnimation',DeltaTimeX=1./60.)
        if talking:
            with self._call(self.instance,'/Script/Engine.AnimInstance:PlaySlotAnimationAsDynamicMontage',Asset=self.clip,SlotNodeName='Mouth',BlendInTime=.35,BlendOutTime=.35,InPlayRate=1.,LoopCount=10000,BlendOutTriggerTime=-1.,InTimeToStartMontageAt=0.) as result:
                if result.return_value is None:raise RuntimeError('Original mouth montage did not start')
                self.montage=self._hold(result.return_value)
        self.last=(expression,talking);self.deadline=time.monotonic()+2.5 if talking else None
    def play(self,row):
        if type(row.get('expression')) is not int or not 0<=row['expression']<32 or type(row.get('talking')) is not bool or row.get('in_dialogue') is not True:raise ValueError('Reviewed source facial performance required')
        self.prepare();self._apply(row['expression'],row['talking'])
        if row.get('loops')==1:self.deadline=time.monotonic()+2.5
    def poll(self):
        if self.deadline is not None and time.monotonic()>=self.deadline:self._apply(0,False)
    def snapshot(self):
        return self._values(self.instance,('Expression_1','ExpressionStrength','IsTalking','Is in Dialogue','EnvelopeVolume','EnvelopeVolumex3','ExpressionsBlendTime'))
    def close(self,*,world_retired=False):
        if self.closed:return True
        if self.unknown:return False
        if not world_retired and self.prepared:
            self._stop_mouth()
            old=self.component_old
            if old is not None:
                self._void(self.component,NPC+'SetFacialExpression',FacialExpression=old['FacialExpression'],FacialExpressionStrength=old['FacialExpressionStrength'],EyesLook=old['EyesLook'])
                self._void(self.component,NPC+'SetIsTalking',IsTalking=old['IsTalking'])
                self._void(self.component,NPC+'SetIsInDialogue',IsInDialogue=old['IsInDialogue'])
                self._void(self.component,NPC+'UpdateEnvelopeVolume',SoundWaveVolume=old['EnvelopeVolume'])
            self._set_scalar(self.instance,'ExpressionsBlendTime',self.old['blend'])
        if not world_retired and self.face is not None and self.old:
            if self.changed_class:self._void(self.face,'/Script/Engine.SkeletalMeshComponent:SetAnimClass',NewClass=self.old['AnimClass'])
            self._set_scalar(self.face,'bPauseAnims',self.old['bPauseAnims'])
            self._void(self.face,'/Script/Engine.SkeletalMeshComponent:SetDisablePostProcessBlueprint',bInDisablePostProcess=self.old['bDisablePostProcessBlueprint'])
            if 'tick' in self.old:self._void(self.face,'/Script/Engine.ActorComponent:SetComponentTickEnabled',bEnabled=self.old['tick'])
        if not world_retired and getattr(self,'created_component',None) is not None:
            actor=capture_selected(self.scope.pid,(self.actor,)).by_index[self.actor[0]]
            self._void(self.created_component,'/Script/Engine.ActorComponent:K2_DestroyComponent',Object=actor)
            self.created_component=None
        for planner in self.planners:planner.close()
        from ._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope):return False
        # The scope has acknowledged release of all output tokens. Dropping the
        # handles now cannot issue a second release or lose deferred ownership.
        self._face_results=[]
        self.closed=True;return True
