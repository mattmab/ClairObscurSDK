"""Reviewed profile-bound title replay. Arming is not playback validation.

Controller-thread orchestration only; native owners retain game-thread cleanup.
This adapter does not authorize other cinematic definitions or save changes.
"""
import json
import logging
import time
from expedition33._sequence_owner import SequenceCleanupDeferred
from expedition33.cinematics.title_profiles import PROLOGUE, TITLE_PROFILES

LOG = logging.getLogger('expedition33.cinematics')

DEFINITION = 'Sandfall/Content/Cinematics/Titles/SequenceTitles/DA_GA_CIN_Title_PrologueLumiere.uasset'
SEQUENCE = '/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere.LS_Title_PrologueLumiere'
SAVE_ID = 'PrologueTitle'


class ExactTitleReplay:
    def __init__(self, session, panel_provider, discover, *, adapter_factory,
                 sequence_factory=None, presentation_factory=None, clock=time.monotonic, profile=PROLOGUE):
        if TITLE_PROFILES.get(profile.definition) is not profile:
            raise ValueError('Replay requires an immutable reviewed title profile')
        self.profile=profile
        if sequence_factory is None:
            from expedition33.sequences import OwnedLevelSequence
            sequence_factory = OwnedLevelSequence
        self.session, self.panel_provider, self.discover = session, panel_provider, discover
        self.adapter_factory, self.sequence_factory, self.clock = adapter_factory, sequence_factory, clock
        self.presentation_factory = presentation_factory
        self.sequence = self.adapters = self.panel = self.presentation = None
        self.state = 'idle'
        self.error = None
        self.cleanup_error = None
        self._failure_exception = None
        self.evidence = {}
        self._next_poll = self._deadline = self._started = 0.
        self._observed_playing = False
        self._cleanup_deadline = None

    def _verify_unlock(self, definition):
        if definition != self.profile.definition:
            raise ValueError('No isolated replay adapter for this definition')
        if not self.profile.available(self.session._session._transport):
            raise RuntimeError('Runtime does not admit this exact title profile')
        discovery = self.discover()
        # The callback returns the fresh discovery dictionary, not cached status.
        rows = [s for s in discovery.get('confirmed', ()) if s.get('id') == definition]
        if (discovery.get('state') != 'history_verified' or
                discovery.get('definition_catalog_complete') is not True or len(rows) != 1 or
                rows[0].get('unlocked') is not True or not self.profile.matches(rows[0])):
            raise RuntimeError('Exact cinematic mapping and current-save unlock must be verified')

    def start(self, definition=None, *, play=False):
        definition=self.profile.definition if definition is None else definition
        # Prepare-only is the default acceptance gate; arming cannot play.
        if self.sequence is not None or self.adapters is not None or self.presentation is not None:
            raise RuntimeError('Stop the current replay before starting another')
        self.evidence = {'definition': definition, 'profile_id': self.profile.profile_id, 'preparation_timings': {}}
        self._prepare_step('unlock', self._verify_unlock, definition)
        self.panel = self.panel_provider()
        if self.panel is None or self.panel.state != 'open' or self.panel.uncertain:
            raise RuntimeError('An open owned menu is required')
        self.state, self.error = 'preparing', None
        self.cleanup_error = self._failure_exception = None
        self._cleanup_deadline = None
        try:
            # Read and plan visual restoration before any native replay adapters
            # arm. No menu mutation occurs until the explicit Play operation.
            if self.presentation_factory is not None:
                self.presentation = self.presentation_factory()
                self._prepare_step('presentation', self.presentation.prepare)
            # Allocate owners before invoking preparation so partial failures
            # remain reachable for deterministic cleanup.
            self.adapters = self.adapter_factory(self.session, self.panel)
            self._prepare_step('music', self.adapters.prepare_music)
            self.sequence = self.sequence_factory(self.session)
            self._prepare_step('sequence_build', self.sequence.build, self.panel, self.profile.sequence)
            self._prepare_step('adapter_arm', self.adapters.arm, self.sequence)
            self.evidence['armed'] = self._prepare_step('armed_status', self.adapters.status)
            self.state = 'armed'
            self._started = self.clock()
            self._deadline = self._started + 180.
            self._next_poll = self._started
            self._observed_playing = False
            if play:
                self.play()
        except BaseException as error:
            self._fail(error, 'start')
            raise
        return self.status()

    def _prepare_step(self, name, operation, *args):
        started = time.perf_counter()
        success = False
        try:
            result = operation(*args)
            success = True
            return result
        finally:
            elapsed = time.perf_counter() - started
            self.evidence.setdefault('preparation_timings', {})[name] = dict(seconds=elapsed, completed=success)
            LOG.info('Cinematic preparation phase %s: %.3fs completed=%s', name, elapsed, success)

    def play(self):
        if self.state != 'armed' or self.sequence is None:
            raise RuntimeError('Prepare the exact replay before playing')
        try:
            transport = self.session._session._transport
            if any(type(getattr(transport, name, 0)) is not int or getattr(transport, name, 0) != 1
                   for name in ('cinematic_widget_animation_protocol', 'owned_audio_cleanup_protocol')):
                raise RuntimeError('Verified native title-animation and audio cleanup are required for playback')
            self._prepare_step('play_unlock', self._verify_unlock, self.profile.definition)
            if self.panel_provider() is not self.panel or self.panel.state != 'open' or self.panel.uncertain:
                raise RuntimeError('Replay context changed before playback')
            self.evidence['before_play'] = self.adapters.status()
            if self.presentation is not None:
                self.presentation.suspend()
            self.sequence.play()
            self.state = 'starting'
            self._started = self.clock()
            self._deadline = self._started + 180.
        except BaseException as error:
            self._fail(error, 'play')
            raise
        return self.status()

    def status(self):
        """Cached status: no hidden blocking calls from menu rendering."""
        self._capture_cleanup_diagnostics()
        return dict(state=self.state, error=self.error, cleanup_error=self.cleanup_error, evidence=dict(self.evidence),
                    active=self.sequence is not None or self.adapters is not None or self.presentation is not None,
                    presentation=getattr(self.presentation, 'state', None),
                    live_playback_verified=False,
                    camera_restoration='requires live before/after evidence',
                    input_restoration='owned menu lifecycle; requires live verification')

    def poll(self):
        """One bounded sample per interval, never a busy wait or sleep loop."""
        if (self.sequence is None and self.adapters is None and self.presentation is None) or self.clock() < self._next_poll:
            return self.status()
        now = self.clock()
        self._next_poll = now + .1
        if self.state == 'cleanup_pending' and self._cleanup_deadline is None:
            # Unknown teardown permits no further calls into engine resources.
            return self.status()
        if self.state == 'cleanup_pending' and self._cleanup_deadline is not None:
            # A proven native deferral grants close-only retries, never playback
            # or general status invocations on an already stopped player.
            if now >= self._cleanup_deadline:
                error = RuntimeError('Deferred cinematic cleanup exceeded its five-second retry window')
                self.error = self.error or repr(error)
                self.cleanup_error = repr(error)
                self._cleanup_deadline = None
                self.evidence['cleanup_failure'] = dict(type=type(error).__name__, message=str(error), reason='timeout')
                self._log_failed_status()
                raise error
            return self.stop(reason=self.evidence.get('cleanup_reason', 'stopped'))
        self.evidence['poll_stage'] = 'context'
        try:
            # Recreated panels after travel cannot inherit this replay.
            if self.panel_provider() is not self.panel or self.panel.state != 'open' or self.panel.uncertain:
                self.stop(reason='context_closed')
            elif now >= self._deadline:
                self.error = 'Replay exceeded the bounded 180-second candidate window'
                self.stop(reason='timed_out')
            elif self._owner_status() != 'armed':
                self.stop(reason='native_closed')
            else:
                self.evidence['poll_stage'] = 'sequence_status'
                sample = self.sequence.status()
                self.evidence['sequence'] = sample
                self.evidence['poll_stage'] = 'adapter_status'
                self.evidence['adapters'] = self.adapters.status()
                self.evidence['poll_stage'] = 'sample_complete'
                if self.evidence.get('last_logged_sequence') != sample:
                    LOG.info('Cinematic playback observation: %s', json.dumps(dict(
                        sequence=sample, adapters=self.evidence['adapters']), default=repr))
                    self.evidence['last_logged_sequence'] = dict(sample)
                if sample.get('playing'):
                    self._observed_playing = True
                    self.state = 'playing'
                elif sample.get('paused'):
                    self.state = 'paused'
                elif self._observed_playing:
                    # This means engine playback stopped, not visual acceptance.
                    self.stop(reason='ended')
                elif self.state != 'armed' and now - self._started >= 3.:
                    self.error = 'Engine playback was never observed running'
                    self.stop(reason='not_observed')
        except BaseException as error:
            self._fail(error, 'poll')
            raise
        return self.status()

    def stop(self, *, reason='stopped'):
        # If native sequence cleanup defers/fails, keep both Python owners.
        # Releasing adapter leases at that point could invalidate active routes.
        self.state = 'stopping'
        try:
            if self.sequence is not None:
                self.sequence.close()
                self._capture_cleanup_diagnostics()
                self.sequence = None
            if self.adapters is not None:
                self.adapters.close()
                self.adapters = None
            if self.presentation is not None:
                # Keep visuals/input gated while native cleanup defers. A
                # failed restore remains an active owner even with no player.
                self.presentation.restore()
                self.evidence['presentation_restored'] = True
                self.presentation = None
        except SequenceCleanupDeferred:
            self.state = 'cleanup_pending'
            if self._cleanup_deadline is None:
                self._cleanup_deadline = self.clock() + 5.
            self.evidence['cleanup_reason'] = reason
            self.evidence['cleanup_deferred'] = self.evidence.get('cleanup_deferred', 0) + 1
            return self.status()
        except BaseException as error:
            self.state = 'cleanup_pending'
            self._cleanup_deadline = None
            self.cleanup_error = repr(error)
            self.evidence['cleanup_failure'] = dict(type=type(error).__name__, message=str(error), reason=reason)
            LOG.error('Cinematic cleanup failed: %s', self.cleanup_error,
                      exc_info=(type(error), error, error.__traceback__))
            self._log_failed_status()
            raise
        self.panel = None
        self._cleanup_deadline = None
        self.state = reason
        return self.status()

    close = stop

    def _capture_cleanup_diagnostics(self):
        owner = getattr(self.sequence, 'owner', None)
        diagnostics = getattr(owner, 'cleanup_diagnostics', None)
        if isinstance(diagnostics, dict):
            self.evidence['native_audio_cleanup'] = dict(diagnostics)

    def _owner_status(self):
        self.evidence['poll_stage'] = 'sequence_owner_status'
        return self.sequence.owner.status()

    def _log_failed_status(self):
        # Existing FileHandler persists this before ModLoader reduces exceptions
        # to strings. Cached observations only: no calls into an aborted session.
        LOG.error('Cinematic failed status: %s', json.dumps(self.status(), default=repr))

    def _fail(self, error, phase):
        # start(play=True) delegates to play(); preserve the first failure and do
        # not retry cleanup merely because the same exception crosses that layer.
        if self._failure_exception is error:
            return
        self._failure_exception = error
        self.error = repr(error)
        self.evidence['failure'] = dict(phase=phase, type=type(error).__name__, message=str(error),
            sequence_state=getattr(self.sequence, 'state', None),
            sequence_owner_state=getattr(getattr(self.sequence, 'owner', None), 'state', None))
        LOG.error('Cinematic %s failed: %s', phase, self.error,
                  exc_info=(type(error), error, error.__traceback__))
        try:
            self.stop(reason='failed')
        except BaseException:
            # stop recorded the independent cleanup error. Caller re-raises the
            # original exception, which retains its original traceback and type.
            pass
        self._log_failed_status()
