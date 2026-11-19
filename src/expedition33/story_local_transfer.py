"""Prepared, collision-qualified landing within one admitted world visit."""
import ctypes
from ._scope import SessionScope
from .catalog import capture_matching,capture_selected
from .map_runtime import context
from .map_readiness import NativeMapReadiness
from .values import read_values_with_references,capture_selected_values

class PreparedStoryLanding:
    def __init__(self,parent,runtime,ctx,position,yaw,*,floor_height):
        self.scope=SessionScope(parent);self.ctx=dict(ctx);self.position=tuple(position)
        self.floor_height=floor_height;self.ready=False;self.unknown=False;self.closed=False
        self.query=NativeMapReadiness(runtime,ctx,expected_token=parent._world_binding_token)
        c,pawns=capture_selected_values(parent.pid,(tuple(ctx['pawn']),),fields=('CapsuleComponent',),references=True)
        self.pawn=c.by_index[ctx['pawn'][0]];self.yaw=yaw
        values=pawns[self.pawn.index]
        capsules=[v for k,v in values.values.items() if k[1]=='CapsuleComponent']
        if values.errors or values.truncated or len(capsules)!=1 or capsules[0] is None:
            raise RuntimeError('Landing capsule observation incomplete')
        capsule=capsules[0]
        if (capsule.outer_index,capsule.outer_serial)!=(self.pawn.index,self.pawn.serial):
            raise RuntimeError('Landing capsule belongs to another pawn')
        values,c=read_values_with_references(c,capsule,fields=('CapsuleHalfHeight','RelativeScale3D'))
        fields={k[1]:v for k,v in values.values.items()}
        if values.errors or not fields.get('CapsuleHalfHeight'):raise RuntimeError('Landing capsule unavailable')
        self.half_height=fields['CapsuleHalfHeight']*abs(fields['RelativeScale3D'].fields['Z'])
        construction=getattr(self.scope._session,'_story_construction_resources',None)
        self.teleport_lease=None
        if construction is not None:
            # The process construction owner retains the original function and
            # its Vector/Rotator closure. A landing owns only its fresh pawn
            # observations and prepared call, not a duplicate metadata lease.
            c=c.with_observations(construction.catalog(self.scope,('K2_TeleportTo',)))
            self.planner=construction.movement_planner(self.scope,c)
            self.teleport=c.find_path('/Script/Engine.Actor:K2_TeleportTo')
        else:
            c=c.with_observations(capture_matching(parent.pid,names=('K2_TeleportTo','Vector','Rotator')))
            from ._stable_lease import acquire_stable
            self.teleport_lease,observed=acquire_stable(self.scope,c.find_path('/Script/Engine.Actor:K2_TeleportTo'))
            c=observed.with_observations(capture_matching(parent.pid,names=('Vector','Rotator')))
            c=c.with_observations(capture_selected(parent.pid,(tuple(ctx['pawn']),)))
            self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
            self.teleport=self.teleport_lease.object
        self._prepare_call()
    def _prepare_call(self):
        self.call=self.planner.prepare(self.pawn,self.teleport,
            DestLocation=dict(zip('XYZ',self.position)),DestRotation=dict(Pitch=0.,Yaw=self.yaw,Roll=0.))
    def qualify(self):
        if self.closed or self.unknown:raise RuntimeError('Landing owner unavailable')
        from .map_readiness import ReadinessPending
        try:r=self.query.query(position=self.position)
        except ReadinessPending:
            self.ready=False;return False
        self.ready=bool(r.collision_ready and not r.streaming_pending and
            all(abs(z-self.floor_height)<=20 for z in r.support_heights))
        if self.ready:
            grounded=max(r.support_heights)+self.half_height+2.15
            if abs(self.position[2]-grounded)>.1:
                self.position=(*self.position[:2],grounded);self._prepare_call()
        return self.ready
    def transfer(self,activation_ms,*,prepare_scene=None):
        if not self.ready or self.closed or self.unknown:raise RuntimeError('Preloaded collision-qualified landing required')
        construction=getattr(getattr(self.scope,'_session',None),'_story_construction_resources',None)
        if construction is None:
            valid=context(self.scope,require_bound_world=True)==self.ctx
        else:
            current=construction.context(self.scope)
            c,values=capture_selected_values(self.scope.pid,(tuple(current['controller'][1:]),),fields=('Pawn',),references=True)
            row=values[current['controller'][1]]
            pawn=next((v for k,v in row.values.items() if k[1]=='Pawn'),None)
            valid=(not row.errors and tuple(current['world'][1:])==tuple(self.ctx['visit']) and pawn is not None
                and (pawn.index,pawn.serial,pawn.address)==tuple(self.ctx['pawn']))
        if not valid:raise RuntimeError('Prepared landing possession changed')
        if prepare_scene is not None:prepare_scene()
        # Never replay a rejected/uncertain teleport. The same retained plan can
        # be used for a later, separate E activation only after success.
        self.unknown=True
        try:
            with self.call.invoke() as result:
                if result.return_value is not True:
                    self.unknown=False;self.ready=False
                    raise RuntimeError('Local landing rejected; qualify a different clear landing before another activation')
        except Exception as error:
            if getattr(error,'outcome',None)=='not_dispatched':self.unknown=False;self.ready=False
            raise
        self.unknown=False
        clock=ctypes.windll.kernel32.GetTickCount64;clock.restype=ctypes.c_ulonglong
        elapsed=int(clock())-activation_ms if activation_ms else None
        return elapsed
    def close(self):
        if self.closed:return True
        if self.unknown:return False
        self.planner.close();self.scope.close();self.closed=True;return True
