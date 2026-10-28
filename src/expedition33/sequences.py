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
from ._menu_latency import measure_method
from contextlib import contextmanager

_PLAYBACK_QUERIES=('IsPlaying','IsPaused','GetPlayRate','GetCurrentTime','GetEndTime')
_PLAYBACK_METADATA=('MovieSceneSequencePlayer','GetCurrentTime','GetEndTime',
    'QualifiedFrameTime','FrameTime','FrameRate','FrameNumber',
    'Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused')


class OwnedLevelSequence:
    def __init__(self,session,*,asset_loader=None,metadata=None):
        self.scope=SessionScope(session)
        self.asset_loader=asset_loader
        self.metadata=metadata
        self.state='new'
        self.owner=NativeSequenceOwner(self.scope)
        self.scope._sequence_owners.append(self.owner)
        self.planner=self.player=self.actor=None
        self._asset=None
        self.uncertain=False
        self._endpoint=None
        self._completion_invalidated=False
        self._seek_function=None
        self._evaluation_attempted=False
        self._actor_binding_attempts=set()
        self._authored_actor_journals=[]
        self._query_group_active=False

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

    @measure_method('sequence.build')
    def build(self,panel,path,*,rate=1.,capture_camera=False,origin_translation=None,origin_yaw=None,asset=None,completion=False):
        """Create without autoplay; optionally translate absolute sections.

        origin_translation is a delta, not a destination. It changes only the
        new actor's private instance data, never the shared sequence asset.
        It does not relocate possessable bindings, relative/additive tracks,
        events, or world dependencies. Adapters must qualify those separately.
        asset optionally supplies an already retained private sequence copy;
        this owner acquires its own lease before creating the player.
        completion prepares the finite endpoint inside this construction call,
        sharing its post-factory metadata scan. It does not start playback.
        """
        if type(completion) is not bool:raise ValueError('completion must be a boolean')
        if completion:self._require_completion_protocols()
        if origin_yaw is not None:
            from ._sequence_origin import encode_transform
            encode_transform(origin_translation,origin_yaw)
            if getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)!=1:
                raise RuntimeError('Verified native sequence origin transform capability required')
        elif origin_translation is not None:
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
        if asset is None:
            with self.latency.measure('sequence.asset_load'):
                asset=load_asset(self.scope,path,**({'prepared':self.asset_loader} if self.asset_loader is not None else {})).return_value
        else:
            if asset.pid!=self.scope.pid or asset.class_name!='LevelSequence':
                raise ValueError('Retained LevelSequence must belong to this process')
            from .cinematics.authored_copy import seal_copy
            seal_copy(self.scope,asset)
            asset=self.scope.retain(asset).object
        if asset is None or asset.class_name!='LevelSequence': raise ValueError('Asset is not a LevelSequence')
        self._asset=asset
        camera_names=('PlayerController','SetViewTargetWithBlend','EViewTargetBlendFunction') if capture_camera else ()
        with self.latency.measure('sequence.factory_metadata'):
            names=(
                'LevelSequencePlayer','LevelSequenceActor','MovieSceneSequencePlayer','MovieSceneSequencePlaybackSettings',
                'Default__LevelSequencePlayer','Default__LevelSequenceActor','CreateLevelSequencePlayer',
                'K2_DestroyActor','Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused')+camera_names
            self.catalog=(self.metadata.capture(self.scope,names=names) if self.metadata is not None else
                          capture_matching(self.scope.pid,names=names))
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
        with self.latency.measure('sequence.native_owner'):
            self.owner.prepare(stop,destroy)
            if capture_camera:
                restore=self.planner.prepare(panel.player,
                    self._function('PlayerController','SetViewTargetWithBlend'),
                    NewViewTarget=None,BlendTime=0.,blendFunc=0,BlendExp=0.,bLockOutgoing=False)
                self.owner.arm_camera(restore._plan)
        self.uncertain=True
        with self.latency.measure('sequence.factory_dispatch'):
            with self.scope._lease_context():
                # Sequence creation can load a nested cast and stabilize previously
                # serial-zero metadata. Discard pre-factory observations instead of
                # merging new output closures into that older catalog.
                owned,current=self.scope._session._invoke_retained_plan(plan,self.catalog,
                    _return_catalog=True,_selected_results=True,_fresh_results=True)
        self.scope._adopt_retained(owned)
        self.player=owned.return_value
        self.actor=owned.outputs.get('OutActor')
        if self.player is None or self.actor is None: raise RuntimeError('Sequence factory returned no player')
        return self._finish_build(current,origin_translation,completion,origin_yaw)

    @measure_method('sequence.finish_build')
    def _finish_build(self,current,origin_translation,completion,origin_yaw=None):
        # This is the immediate factory continuation, before returning to user
        # code. Nested cast loading has finished, so all descriptors below are
        # freshly observed after construction. No metadata-ready flag escapes.
        names=_PLAYBACK_METADATA if completion else ('MovieSceneSequencePlayer',
            'Stop','Play','Pause','SetPlayRate','GetPlayRate','IsPlaying','IsPaused')
        with self.latency.measure('sequence.playback_metadata'):
            metadata=getattr(self,'metadata',None)
            fresh=(metadata.capture(self.scope,names=names) if metadata is not None else
                   capture_matching(self.scope.pid,names=names))
            self.catalog=fresh.with_observations(current)
        self.planner.refresh_from(self.catalog)
        if self.owner.status()!='armed': raise RuntimeError('Native sequence ownership not armed')
        if origin_yaw is not None:
            self.owner.configure_origin_transform(origin_translation,origin_yaw)
        elif origin_translation is not None:
            self.owner.configure_origin(origin_translation)
        self.uncertain=False
        self.state='ready'
        if completion:
            with self.latency.measure('sequence.completion_prepare'):
                self._prepare_completion(refresh_metadata=False)
        return self

    def _call(self,name,**args):
        self.scope._check()
        if self.uncertain or self.state not in ('ready','playing','paused','stopped'):
            raise RuntimeError('Sequence is unavailable')
        grouped=getattr(self,'_query_group_active',False)
        if grouped and name not in _PLAYBACK_QUERIES:raise RuntimeError('Playback query groups cannot mutate a sequence')
        if not grouped and self.owner.status()!='armed': raise RuntimeError('Sequence context was closed')
        queries=_PLAYBACK_QUERIES
        ticket=None
        if self._endpoint is not None and name not in queries:
            ticket=self._endpoint.begin_command(name)
        try:
            prepared=self.planner.prepare(self.player,self._function('MovieSceneSequencePlayer',name),**args)
            self.uncertain=True
            with prepared.invoke(refresh_from_result=True) as result:
                value=result.return_value
        except BaseException:
            if ticket is not None:
                self._endpoint.finish_command(ticket,returned=False)
            elif self._endpoint is not None:
                self._endpoint.state='unknown'
            raise
        if ticket is not None:
            self._endpoint.finish_command(ticket,returned=True)
        self.uncertain=False
        return value

    @contextmanager
    def _query_group(self):
        """Bound read-only calls with fresh owner checks at both ends.

        Each reflected invocation still validates its own target and schema.
        Endpoint callers additionally compare fresh world contexts around the
        group. No result or ownership observation survives this lexical scope.
        """
        self.scope._check()
        if getattr(self,'_query_group_active',False) or self.uncertain:
            raise RuntimeError('Playback query group is unavailable')
        if self.owner.status()!='armed':raise RuntimeError('Sequence context was closed')
        self._query_group_active=True
        try:
            yield
            if self.owner.status()!='armed':raise RuntimeError('Sequence context changed during playback queries')
        finally:self._query_group_active=False

    def _refresh_playback_metadata(self,*,include_seek=False):
        names=_PLAYBACK_METADATA+('SetPlaybackPosition',) if include_seek else _PLAYBACK_METADATA
        extra=capture_matching(self.scope.pid,names=names)
        # Nested cast loading can assign previously unassigned metadata serials.
        # Discard the factory catalog; retain only fresh descriptors and the
        # independently selected native-owned player/actor identities.
        self.catalog=extra.with_observations(capture_selected(self.scope.pid,
            tuple((o.index,o.serial,o.address) for o in (self.player,self.actor))))
        self.planner.refresh_from(self.catalog)

    def prepare_scrubbing(self):
        """Prepare interactive playback queries without endpoint tracking.

        The first native seek validates the owned player's live context. A
        scrubber cannot claim natural completion, including before its first
        seek; its owner must be closed explicitly.
        """
        self.scope._check()
        if self.state!='ready' or self.uncertain or self._endpoint is not None or self._completion_invalidated:
            raise RuntimeError('Scrubbing requires a new ready sequence')
        transport=self.scope._session._transport
        if any(type(value) is not int or value!=1 for value in (
                getattr(transport,'frame_time_values_protocol',0),getattr(transport,'sequence_seek_protocol',0))):
            raise RuntimeError('Verified frame-time and seek capabilities required')
        self._refresh_playback_metadata(include_seek=True)
        # Reuse the freshly selected metadata while preparing the scrubber.
        # Stabilize the function on this scope now; the initial seek can then
        # avoid a second whole-registry discovery after context is armed.
        self._prepare_seek_function(self.catalog)
        self._completion_invalidated=True

    def prepare_completion(self):
        """Opt in before Play to one finite owned endpoint observation.

        This observes a natural playback endpoint; it does not fabricate an
        Unreal OnFinished delegate callback. Stop/seek/unknown outcomes invalidate
        the attempt. A tracked attempt is one-shot: use a new owner to replay.
        """
        return self._prepare_completion(refresh_metadata=True)

    def _require_completion_protocols(self):
        transport=self.scope._session._transport
        protocols=(getattr(transport,'frame_time_values_protocol',0),
                   getattr(transport,'sequence_player_protocol',0))
        if any(type(value) is not int or value!=1 for value in protocols):
            raise RuntimeError('Verified sequence and frame-time capabilities required')

    @measure_method('sequence.completion_prepare_total')
    def _prepare_completion(self,*,refresh_metadata):
        from ._sequence_endpoint import OwnedSequenceEndpoint, current_owned_context
        self.scope._check()
        if self.state!='ready' or self.uncertain or self._endpoint is not None or self._completion_invalidated:
            raise RuntimeError('Completion tracking requires a new ready sequence')
        self._require_completion_protocols()
        with self.latency.measure('sequence.completion_context_before'):
            context=current_owned_context(self)
        if refresh_metadata:self._refresh_playback_metadata()
        with self.latency.measure('sequence.completion_idle_queries'):
            with self._query_group():
                if self._call('IsPlaying') or self._call('IsPaused'):
                    raise RuntimeError('Completion tracking must precede playback')
                end=self._call('GetEndTime')
        with self.latency.measure('sequence.completion_context_after'):
            if current_owned_context(self)!=context:
                raise RuntimeError('Sequence context changed during completion preparation')
        self._endpoint=OwnedSequenceEndpoint(context,end)
        # The just-created player is confirmed idle and the end/context were
        # validated above. A second full observation cannot establish playback
        # progress before Play; it only repeats four calls and two world reads
        # while input is locked. Real playback polls still use completion().
        return {'state':'ready','endpoint_observed':False,
                'on_finished_observed':False,'seen_playing':False}

    def completion(self):
        """Return copied endpoint evidence for this opted-in attempt only."""
        from ._sequence_endpoint import current_owned_context
        if self._endpoint is None:
            raise RuntimeError('Sequence completion tracking is not prepared')
        try:
            context=current_owned_context(self)
            # Observe state before cursor: natural completion may occur between
            # requests. A cursor sampled while still playing must not be paired
            # with a later stopped state and mistaken for an interruption.
            with self._query_group():
                playing=self._call('IsPlaying')
                paused=self._call('IsPaused')
                current=self._call('GetCurrentTime')
                end=self._call('GetEndTime')
            if current_owned_context(self)!=context:
                raise RuntimeError('Sequence context changed during completion observation')
            state=self._endpoint.observe(context=context,current_time=current,end_time=end,
                playing=playing,paused=paused)
        except BaseException:
            self._endpoint.state='unknown'
            raise
        scale=current['Rate']['Denominator']/current['Rate']['Numerator']
        end_scale=end['Rate']['Denominator']/end['Rate']['Numerator']
        return {'state':state,'endpoint_observed':state=='endpoint_observed',
                'on_finished_observed':False,'seen_playing':self._endpoint.seen_playing,
                'position_seconds':(current['Time']['FrameNumber']['Value']+current['Time']['SubFrame'])*scale,
                'end_seconds':(end['Time']['FrameNumber']['Value']+end['Time']['SubFrame'])*end_scale}

    def play(self):
        self._evaluation_attempted=True
        self._call('Play'); self.state='playing'

    def pause(self):
        self._call('Pause'); self.state='paused'

    def move_origin(self,translation):
        """Move this instance while idle; the caller then reevaluates its frame."""
        from ._sequence_origin import encode
        encode(translation)
        if getattr(self.scope._session._transport,'sequence_origin_update_protocol',0)!=1:
            raise RuntimeError('Native live sequence placement capability required')
        if self.uncertain or self.state not in ('ready','playing','paused','stopped'):raise RuntimeError('Sequence is unavailable')
        if self.state=='playing':self.pause()
        prepared=self.planner.prepare(self.player,self._function('MovieSceneSequencePlayer','IsPlaying'))
        self.uncertain=True
        try:return self.owner.update_origin(translation,prepared._plan)
        finally:
            if self.owner.state=='armed':self.uncertain=False

    def move_origin_transform(self,translation,yaw):
        """Move and rotate this owned private origin while its player is idle."""
        from ._sequence_origin import encode_transform
        encode_transform(translation,yaw)
        if getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)!=1:
            raise RuntimeError('Native sequence origin transform capability required')
        if self.uncertain or self.state not in ('ready','playing','paused','stopped'):raise RuntimeError('Sequence is unavailable')
        if self.state=='playing':self.pause()
        prepared=self.planner.prepare(self.player,self._function('MovieSceneSequencePlayer','IsPlaying'))
        self.uncertain=True
        try:return self.owner.update_origin_transform(translation,yaw,prepared._plan)
        finally:
            if self.owner.state=='armed':self.uncertain=False

    def _prepare_seek_function(self,catalog=None):
        if self._seek_function is not None:return
        if catalog is None:
            catalog=capture_matching(self.scope.pid,names=('MovieSceneSequencePlayer','SetPlaybackPosition'))
        cls=self._one(o for o in catalog.objects if o.name=='MovieSceneSequencePlayer' and o.class_name=='Class')
        function=self._one(o for o in catalog.objects if o.outer_index==cls.index and
            o.name=='SetPlaybackPosition' and o.class_name=='Function')
        # Stabilize serial-zero metadata before the function can be used.
        # Acquisition adopts its lease before reading back the exact identity;
        # any failure belongs to normal scope cleanup, never an implicit retry.
        from ._stable_lease import acquire_stable
        lease,_=acquire_stable(self.scope,function)
        self._seek_function=lease.object

    def seek_frame(self,frame,subframe=0.):
        """Scrub this owned player; frame units use its qualified frame rate.

        Pause an active preview first. Scrubbing cancels natural-completion
        tracking permanently for this owner, including a seek to its endpoint.
        It does not apply timeline document edits to the source asset.
        """
        from . import _sequence_seek as seek
        self.scope._check()
        capability=getattr(self.scope._session._transport,'sequence_seek_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Verified owned sequence seek capability required')
        if self.uncertain or self.state not in ('ready','playing','paused','stopped'):
            raise RuntimeError('Sequence is unavailable')
        if self._seek_function is None:
            self._prepare_seek_function()
        seek.encode(self._seek_function,frame,subframe)
        if self.state=='playing':self.pause()
        if self._endpoint is not None:self._endpoint.state='cancelled'
        self._endpoint=None;self._completion_invalidated=True
        self.uncertain=True
        self._evaluation_attempted=True
        try:self.owner.seek_frame(self._seek_function,frame,subframe)
        finally:
            # A known no-dispatch rejection keeps cleanup available. Unknown
            # native outcomes leave this owner unavailable and retained.
            if self.owner.state=='armed':self.uncertain=False
        return True

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

    def _close_authored_actors(self,*,retiring=False):
        # The consumer has already acknowledged closure. Retain the journals
        # on a deferred actor release so the same owner can be retried safely.
        journals=getattr(self,'_authored_actor_journals',())
        for journal in journals:
            for actor in journal:
                if not (actor.retire_world() if retiring else actor.close()):return False
        if journals:self._authored_actor_journals=[]
        return True

    def close(self):
        if self.state=='closed': return
        if getattr(self.owner,'_retiring',False) is True:
            if not self.retire_world():raise SequenceCleanupDeferred('Retired sequence cleanup deferred')
            return
        if not self.owner.close(): raise SequenceCleanupDeferred('Sequence cleanup deferred')
        if not self._close_authored_actors(): raise SequenceCleanupDeferred('Sequence actor cleanup deferred')
        if self.planner is not None: self.planner.close()
        self.scope.close()
        self.state='closed'

    def retire_world(self, *, closed_dependents=()):
        """Retire an old-world owned player without gameplay compensation."""
        if self.state=='closed':return True
        if not self.owner.retire_world():return False
        if not self._close_authored_actors(retiring=True):return False
        from ._cinematic_widget import NativeCinematicWidgets
        if closed_dependents and getattr(self.owner,'_retirement_ack',False) is not True:
            raise RuntimeError('Sequence retirement receipt is unavailable')
        for dependent in closed_dependents:
            if type(dependent) is not NativeCinematicWidgets or dependent.scope is not self.scope or (dependent not in self.scope._audio_owners and dependent.state!='closed'):
                raise RuntimeError('Unrelated sequence retirement dependent')
            dependent.state='closed'
            if dependent in self.scope._audio_owners:self.scope._audio_owners.remove(dependent)
        if self.planner is not None:self.planner.close()
        # Native sequence/camera holders are already acknowledged closed.
        # This child scope now contains only its retained asset/factory outputs.
        from ._retired_tracking import close_lease_only_scope
        if not close_lease_only_scope(self.scope,closed_sequence_owners=(self.owner,)):return False
        if self._endpoint is not None:self._endpoint.state='cancelled'
        self.state='closed'
        return True
