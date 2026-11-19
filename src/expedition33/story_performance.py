"""Conversation body gestures through original animation blueprint slots.

Only the montage returned to this owner is stopped. Animation mode, animation
blueprint and unrelated game montages are never replaced or stopped.
"""
import time
from .story_animation import DialogueAnimations
from .story_dialogue import identity,field

BASE='/Game/Animations/AnimNPC/RD_Idles/Gustave/A_RD_Base_Idle_Gustave.A_RD_Base_Idle_Gustave'

class DialogueBodyPerformance:
    def __init__(self,parent,actor,*,player=True):
        self._scope=parent;self.actor=tuple(actor);self.media=DialogueAnimations(parent)
        self.scope=self.media.scope;self.instance=None;self.current=None;self.montage=None
        self.deadline=None;self.closed=False;self.unknown=False
        self.player=player;self.single_node=False
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def _closed(self):return self.closed
    def _invoke(self,name,**arguments):
        call=self.media._prepare_call(self.instance,'AnimInstance',name,**arguments)
        return call.invoke()
    def preflight(self,path,loops):
        if self.current is not None or self.montage is not None:
            raise RuntimeError('Read-only preflight cannot replace active body playback')
        self.media.preflight_reads=True
        try:return self.prepare(path,loops)
        finally:self.media.preflight_reads=False
    def preflight_many(self,selections,*,body_observation=None):
        """Prepare every gesture using a single fresh body/clip read batch."""
        if self.closed or self.unknown:raise RuntimeError('Performance owner unavailable')
        if self.current is not None or self.montage is not None:
            raise RuntimeError('Read-only preflight cannot replace active body playback')
        pairs=tuple(dict.fromkeys(selections))
        if not pairs or len(pairs)>32:raise ValueError('One to 32 body performances required')
        if any(type(loops) is not int or loops not in (1,10000) for _,loops in pairs):
            raise ValueError('Reviewed body loop count required')
        self.media.preflight_reads=True
        try:
            options={'body_observation':body_observation} if body_observation is not None else {}
            body,state,clips=self.media.prepare_many(self.actor,
                tuple(dict(asset=path) for path,_ in pairs),player=self.player,**options)
            by_path=dict(zip(dict.fromkeys(path for path,_ in pairs),clips))
            observed=self._body_call_observation(state,tuple(row[1] for row in clips))
            for path,loops in pairs:self._prepare_observed(body,by_path[path][1],state,loops,observed=observed)
        finally:self.media.preflight_reads=False
    def _body_call_observation(self,state,clips):
        if field(state,'AnimationMode')!=0:return None
        from ._stable_lease import acquire_stable
        from .catalog import capture_selected
        from .story_preflight import observe
        instance=field(state,'AnimScriptInstance')
        if instance is None:raise RuntimeError('Conversation body animation instance unavailable')
        selectors=tuple(dict.fromkeys(identity(clip) for clip in clips))
        if self.instance is None:
            held,catalog=acquire_stable(self.scope,instance,selectors=selectors)
            self.instance=held.object
            return catalog
        if identity(instance)!=identity(self.instance):raise RuntimeError('Conversation body animation instance changed')
        return observe(capture_selected,self.scope.pid,(identity(instance),)+selectors)
    def prepare(self,path,loops):
        if self.closed or self.unknown:raise RuntimeError('Performance owner unavailable')
        if type(loops) is not int or loops not in (1,10000):raise ValueError('Reviewed body loop count required')
        from .values import capture_selected_values
        selection=dict(asset=path,target='player',loop=loops!=1,speed=1.)
        body,clip,_=self.media.prepare(self.actor,selection,player=self.player)
        from .story_preflight import observe
        reader=observe if getattr(self.media,'preflight_reads',False) else lambda fn,*a,**kw:fn(*a,**kw)
        c,v=reader(capture_selected_values,self.scope.pid,(identity(body),),fields=('AnimationMode','AnimScriptInstance','SkeletalMesh'),references=True)
        return self._prepare_observed(body,clip,v[body.index],loops)
    def _prepare_observed(self,body,clip,state,loops,*,observed=None):
        from ._stable_lease import acquire_stable
        self.preflight_signature=(identity(body),identity(field(state,'SkeletalMesh')),
            identity(field(state,'AnimScriptInstance')),field(state,'AnimationMode'))
        if field(state,'AnimationMode')!=0:
            if self.player:raise RuntimeError('Conversation body requires its original animation blueprint')
            self.single_node=True
            return None
        instance=field(state,'AnimScriptInstance')
        if instance is None:raise RuntimeError('Conversation body animation instance unavailable')
        if self.instance is None:self.instance=acquire_stable(self.scope,instance)[0].object
        elif (self.instance.index,self.instance.address)!=(instance.index,instance.address) or instance.serial>0 and self.instance.serial!=instance.serial:
            raise RuntimeError('Conversation body animation instance changed')
        self.preflight_signature=(identity(body),identity(field(state,'SkeletalMesh')),identity(self.instance),field(state,'AnimationMode'))
        arguments=dict(Asset=clip,SlotNodeName='DefaultSlot',BlendInTime=.4,BlendOutTime=.4,InPlayRate=1.,LoopCount=loops,BlendOutTriggerTime=-1.,InTimeToStartMontageAt=0.)
        self.media._prepare_call(self.instance,'AnimInstance','PlaySlotAnimationAsDynamicMontage',_observed=observed,**arguments)
        return arguments
    def matches_current(self):
        """Validate a warmed body after a party/cosmetic change; no playback."""
        from .story_animation import body
        from .values import capture_selected_values
        from .story_preflight import observe
        obj=body(self.scope,self.actor,defer_reads=True)
        _,values=observe(capture_selected_values,self.scope.pid,(identity(obj),),fields=('SkeletalMesh','AnimScriptInstance','AnimationMode'),references=True)
        value=values[obj.index]
        current=(identity(obj),identity(field(value,'SkeletalMesh')),identity(field(value,'AnimScriptInstance')),field(value,'AnimationMode'))
        return current==getattr(self,'preflight_signature',None)
    def play(self,path,loops):
        arguments=self.prepare(path,loops)
        if arguments is None:
            self.media.play(self.actor,dict(asset=path,target='player',loop=loops!=1,speed=1.),player=False)
            self.current=path;self.deadline=time.monotonic()+2.5 if loops==1 else None
            return
        if loops==10000 and self.current==path and self.montage is not None:
            with self._invoke('Montage_IsPlaying',Montage=self.montage) as result:
                if result.return_value is True:self.deadline=None;return
        self._stop()
        self.unknown=True
        from ._stable_lease import acquire_stable
        with self._invoke('PlaySlotAnimationAsDynamicMontage',**arguments) as result:
            montage=result.return_value
            if montage is None:raise RuntimeError('Dialogue slot montage returned no playback; owner retained')
            self.montage=acquire_stable(self.scope,montage)[0].object
        self.unknown=False;self.current=path
        self.deadline=time.monotonic()+2.5 if loops==1 else None
    def poll(self):
        if self.deadline is not None and time.monotonic()>=self.deadline:
            self.play(BASE,10000)
    def _stop(self):
        if self.montage is None:return
        self.unknown=True
        with self._invoke('Montage_Stop',InBlendOutTime=.4,Montage=self.montage):pass
        self.unknown=False;self.montage=None;self.current=None;self.deadline=None
    def close(self,*,world_retired=False):
        if self.closed:return True
        if self.unknown:return False
        if self.single_node:
            if not self.media.close(world_retired=world_retired):return False
            self.closed=True;return True
        if not world_retired:self._stop()
        for planner in dict.fromkeys(planner for planner,call in self.media.calls.values()):planner.close()
        self.media.calls={};self.media._warm_planners={};self.media.records={}
        from ._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope):return False
        self.closed=True;return True
