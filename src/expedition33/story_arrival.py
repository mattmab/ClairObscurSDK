"""Prepare a story destination under an existing native loading hold."""
import logging
import time
from ._scope import SessionScope
from .map_runtime import MapRuntime,context
from .map_readiness import NativeMapReadiness,ReadinessPending
from .story_layers import StoryDataLayers
from .catalog import capture_matching,capture_selected

LOG=logging.getLogger('expedition33.story_arrival')
_NATIVE_READINESS_TYPE=NativeMapReadiness

class StorySceneArrival:
    def __init__(self,parent,ctx,token,gate,*,layers,position,yaw,floor_height,runtime=None):
        self._scope=parent;self.scope=SessionScope(parent);self.ctx=dict(ctx);self.token=token;self.gate=gate
        self.position=tuple(position) if position is not None else None;self.yaw=yaw;self.floor_height=floor_height
        self.state='new';self.layers=StoryDataLayers(self.scope);self.runtime=runtime;self.query=None;self.receipt=None
        self._owns_runtime=runtime is None
        if runtime is not None:
            if (runtime.scope._session is not parent._session or not runtime.started or
                    runtime.uncertain or runtime._closed):
                raise RuntimeError('Arrival requires a live map from the same session')
        parent._register_native_owner(self);parent._close_before_descendants(self)
        self.layer_states=dict(layers)
        self.timings={}
    def advance(self):
        if self.state=='ready':return True
        if self.state in ('closed','unknown'):raise RuntimeError('Scene arrival unavailable')
        # ACKed preparation can proceed immediately. A scheduler turn is not
        # evidence that streaming completed: query it once and yield only when
        # the layer/floor/visibility observation is actually pending. Three
        # phases bound this work; every phase re-proves possession and the hold.
        for _ in range(3):
            phase=self.state;started=time.perf_counter()
            try:
                if not self._admitted():return False
                ready=self._advance_phase()
            finally:
                elapsed=(time.perf_counter()-started)*1000
                timings=getattr(self,'timings',None)
                if timings is None:self.timings=timings={}
                row=timings.setdefault(phase,dict(count=0,ms=0.,max_ms=0.))
                row['count']+=1;row['ms']+=elapsed;row['max_ms']=max(row['max_ms'],elapsed)
            if ready:
                LOG.info('Story arrival ready; active phase timings=%s',self.timings)
                return True
            if self.state==phase:return False
        return False
    def _admitted(self):
        if self.state=='observing' and type(self.query) is _NATIVE_READINESS_TYPE:
            # The following native query checks viewport/World, possession and
            # the exact GI/save-manager/slot before AND after its floor traces.
            # Do not precede that read-only proof with the same Python graph
            # query every pending tick. Preparation/placement still require it.
            self.scope._check()
            if (self.query.runtime is not self.runtime or self.query.expected!=self.ctx or
                    self.query.expected_token!=self.query._token(self.token)):
                raise RuntimeError('Story landing native context proof changed')
        else:
            fresh=context(self.scope,require_bound_world=True)
            if fresh!=self.ctx:raise RuntimeError('Story landing possession changed')
        held=self.gate.status()
        exact=held['world']==self.ctx['visit'] and held['pawn']==self.ctx['pawn']
        if exact and held['state']==2:return True
        # A loaded checkpoint has no placement to execute. Once its native
        # hold has ended, finish only the read-only floor/render proof; otherwise
        # the already playable visit can never clear its narrative admission.
        return bool(exact and held['state']==1 and self.state=='observing' and
            getattr(self,'position','placement-required') is None and
            type(held.get('hold_sequence')) is int and held['hold_sequence']>0)
    def _advance_phase(self):
        if self.state=='new':
            if self.layer_states:
                self.state='preparing'
                self.layers.prepare(self.ctx,self.layer_states);self.layers.apply()
            self.state='layers'
            return False
        if self.state=='layers':
            if self.layer_states and not self.layers.requested_ready():return False
            if self.position is not None:
                c=capture_selected(self.scope.pid,(tuple(self.ctx['pawn']),))
                construction=getattr(self.scope._session,'_story_construction_resources',None)
                c=c.with_observations(construction.catalog(self.scope,('K2_TeleportTo',)) if construction is not None else
                    capture_matching(self.scope.pid,names=('K2_TeleportTo','Vector','Rotator')))
                pawn=c.by_index[self.ctx['pawn'][0]]
                with (construction.movement_planner(self.scope,c) if construction is not None else
                        self.scope.invocation_planner(catalog=c,selected_results=True)) as planner:
                    call=planner.prepare(pawn,c.find_path('/Script/Engine.Actor:K2_TeleportTo'),DestLocation=dict(zip('XYZ',self.position)),DestRotation={'Pitch':0.,'Yaw':self.yaw,'Roll':0.})
                    self.state='unknown'
                    with call.invoke() as result:
                        if result.return_value is not True:raise RuntimeError('Story landing placement rejected; hold retained')
            self.state='placed'
            if self.runtime is None:
                self.runtime=MapRuntime(self.scope);self.runtime._prepare(self.ctx)
            self.query=NativeMapReadiness(self.runtime,self.ctx,expected_token=self.token);self.state='observing'
            return False
        if self.state=='observing':
            try:self.receipt=self.query.query()
            except ReadinessPending:return False
            r=self.receipt
            # A borrowed map can contain only invisible collision helpers. Its
            # rows must not become visible before releasing the player. Require
            # actual rendered landing support and completed streaming instead.
            visual=r.visual_ready or (not getattr(self,'_owns_runtime',True) and
                r.rows>0 and r.live_rows==r.rows and r.collision_query_rows==r.rows and
                r.visible_rows==0 and r.streaming_pending==0 and
                r.support_samples>0 and r.support_hits==r.support_samples and
                r.rendered_support_hits==r.support_samples)
            if not r.collision_ready or not visual or (self.floor_height is not None and any(abs(z-self.floor_height)>20 for z in r.support_heights)):return False
            # The native map owner is exclusive. Release the empty observation
            # owner before the caller loads its actual story geometry.
            if getattr(self,'_owns_runtime',True) and not self.runtime.close():return False
            self.runtime=None;self.query=None
            self.state='ready';return True
        raise RuntimeError('An incomplete scene preparation cannot be replayed')
    def retire_world(self,*,retirement=None):
        fresh=context(self.scope)
        verified=(retirement is not None and retirement.reason in ('title','epoch_changed','loading_world_changed') and tuple(retirement.previous_token[0][1:])==tuple(self.ctx['visit']))
        if not verified and (not fresh or fresh['visit']==self.ctx['visit']):return False
        if self.runtime is not None and getattr(self,'_owns_runtime',True) and self.runtime.retire_world()!='ack':return False
        if not self.layers.retire_world(retirement=retirement):return False
        self.scope.close();self.state='closed';return True
    def close(self):
        if self.state=='closed':return True
        # Removing the loaded floor beneath the player is not valid cleanup.
        # Leave this scene through travel before disabling its owner.
        fresh=context(self.scope)
        if fresh and fresh['visit']==self.ctx['visit']:return False
        return self.retire_world()
