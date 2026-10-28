"""Explicit lifecycle bridges for reviewed replay mechanisms.

These wrappers own backend objects before preparation starts. They normalize
outcomes for ReplayController; UI code never interprets backend truthiness.
Original game actions are observed in place and never stopped or destroyed.
"""
import time

from .controller import StartResult, StopResult, BackendState, ReplayObservation
from .._sequence_owner import SequenceCleanupDeferred


class TitleAdapter:
    def __init__(self, scope, scene, menu_provider, discovery):
        self.scope, self.scene = scope, scene
        self.menu_provider, self.discovery = menu_provider, discovery
        self.backend = None
        self.last = ReplayObservation(BackendState.ACTIVE, 'Preparing title')

    def start(self):
        from .title_replay import ExactTitleReplay
        from .title_profiles import TITLE_PROFILES
        from .title_adapters import OwnedTitleAdapters
        from .presentation import MenuPresentation
        from .retirement import title_retirement_available
        if not title_retirement_available(getattr(self.scope,'_session',self.scope)._transport):
            return StartResult.REJECTED
        profile = TITLE_PROFILES[self.scene['id']]
        self.backend = ExactTitleReplay(self.scope,
            lambda: self.menu_provider().panel, self.discovery,
            adapter_factory=lambda scope, panel: OwnedTitleAdapters(scope, panel, profile=profile),
            profile=profile, presentation_factory=lambda: MenuPresentation(self.menu_provider()))
        self.backend.start()
        self.backend.play()
        return StartResult.STARTED

    def status(self):
        return self.last

    def poll(self):
        state = self.backend.poll()
        self.last = ReplayObservation(BackendState.ACTIVE if state['active'] else BackendState.COMPLETE,
                                      'Title: ' + state['state'])
        return self.last

    def stop(self):
        if self.backend is None:
            return StopResult.STOPPED
        state = self.backend.stop()
        return StopResult.DEFERRED if state['active'] else StopResult.STOPPED

    def close(self, request):
        if self.backend is None:
            return True
        if not request.epoch_valid:
            from .retirement import retire_presentation
            backend = self.backend
            if backend.sequence is not None:
                dependents=()
                if backend.adapters is not None:
                    widget=getattr(backend.adapters,'widgets',None)
                    if widget is not None:dependents=(widget,)
                if not backend.sequence.retire_world(closed_dependents=dependents):return False
                backend.sequence = None
            if backend.adapters is not None:
                if not backend.adapters.retire_world():return False
                backend.adapters = None
            if backend.panel is not None:
                result = backend.panel.retire_world()
                if result == 'pending':return False
                if result != 'ack':raise RuntimeError('Title panel retirement was not acknowledged')
            retire_presentation(backend.presentation)
            backend.presentation = backend.panel = None
            backend.state = 'retired'
            return True
        return self.stop() is StopResult.STOPPED


class MediaAdapter:
    def __init__(self, scope, scene, menu_provider, discovery, stop_callback):
        self.scope, self.scene = scope, scene
        self.menu_provider, self.discovery, self.stop_callback = menu_provider, discovery, stop_callback
        self.backend = None
        self.running = False
        self._observed_playing = False
        self.opening_deadline = None
        self.last = ReplayObservation(BackendState.ACTIVE, 'Preparing video')

    def start(self):
        from .fullscreen_media import FullscreenMedia
        from .media_profiles import MEDIA_PROFILES
        from .media_audio_adapter import MediaAudioAdapter, admitted_audio_profile
        from .retirement import media_retirement_available
        if not media_retirement_available(getattr(self.scope,'_session',self.scope)._transport):
            return StartResult.REJECTED
        clip = self.scene.get('replay_kind') == 'movie_clip'
        if clip:
            from .movie_clips import clip_path
            path = clip_path(self.scene)
            profile = None
        else:
            profile = MEDIA_PROFILES[self.scene['id']]
            path = profile.movie_path
        menu = self.menu_provider()
        self.backend = FullscreenMedia(self.scope)
        self.backend.build(menu, path, self.stop_callback)
        audio = admitted_audio_profile(profile) if profile is not None else None
        if audio is not None:
            self.backend.audio_dependency = MediaAudioAdapter(self.scope, menu.panel, audio)
            self.backend.audio_dependency.prepare()
            fresh = self.discovery()
            if not any(row['id'] == self.scene['id'] and row.get('unlocked') is True
                       for row in fresh.get('confirmed', ())):
                return StartResult.REJECTED
        self.backend.play()
        self.opening_deadline = time.monotonic() + 10.
        return StartResult.STARTED

    def status(self):
        return self.last

    def poll(self):
        if self.backend.state == 'cleanup_pending':
            self.last = ReplayObservation(BackendState.FAILED, 'Video is awaiting cleanup')
            return self.last
        state = self.backend.playback_status(opening=not self.running)
        if not self.running:
            if state.get('IsReady') is True:
                if self.backend.resume() is not True:
                    raise RuntimeError('Media playback was not acknowledged')
                self.running = True
                state = self.backend.playback_status()
            elif time.monotonic() >= self.opening_deadline:
                self.last = ReplayObservation(BackendState.FAILED, 'Video could not be opened')
                return self.last
        if self.running and state.get('IsPaused') is True:
            self.last = ReplayObservation(BackendState.FAILED, 'Video paused unexpectedly')
            return self.last
        if state.get('IsPlaying') is True:
            self._observed_playing = True
        elif self._observed_playing:
            self.last = ReplayObservation(BackendState.COMPLETE if state.get('IsPaused') is not True
                                           else BackendState.FAILED, 'Video stopped')
            return self.last
        elif time.monotonic() >= self.opening_deadline:
            self.last = ReplayObservation(BackendState.FAILED, 'Video playback was never observed')
            return self.last
        if self.running and state.get('IsPlaying') is True and self.backend.audio_dependency is not None:
            self.backend.audio_dependency.poll(self.backend, True)
        self.last = ReplayObservation(BackendState.ACTIVE, 'Playing video' if self.running else 'Opening video')
        return self.last

    def stop(self):
        if self.backend is None:
            return StopResult.STOPPED
        return StopResult.STOPPED if self.backend.close() is True else StopResult.DEFERRED

    def close(self, request):
        if self.backend is None:
            return True
        if not request.epoch_valid:
            return self.backend.retire_world() is True
        return self.stop() is StopResult.STOPPED


class PreviewAdapter:
    def __init__(self, scope, scene):
        self.scope, self.scene = scope, scene
        self.panel = self.sequence = None
        self.last = ReplayObservation(BackendState.ACTIVE, 'Preparing preview')

    def start(self):
        from ..cinematic_context_panel import CinematicContextPanel
        from ..sequences import OwnedLevelSequence
        from ..simon_portable import _snapshot, WORLD
        from .library import PREVIEW_PROFILES
        profile = PREVIEW_PROFILES[self.scene['id']]
        if not profile.matches(self.scene):
            return StartResult.REJECTED
        context, _, position = _snapshot(self.scope)
        if context['world_path'] != WORLD:
            return StartResult.REJECTED
        target = (position[0] + 1500., position[1], position[2] + 500.)
        anchor = (21422.7285, 6693.6206, -402267.125)
        delta = tuple(target[i] - anchor[i] for i in range(3))
        self.panel = CinematicContextPanel(self.scope._session)
        self.panel.build()
        self.panel.open()
        self.sequence = OwnedLevelSequence(self.scope._session)
        self.sequence.build(self.panel, profile.sequence, capture_camera=True, origin_translation=delta)
        self.sequence.prepare_completion()
        self.sequence.play()
        return StartResult.STARTED

    def status(self):
        return self.last

    def poll(self):
        result = self.sequence.completion()
        state = result['state']
        progress=(f" | {result['position_seconds']:.1f} / {result['end_seconds']:.1f} s"
                  if 'position_seconds' in result and 'end_seconds' in result else '')
        self.last = ReplayObservation(BackendState.COMPLETE if result['endpoint_observed'] else
            BackendState.FAILED if state in ('cancelled', 'interrupted') else
            BackendState.UNKNOWN if state == 'unknown' else BackendState.ACTIVE,
            'Preview: ' + state + progress)
        return self.last

    def stop(self):
        try:
            if self.sequence is not None:
                self.sequence.close()
                self.sequence = None
            if self.panel is not None:
                self.panel.close()
                self.panel = None
        except SequenceCleanupDeferred:
            return StopResult.DEFERRED
        return StopResult.STOPPED

    def close(self, request):
        if not request.epoch_valid:
            if self.sequence is not None:
                if self.sequence.retire_world() is not True:
                    self.last=ReplayObservation(BackendState.UNKNOWN,'Waiting for positive native sequence retirement')
                    return False
                self.sequence=None
            if self.panel is not None:
                result=self.panel.retire_world()
                if result!='ack':
                    self.last=ReplayObservation(BackendState.UNKNOWN,'Owned panel retirement: '+str(result))
                    return False
                self.panel=None
            self.last=ReplayObservation(BackendState.COMPLETE,'Owned preview retired without old-world restoration')
            return True
        return self.stop() is StopResult.STOPPED


class OriginalActionAdapter:
    """Explicit story playback in the original map; no implicit map transition."""
    def __init__(self, scope, scene, profile):
        self.scope, self.scene, self.profile = scope, scene, profile
        self.prepared = None
        self.source = None
        self.seen = False
        self.dispatch_acknowledged = False
        self.idle_since = None
        self.idle_samples = 0
        self.monitor = None
        self.sequence_seen = False
        self.last = ReplayObservation(BackendState.ACTIVE, 'Preparing original story action')

    def start(self):
        from .original_game_action import prepare, NotReady
        self.prepared = prepare(self.scope, self.scene, self.profile)
        self.source = _prepared_action_source(self.prepared)
        from .._original_action_observation import CinematicActionMonitor
        self.monitor = CinematicActionMonitor(self.scope, prepared=self.prepared, profile=self.profile)
        try:
            self.prepared.play()
        except NotReady as error:
            self.last=ReplayObservation(BackendState.FAILED,str(error))
            return StartResult.REJECTED
        self.dispatch_acknowledged = True
        return StartResult.STARTED

    def status(self):
        # Recovery from a transient read failure must observe the game again.
        # A lost dispatch acknowledgement must never be converted into success.
        if not self.dispatch_acknowledged:
            return ReplayObservation(BackendState.UNKNOWN, 'Original action dispatch outcome is unknown')
        return self.poll()

    def poll(self):
        if not self.dispatch_acknowledged:
            return ReplayObservation(BackendState.UNKNOWN, 'Original action dispatch outcome is unknown')
        try:
            selected, cinematic_active = self._observe_activity()
        except Exception:
            self.idle_since = None
            self.idle_samples = 0
            raise
        return self._record_activity(selected, cinematic_active)

    def _record_activity(self, selected, cinematic_active):
        self.seen |= selected
        if selected or cinematic_active:
            self.idle_since = None
            self.idle_samples = 0
        else:
            now = time.monotonic()
            if self.idle_since is None:
                self.idle_since = now
            self.idle_samples += 1
        ended = self.seen and not selected and not cinematic_active
        # Some game actions finish synchronously or are skipped by the game.
        # Stable idle retires SDK observation only, never completes a campaign
        # action or advances an encounter. Report this as unverified failure.
        unobserved = (not self.seen and self.idle_since is not None and
                      self.idle_samples >= 3 and time.monotonic() - self.idle_since >= 10.0)
        state = BackendState.COMPLETE if ended else BackendState.FAILED if unobserved else BackendState.ACTIVE
        self.last = ReplayObservation(state,
            ('Original action completed; expected in-engine sequence observed' if self.sequence_seen else
             'Selected original action retired; visual completion is unverified') if ended else
            'No selected action observed after acknowledged dispatch; SDK tracking released, playback unverified' if unobserved else
            'Selected original story action active' if selected else 'Awaiting exact selected-action evidence')
        return self.last

    def _observe_activity(self):
        if self.monitor is not None:
            observed = self.monitor.observe()
            selected = any(row.action_identity == (self.source.pid, self.source.index,
                           self.source.serial, self.source.address) for row in observed.instances)
            if selected and observed.sequence_path == self.profile['sequence']:
                self.sequence_seen = True
            return selected, observed.sequence_player is not None or observed.pending_asset_request is not None
        from .._reader import ReadBatch
        from ..catalog import capture_selected
        from ..values import read_values_with_references, StoredArray
        from .history import field
        with ReadBatch(self.scope.pid, share=True, _executable=self.scope._session._transport._executable):
            objects = (self.prepared.executor, self.prepared.component)
            c = capture_selected(self.scope.pid, tuple((o.index, o.serial, o.address) for o in objects))
            v, c = read_values_with_references(c, c.by_index[objects[0].index],
                                             fields=('GameActionInstancesInExecution',))
            actions = field(v, 'GameActionInstancesInExecution', 'ArrayProperty')
            if (not isinstance(actions, StoredArray) or actions.length != len(actions.items) or
                    actions.length>64):
                raise RuntimeError('Original action activity observation is incomplete')
            selected=False
            for instance in actions.items:
                if instance is None:
                    raise RuntimeError('Original executor contains a null instance')
                c=c.with_observations(capture_selected(self.scope.pid,((instance.index,instance.serial,instance.address),)))
                observed,c=read_values_with_references(c,c.by_index[instance.index],fields=('GameAction',))
                action=field(observed,'GameAction','ObjectProperty')
                if action is None:raise RuntimeError('Original action instance has no attributable source')
                if _same_source(action,self.source):selected=True
            v, c = read_values_with_references(c, c.by_index[objects[1].index],
                                             fields=('LevelSequencePlayer', 'LoadCinematicAssetRequest'))
            cinematic_active=(field(v,'LevelSequencePlayer','ObjectProperty') is not None or
                              field(v,'LoadCinematicAssetRequest','ObjectProperty') is not None)
        return selected, cinematic_active

    def stop(self):
        raise RuntimeError('Original game-owned story actions cannot be stopped by Cinematics')

    def close(self, request):
        if self.prepared is not None:
            # Releases SDK plans/leases only. The game keeps its actors/actions.
            from .._retired_tracking import close_lease_only_scope
            self.prepared.planner.close()
            if not close_lease_only_scope(self.prepared.scope):return False
            self.prepared = None
        if self.monitor is not None:
            self.monitor.close()
            self.monitor = None
        return True


def _same_source(a,b):
    return b is not None and (a.pid,a.index,a.serial,a.address)==(b.pid,b.index,b.serial,b.address)


def _prepared_action_source(prepared):
    plan=prepared.call._plan
    parameters=tuple(p for p in plan.parameters if p.name=='GameAction' and p.kind=='ObjectProperty')
    if len(parameters)!=1:raise RuntimeError('Exact original action parameter is unavailable')
    matches=tuple(p.object for p in plan.objects if p.offset==parameters[0].offset)
    if len(matches)!=1 or matches[0] is None:raise RuntimeError('Exact original action source is unavailable')
    return matches[0]
