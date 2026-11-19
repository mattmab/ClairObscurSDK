"""Skeleton-checked dialogue clips using original skeletal components.

No meshes or animation blueprints are replaced. Player animation mode/rate are
restored when dialogue ends; world retirement releases leases without calls.
"""
import json
from functools import lru_cache
from pathlib import Path
from .story_dialogue import identity,field

@lru_cache(maxsize=1)
def library():
    return json.loads(Path(__file__).with_name('story-animation-library.json').read_text(encoding='utf-8'))

def choices(profile,query=''):
    skeleton=library()['profiles'].get(profile)
    words=query.casefold().split()
    return tuple(sorted((r for r in library()['clips'] if r['skeleton']==skeleton and
        all(w in (r['label']+' '+r['path']).casefold() for w in words)),key=lambda r:(r['label'].casefold(),r['path'])))

def body(scope,actor,*,defer_reads=False):
    from .values import capture_selected_values
    from .story_preflight import observe
    reader=observe if defer_reads else lambda fn,*a,**kw:fn(*a,**kw)
    c,v=reader(capture_selected_values,scope.pid,(actor,),fields=('Body','Mesh'),references=True)
    return body_from_observation(c,actor,v[actor[0]])


def body_from_observation(c,actor,value):
    """Select an actor-owned body from a fresh caller-supplied read batch."""
    for name in ('Body','Mesh'):
        keys=[k for k in value.values if k[1]==name and k not in value.errors]
        if len(keys)==1:
            obj=value.values[keys[0]]
            if obj is not None and any(c.classes[i].name=='SkeletalMeshComponent' for i in c.ancestors(obj.class_index)):
                if obj.outer_index!=actor[0] or obj.outer_serial!=actor[1]:raise ValueError('Dialogue body is not owned by its actor')
                return obj
    raise ValueError('This character has no supported body animation component')


class BodyPreflightObservation:
    """One-use body read shared inside an uninterrupted preparation operation."""
    def __init__(self,scope,actor,component,state):
        from ._reader import active_reader
        self.scope=scope;self.session=scope._session;self.actor=tuple(actor)
        self.component=component;self.state=state;self.used=False
        self.reader=active_reader();self.token=getattr(self.reader,'_token',None)
        transport=self.session._transport
        self.sequence=getattr(transport,'_native_command_sequence',None) if getattr(transport,'command_wait_protocol',0)==1 else None
        if ((component.outer_index,component.outer_serial)!=self.actor[:2] or component.object_flags&0x30
                or state.errors or state.truncated):raise ValueError('Incomplete actor-owned body observation')
        # Require the complete preflight shape now; a role-only mesh read is
        # insufficient. No restoration values are captured by this handoff.
        for name in ('SkeletalMesh','AnimationMode','GlobalAnimRateScale','AnimScriptInstance'):field(state,name)

    def consume(self,scope,actor):
        from ._reader import active_reader
        if self.used:return None
        self.used=True
        scope._check();self.scope._check()
        if (scope._session is not self.session or tuple(actor)!=self.actor or self.reader is None or self.token is None
                or active_reader() is not self.reader or getattr(self.reader,'_token',None) is not self.token
                or type(self.sequence) is not int or self.sequence!=getattr(self.session._transport,'_native_command_sequence',None)):
            return None
        return self.component,self.state

class DialogueAnimations:
    def __init__(self,scope):
        from ._scope import SessionScope
        self.scope=SessionScope(scope);self.records={};self.failed=False;self.prepared={};self.calls={};self.mutated=set();self.preflight_reads=False

    def _prepare_call(self,obj,owner,name,*,_observed=None,**args):
        key=(identity(obj),owner,name,repr(args))
        calls=getattr(self,'calls',None)
        if calls is None:calls=self.calls={}
        if key in calls:return calls[key][1]
        path='/Script/Engine.'+owner+':'+name
        warm=getattr(self.scope._session,'_story_performance_preflight',None)
        if warm is not None and path in warm.paths:
            # Each argument set keeps its own planner generation. Adopting a
            # later clip into a shared planner would revoke earlier gestures.
            if _observed is None:
                planner=warm.planner(self.scope,obj,path,args,defer_reads=getattr(self,'preflight_reads',False))
            else:
                if self.scope._session is not warm.session or _observed.pid!=self.scope.pid:
                    raise RuntimeError('Body preparation observations belong to another session')
                objects=(obj,)+tuple(value for value in args.values() if hasattr(value,'class_index'))
                for value in objects:
                    current=_observed.by_index[value.index]
                    if identity(current)!=identity(value) or current.object_flags&0x30:
                        raise RuntimeError('Body preparation target or clip changed')
                planner=self.scope.invocation_planner(observations=warm.observations,selected_results=True)
                try:planner.adopt_observations(_observed)
                except BaseException:planner.close();raise
            try:
                c=planner._catalog
                prepare=planner.prepare_dialogue_slot if name=='PlaySlotAnimationAsDynamicMontage' and owner=='AnimInstance' else planner.prepare
                call=prepare(c.by_index[obj.index],c.find_path(path),**args)
            except BaseException:planner.close();raise
            calls[key]=(planner,call)
            return call
        from .catalog import capture_matching,capture_selected
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        c=construction.catalog(self.scope,(name,owner,'EAnimationMode')) if construction is not None and any(o.name==name for o in construction.metadata) else capture_matching(self.scope.pid,names=(name,owner,'EAnimationMode'))
        objects=tuple(dict.fromkeys((identity(obj),)+tuple(identity(value) for value in args.values() if hasattr(value,'class_index'))))
        c=c.with_observations(_observed if _observed is not None else capture_selected(self.scope.pid,objects))
        from .reflection import describe_selected
        function=c.find_path('/Script/Engine.'+owner+':'+name)
        c=describe_selected(self.scope.pid,(identity(function),)).catalog.with_observations(c)
        planner=self.scope.invocation_planner(catalog=c,selected_results=True)
        try:
            prepare=planner.prepare_dialogue_slot if name=='PlaySlotAnimationAsDynamicMontage' and owner=='AnimInstance' else planner.prepare
            call=prepare(c.by_index[obj.index],c.find_path('/Script/Engine.'+owner+':'+name),**args)
        except BaseException:
            planner.close();raise
        calls[key]=(planner,call)
        return call

    def _call(self,obj,owner,name,*,_track=None,**args):
        call=self._prepare_call(obj,owner,name,**args)
        if _track is not None:self.mutated.add(_track)
        self.failed=True
        with call.invoke() as result:
            if result.outcome!='dispatch_returned':raise RuntimeError('Media dispatch did not complete')
        self.failed=False

    def prepare_playback(self,actor,selection,*,player=False):
        obj,clip,duration=self.prepare(actor,selection,player=player)
        self._prepare_call(obj,'SkeletalMeshComponent','PlayAnimation',NewAnimToPlay=clip,bLooping=selection['loop'])
        self._prepare_call(obj,'SkeletalMeshComponent','SetPlayRate',Rate=selection['speed'])
        return duration

    def prepare_many(self,actor,selections,*,player=False,body_observation=None):
        """Qualify a bounded clip set against one freshly observed body.

        This is preparation only. No actor/mesh/mode observation is shared
        between calls or owners; subsequent playback keeps its own validation.
        """
        if self.failed:raise RuntimeError('Animation dispatch stopped; close the conversation before retrying')
        self.scope._check()
        paths=tuple(dict.fromkeys(row['asset'] for row in selections))
        if not paths or len(paths)>32:raise ValueError('One to 32 body clips required')
        from .values import capture_selected_values
        from .assets import load_asset
        from ._stable_lease import acquire_stable
        from .story_preflight import observe
        reader=observe if getattr(self,'preflight_reads',False) else lambda fn,*a,**kw:fn(*a,**kw)
        if body_observation is not None and not isinstance(body_observation,BodyPreflightObservation):
            raise TypeError('Owned one-use body observation required')
        observed=body_observation.consume(self.scope,actor) if body_observation is not None else None
        if observed is None:
            obj=body(self.scope,actor,defer_reads=getattr(self,'preflight_reads',False));key=identity(obj)
            _,values=reader(capture_selected_values,self.scope.pid,(key,),
                fields=('SkeletalMesh','AnimationMode','GlobalAnimRateScale','AnimScriptInstance'),references=True)
            state=values[obj.index]
        else:obj,state=observed;key=identity(obj)
        if state.errors or getattr(state,'truncated',()):raise ValueError('Body performance observation incomplete')
        mesh=field(state,'SkeletalMesh');mode=field(state,'AnimationMode');rate=field(state,'GlobalAnimRateScale')
        if mesh is None:raise ValueError('Character body mesh is unavailable')
        if player and mode!=0:raise ValueError('Player is already using a special animation; finish it before testing this response')
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        clips={path:(construction.resources.load(path) if construction is not None else load_asset(self.scope,path).return_value)
               for path in paths}
        if any(clip is None or clip.class_name!='AnimSequence' for clip in clips.values()):
            raise ValueError('Select an animation sequence')
        objects=tuple(dict.fromkeys((identity(mesh),)+tuple(identity(clip) for clip in clips.values())))
        _,assets=reader(capture_selected_values,self.scope.pid,objects,fields=('Skeleton','SequenceLength'),references=True)
        if any(row.errors or getattr(row,'truncated',()) for row in assets.values()):
            raise ValueError('Body clip observation incomplete')
        skeleton=field(assets[mesh.index],'Skeleton');qualified={}
        for path,clip in clips.items():
            value=assets[clip.index];duration=field(value,'SequenceLength')
            if type(duration) not in (int,float) or not 0<duration<=3600:raise ValueError('Animation duration is invalid')
            if skeleton is None or identity(skeleton)!=identity(field(value,'Skeleton')):
                raise ValueError('Animation and character skeletons differ')
            qualified[(tuple(actor),path,player)]=(obj,clip,duration)
        # Publish only after every clip passed. Failed reads retain earlier
        # prepared plans but never qualify a partial/new body set.
        if key not in self.records:
            held,_=acquire_stable(self.scope,obj);self.records[key]=(held,mode,rate)
        self.prepared.update(qualified)
        return obj,state,tuple(qualified[(tuple(actor),path,player)] for path in paths)

    def prepare(self,actor,selection,*,player=False):
        if self.failed:raise RuntimeError('Animation dispatch stopped; close the conversation before retrying')
        cache=getattr(self,'prepared',None)
        if cache is None:cache=self.prepared={}
        cache_key=(tuple(actor),selection['asset'],player)
        if cache_key in cache:return cache[cache_key]
        from .values import capture_selected_values
        from .assets import load_asset
        from ._stable_lease import acquire_stable
        from .story_preflight import observe
        defer=getattr(self,'preflight_reads',False)
        reader=observe if defer else lambda fn,*a,**kw:fn(*a,**kw)
        obj=body(self.scope,actor,defer_reads=True) if defer else body(self.scope,actor);key=identity(obj)
        c,v=reader(capture_selected_values,self.scope.pid,(key,),fields=('SkeletalMesh','AnimationMode','GlobalAnimRateScale'),references=True)
        mesh=field(v[obj.index],'SkeletalMesh')
        if mesh is None:raise ValueError('Character body mesh is unavailable')
        c,m=reader(capture_selected_values,self.scope.pid,(identity(mesh),),fields=('Skeleton',),references=True)
        skeleton=field(m[mesh.index],'Skeleton')
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        clip=construction.resources.load(selection['asset']) if construction is not None else load_asset(self.scope,selection['asset']).return_value
        if clip is None or clip.class_name!='AnimSequence':raise ValueError('Select an animation sequence')
        cc,a=reader(capture_selected_values,self.scope.pid,(identity(clip),),fields=('Skeleton','SequenceLength'),references=True)
        duration=field(a[clip.index],'SequenceLength')
        if type(duration) not in (int,float) or not 0<duration<=3600:raise ValueError('Animation duration is invalid')
        if skeleton is None or identity(skeleton)!=identity(field(a[clip.index],'Skeleton')):raise ValueError('Animation and character skeletons differ')
        if key not in self.records:
            mode=field(v[obj.index],'AnimationMode');rate=field(v[obj.index],'GlobalAnimRateScale')
            if player and mode!=0:raise ValueError('Player is already using a special animation; finish it before testing this response')
            held,_=acquire_stable(self.scope,obj)
            self.records[key]=(held,mode,rate)
        cache[cache_key]=(obj,clip,duration)
        return cache[cache_key]

    def play(self,actor,selection,*,player=False):
        obj,clip,duration=self.prepare(actor,selection,player=player)
        self._call(obj,'SkeletalMeshComponent','PlayAnimation',_track=identity(obj),NewAnimToPlay=clip,bLooping=selection['loop'])
        self._call(obj,'SkeletalMeshComponent','SetPlayRate',Rate=selection['speed'])
        self.failed=False
        return duration/selection['speed']

    def close(self,*,world_retired=False):
        if not world_retired:
            if self.failed:return False
            for key,(held,mode,rate) in list(self.records.items()):
                if key not in getattr(self,'mutated',self.records):continue
                self._call(held.object,'SkeletalMeshComponent','Stop')
                self._call(held.object,'SkeletalMeshComponent','SetAnimationMode',InAnimationMode=mode,bForceInitAnimScriptInstance=True)
                self.failed=False;del self.records[key]
        for planner in dict.fromkeys(planner for planner,call in getattr(self,'calls',{}).values()):planner.close()
        self.calls={};self._warm_planners={}
        from ._retired_tracking import close_lease_only_scope
        return close_lease_only_scope(self.scope)
