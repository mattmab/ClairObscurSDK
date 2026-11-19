"""An SDK-owned original streaming-source actor; never moves a game actor."""
from ._scope import SessionScope
from .cinematics.blueprint_actor import BlueprintActor
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references

COMPLETION_FUNCTION='/Script/SandFall.SandfallBlueprintHelpers:BlockTillLevelStreamingCompleted'
COMPLETION_CDO='/Script/SandFall.Default__SandfallBlueprintHelpers'


class StoryStreamingCompletion:
    """One original blocking completion request during an exact native hold.

    The engine updates and flushes streaming here; it provides no time bound.
    Returning is not a landing-readiness receipt. Callers must still check their
    sources, floor, rendered geometry and cast before releasing the hold.
    """
    def __init__(self,parent,ctx,gate):
        self._scope=parent;self.scope=SessionScope(parent);self.ctx=dict(ctx)
        self.gate=gate;self.token=self.scope._world_binding_token
        self.state='new';self.planner=None;self.call=None;self.closed=False
        self.sequence=None;self.gate_owner=gate.owner
        parent._register_native_owner(self);parent._close_before_descendants(self)

    @property
    def _closed(self):return self.closed

    def _held(self):
        from .map_runtime import context
        self.scope._check()
        capability=getattr(self.scope._session._transport,'loading_dispatch_reentrancy_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Blocking streaming requires reentrant-dispatch protection')
        if (self.gate.session is not self.scope._session or self.gate.closed or
                self.gate.owner!=self.gate_owner or self.token is None or
                self._scope._world_binding_token!=self.token or self.scope._world_binding_token!=self.token):
            raise RuntimeError('Blocking streaming owner or world admission changed')
        if context(self.scope,require_bound_world=True)!=self.ctx:
            raise RuntimeError('Blocking streaming possession changed')
        held=self.gate.status()
        sequence=held.get('hold_sequence')
        if (held['state']!=2 or tuple(held['world'])!=tuple(self.ctx['visit']) or
                tuple(held['pawn'])!=tuple(self.ctx['pawn']) or type(sequence) is not int or sequence<=0 or
                (self.sequence is not None and sequence!=self.sequence)):
            raise RuntimeError('Blocking streaming requires the same active native hold')
        return sequence

    def _sources(self,sources):
        if not 1<=len(sources)<=32 or len({id(source) for source in sources})!=len(sources):
            raise RuntimeError('Distinct configured streaming sources required')
        for source in sources:
            if (source.scope._session is not self.scope._session or source.closed or source.unknown or
                    source.scope._world_binding_token!=self.token or source.actor.state!='prepared' or
                    source.query is None or source.planner is None):
                raise RuntimeError('Streaming source configuration is not acknowledged in this world')

    def complete(self,sources):
        if self.closed or self.state=='unknown':
            raise RuntimeError('Blocking streaming outcome unavailable; not replayed')
        if self.state=='complete':return True
        sources=tuple(sources);self._sources(sources)
        if self.state=='new':
            self.sequence=self._held()
            construction=getattr(self.scope._session,'_story_construction_resources',None)
            if construction is None:raise RuntimeError('Blocking streaming metadata must be prepared at title')
            c=capture_selected(self.scope.pid,(tuple(self.ctx['visit']),))
            c=c.with_observations(construction.catalog(self.scope,
                ('BlockTillLevelStreamingCompleted','Default__SandfallBlueprintHelpers')))
            self.planner=construction.movement_planner(self.scope,c)
            self.call=self.planner.prepare(c.find_path(COMPLETION_CDO),c.find_path(COMPLETION_FUNCTION),
                WorldContextObject=c.by_index[self.ctx['visit'][0]])
            self.state='prepared'
        # No registry scan or metadata preparation is permitted after this fresh
        # possession/hold observation and before the original function request.
        self._sources(sources);self._held()
        key=(self.gate_owner,self.sequence,tuple(self.ctx['visit']),tuple(self.ctx['pawn']))
        journal=getattr(self.gate,'_story_streaming_completions',None)
        if journal is None:self.gate._story_streaming_completions=journal={}
        if key in journal:raise RuntimeError('Streaming completion already requested for this hold; not replayed')
        journal[key]=self;self.state='unknown'
        with self.call.invoke() as result:
            if result.outcome!='dispatch_returned':
                raise RuntimeError('Blocking streaming dispatch did not return; not replayed')
        # Any exception, lost ACK or changed hold retains the attempted owner;
        # the original function is never repeated by a later preparation tick.
        self._held();self.state='complete'
        return True

    def close(self):
        if self.closed:return True
        if self.state=='unknown':return False
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();self.closed=True
        return True

def prepare_metadata(session):
    cached=getattr(session,'_story_streaming_metadata',None)
    if cached is not None:return cached
    from ._metadata_stabilization import process_preparation
    c=capture_matching(session.pid,names=('EnableStreamingSource','IsStreamingCompleted'))
    objects=tuple(c.find_path('/Script/Engine.WorldPartitionStreamingSourceComponent:'+name)
                  for name in ('EnableStreamingSource','IsStreamingCompleted'))
    stable=process_preparation(session).prepare(c,objects)
    cached=tuple(stable.by_index[o.index] for o in objects)
    session._story_streaming_metadata=cached
    return cached

class StoryStreamingSource:
    def __init__(self,parent):
        self._scope=parent;self.scope=SessionScope(parent);self.actor=BlueprintActor(self.scope)
        self.closed=False;self.unknown=False;self.planner=None;self.query=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def _closed(self):return self.closed
    def prepare(self,position,*,radius=None):
        if self.planner is not None or self.actor.state!='new':raise RuntimeError('Streaming construction is one-shot')
        self._check_radius(radius)
        self.actor.prepare_streaming_source((0.,0.,0.,1.,*position,0.,1.,1.,1.,0.))
        self.configure(radius=radius)
    def _check_radius(self,radius):
        if radius is None:return
        from ._story_streaming_radius import checked_radius
        checked_radius(radius)
        capability=getattr(self.scope._session._transport,'story_streaming_radius_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Owned streaming source radius runtime required')
    def configure(self,*,radius=None):
        """Finish observations for an already spawned source, without respawn."""
        if self.actor.state!='prepared' or self.planner is not None or self.unknown:raise RuntimeError('Prepared, undispatched streaming source required')
        self._check_radius(radius)
        c=capture_selected(self.scope.pid,(self.actor.identity,))
        obj=c.by_index[self.actor.identity[0]]
        v,c=read_values_with_references(c,obj,fields=('WorldPartitionStreamingSource',))
        components=[x for k,x in v.values.items() if k[1]=='WorldPartitionStreamingSource']
        if v.errors or len(components)!=1 or components[0] is None:raise RuntimeError('Original owned streaming component missing')
        component=components[0]
        if radius is not None:
            from ._story_streaming_radius import encode,acknowledge
            packet=encode(self.actor.owner._owner,self.actor.identity,component,radius)
            self.unknown=True
            acknowledge(packet,self.scope._session._transport.command('mesh',packet))
            self.unknown=False
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        if construction is not None:
            # Reuse process-owned function schemas, never a source actor or a
            # readiness result. The actor/component above are freshly read;
            # retained function metadata is still natively validated per call.
            c=c.with_observations(construction.catalog(self.scope,('EnableStreamingSource','IsStreamingCompleted')))
            self.planner=construction.movement_planner(self.scope,c)
        else:
            metadata=prepare_metadata(self.scope._session)
            c=c.with_observations(capture_selected(self.scope.pid,tuple((o.index,o.serial,o.address) for o in metadata)))
            self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
        self.query=self.planner.prepare(component,c.find_path('/Script/Engine.WorldPartitionStreamingSourceComponent:IsStreamingCompleted'))
        enable=self.planner.prepare(component,c.find_path('/Script/Engine.WorldPartitionStreamingSourceComponent:EnableStreamingSource'))
        self.unknown=True
        with enable.invoke():pass
        self.unknown=False
    def ready(self):
        if self.unknown or self.closed or self.query is None:return False
        with self.query.invoke() as result:return result.return_value is True
    def retire_world(self):
        if self.closed:return True
        if self.unknown:return False
        if self.planner is not None:self.planner.close();self.planner=None
        if not self.actor.retire_world():return False
        from ._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope):return False
        self.closed=True;return True
    def close(self):return self.retire_world()
