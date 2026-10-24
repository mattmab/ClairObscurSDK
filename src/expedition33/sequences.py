"""Experimental owned native sequence mechanism.

An asset load or successful factory call is not a safety audit. Game adapters
must establish unlocks, bindings and callback isolation before calling play.
The current candidate is tied to the owned menu's player/context lifecycle.
"""
from ._scope import SessionScope
from ._sequence_owner import NativeSequenceOwner, SequenceCleanupDeferred
from ._sequence_wire import settings
from .assets import load_asset
from .catalog import capture_matching, capture_selected
from .reflection import describe
from .invocation import CallPlan, Parameter, ObjectPatch


class OwnedLevelSequence:
    def __init__(self,session):
        self.scope=SessionScope(session)
        self.state='new'
        self.owner=NativeSequenceOwner(self.scope)
        self.scope._sequence_owners.append(self.owner)
        self.planner=self.player=self.actor=None
        self.uncertain=False

    @staticmethod
    def _one(values):
        rows=tuple(values)
        if len(rows)!=1: raise ValueError('Ambiguous sequence identity')
        return rows[0]

    def _class(self,name):
        return self._one(o for o in self.catalog.objects if o.name==name and o.class_name=='Class')

    def _function(self,owner,name):
        cls=self._class(owner)
        return self._one(o for o in self.catalog.objects if o.outer_index==cls.index and o.name==name and o.class_name=='Function')

    def build(self,panel,path,*,rate=1.,capture_camera=False,origin_translation=None):
        """Create without autoplay; optionally translate absolute sections.

        origin_translation is a delta, not a destination. It changes only the
        new actor's private instance data, never the shared sequence asset.
        It does not relocate possessable bindings, relative/additive tracks,
        events, or world dependencies. Adapters must qualify those separately.
        """
        if origin_translation is not None:
            from ._sequence_origin import encode
            encode(origin_translation)
            if getattr(self.scope._session._transport,'sequence_origin_protocol',0)!=1:
                raise RuntimeError('Verified native sequence origin capability required')
        if type(capture_camera) is not bool:
            raise ValueError('capture_camera must be a boolean')
        if capture_camera and getattr(self.scope._session._transport,'sequence_camera_protocol',0)!=1:
            raise RuntimeError('Verified native camera ownership capability required')
        if self.state!='new' or getattr(self.scope._session._transport,'sequence_player_protocol',0)!=1:
            raise RuntimeError('A new sequence owner and verified runtime are required')
        if panel.state!='open' or panel.uncertain or panel.scope._session is not self.scope._session:
            raise RuntimeError('An open panel in this session is required')
        self.state='building'
        loaded=load_asset(self.scope,path)
        asset=loaded.return_value
        if asset is None or asset.class_name!='LevelSequence': raise ValueError('Asset is not a LevelSequence')
        camera_names=('PlayerController','SetViewTargetWithBlend','EViewTargetBlendFunction') if capture_camera else ()
        self.catalog=capture_matching(self.scope.pid,names=(
            'LevelSequencePlayer','LevelSequenceActor','MovieSceneSequencePlayer','MovieSceneSequencePlaybackSettings',
            'Default__LevelSequencePlayer','Default__LevelSequenceActor','CreateLevelSequencePlayer',
            'K2_DestroyActor','Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused')+camera_names)
        self.catalog=self.catalog.with_observations(capture_selected(self.scope.pid,
            tuple((o.index,o.serial,o.address) for o in (panel.player,asset))))
        self.planner=self.scope.invocation_planner(selected_results=True,catalog=self.catalog)
        default=self._one(o for o in self.catalog.objects if o.name=='Default__LevelSequencePlayer')
        actor_default=self._one(o for o in self.catalog.objects if o.name=='Default__LevelSequenceActor')
        stop=self.planner.prepare(default,self._function('MovieSceneSequencePlayer','Stop'))._plan
        destroy=self.planner.prepare(actor_default,self._function('Actor','K2_DestroyActor'))._plan
        fn=self._function('LevelSequencePlayer','CreateLevelSequencePlayer')
        d=describe(self.catalog,(fn,))[fn.index]
        parameters=[]
        for p in d.properties:
            prefix='struct' if p['type']=='StructProperty' else 'property_class'
            constraint=self.catalog.by_index[p[prefix+'_index']]
            if constraint.serial!=p[prefix+'_serial']: raise ValueError('Factory constraint changed')
            parameters.append(Parameter(p['name'],'SequencePlaybackSettings' if p['name']=='Settings' else p['type'],
                p['offset'],p['element_size'],p['dimension'],p['flags'],constraint=constraint))
        info=d.function
        plan=CallPlan(default,fn,info['flags'],int(info['entry_rva'],16),info['params_size'],d.owners[0]['size'],
            info['return_offset'],tuple(parameters),bytes(16)+settings(rate)+bytes(16),
            (ObjectPatch(0,panel.player),ObjectPatch(8,asset)),7)
        # Validate wire locally before preparing durable native ownership.
        from ._sequence_wire import encode_plan
        encode_plan(plan)
        self.owner.prepare(stop,destroy)
        if capture_camera:
            restore=self.planner.prepare(panel.player,
                self._function('PlayerController','SetViewTargetWithBlend'),
                NewViewTarget=None,BlendTime=0.,blendFunc=0,BlendExp=0.,bLockOutgoing=False)
            self.owner.arm_camera(restore._plan)
        self.uncertain=True
        with self.scope._lease_context():
            owned,current=self.scope._session._invoke_retained_plan(plan,self.catalog,_return_catalog=True,_selected_results=True)
        self.scope._adopt_retained(owned)
        self.player=owned.return_value
        self.actor=owned.outputs.get('OutActor')
        if self.player is None or self.actor is None: raise RuntimeError('Sequence factory returned no player')
        self.planner.refresh_from(current)
        if self.owner.status()!='armed': raise RuntimeError('Native sequence ownership not armed')
        if origin_translation is not None:
            self.owner.configure_origin(origin_translation)
        self.uncertain=False
        self.state='ready'
        return self

    def _call(self,name,**args):
        self.scope._check()
        if self.uncertain or self.state not in ('ready','playing','paused','stopped'):
            raise RuntimeError('Sequence is unavailable')
        if self.owner.status()!='armed': raise RuntimeError('Sequence context was closed')
        prepared=self.planner.prepare(self.player,self._function('MovieSceneSequencePlayer',name),**args)
        self.uncertain=True
        with prepared.invoke(refresh_from_result=True) as result:
            value=result.return_value
        self.uncertain=False
        return value

    def play(self):
        self._call('Play'); self.state='playing'

    def pause(self):
        self._call('Pause'); self.state='paused'

    def resume(self): self.play()

    def stop(self):
        self._call('Stop'); self.state='stopped'

    def restart(self):
        self.stop(); self.play()

    def set_rate(self,rate):
        settings(rate)
        self._call('SetPlayRate',PlayRate=float(rate))

    def status(self):
        return {'state':self.state,'playing':self._call('IsPlaying'),'paused':self._call('IsPaused'),
                'rate':self._call('GetPlayRate')}

    def close(self):
        if self.state=='closed': return
        if not self.owner.close(): raise SequenceCleanupDeferred('Sequence cleanup deferred')
        if self.planner is not None: self.planner.close()
        self.scope.close()
        self.state='closed'
