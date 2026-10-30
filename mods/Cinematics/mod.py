"""Cinematics v2: catalog UI and explicit owner-scoped replay routing."""
from dataclasses import asdict
from contextlib import nullcontext
from pathlib import Path
import logging
import time

from expedition33.management import Action, Keybind, ModDefinition, Option, ManagementError
from expedition33.paths import game_root
from expedition33._reader import shared_operation
from expedition33.cinematics.history import read_current_history, observation_error_reason
from expedition33.cinematics.original_game_action import controller_context, profiles as original_profiles, available as original_available
from expedition33.cinematics.title_replay import DEFINITION, SEQUENCE, SAVE_ID
from expedition33.cinematics.title_profiles import TITLE_PROFILES, PROLOGUE
from expedition33.cinematics.media_profiles import MEDIA_PROFILES
from expedition33.cinematics.library import (CatalogStore, PREVIEW_PROFILES, catalog_scenes,
    installed_cinematics, exact_title, preview_available, protocol, title_available as _title_available)
from expedition33.cinematics.browser_view import BrowserView, WorkspaceBrowserView, availability_label, menu_scene_label
from expedition33.cinematics.controller import (ReplayController, ControllerState, StartResult,
    ReplayBusy)
from expedition33.cinematics.adapters import TitleAdapter, MediaAdapter, PreviewAdapter, OriginalActionAdapter
from expedition33.cinematics.movie_clips import installed_movie_clips
from expedition33.cinematics.portable import PortableSceneAdapter, available as portable_available

LOG = logging.getLogger('expedition33.cinematics')
TITLE_PROTOCOLS = PROLOGUE.required_protocols


def title_available(transport, definition=DEFINITION):
    return _title_available(transport, definition)


def _epoch(context):
    return tuple(context['world']), tuple(context['controller'])


class AdmittedReplay:
    """Recheck selection, slot and current catalog before any backend allocation."""
    def __init__(self, admit, factory, *, requested_at=None):
        self.admit, self.factory, self.inner = admit, factory, None
        self.requested_at=requested_at

    def start(self):
        started=time.perf_counter()
        try:
            scene = self.admit()
        except Exception:
            # Admission is read-only and precedes backend allocation. Its
            # rejection is known, not an uncertain native playback attempt.
            LOG.exception('Cinematic admission rejected')
            return StartResult.REJECTED
        self.inner = self.factory(scene)
        admitted=time.perf_counter()
        result=self.inner.start()
        LOG.info('Cinematic request timings: queue_wait_ms=%.1f admission_ms=%.1f backend_ms=%.1f request_to_dispatch_ms=%.1f result=%s',
                 (started-self.requested_at)*1000 if self.requested_at is not None else 0.,
                 (admitted-started)*1000,(time.perf_counter()-admitted)*1000,
                 (time.perf_counter()-(self.requested_at if self.requested_at is not None else started))*1000,result.value)
        return result

    def poll(self):
        return self.inner.poll()

    def status(self):
        if self.inner is None:
            from expedition33.cinematics.controller import ReplayObservation, BackendState
            return ReplayObservation(BackendState.FAILED, 'Admission failed before native preparation')
        return self.inner.status()

    def stop(self):
        from expedition33.cinematics.controller import StopResult
        return self.inner.stop() if self.inner is not None else StopResult.STOPPED

    def close(self, request):
        return self.inner.close(request) if self.inner is not None else True


class Mod:
    def __init__(self, *, installation=None):
        self.session = self.native = self.pause = None
        self.controller = ReplayController()
        self.library = ()
        self.discovery = {'state': 'not_scanned', 'confirmed': [], 'all': []}
        self.reason = 'The cinematic library is prepared from local files before gameplay.'
        self.playback_status = 'Idle'
        self.show_all, self.filter = True, 'all'
        self.allow_original_actions = False
        self._installation = Path(installation) if installation is not None else None
        self._catalog_store = None
        self._catalog_store_paths = None
        self.static_preparation_error = None
        self._pending_refresh = False
        self._pending_open = False
        self._want_stop = False
        self._detaching_browser = False
        self._route = None
        self._last_epoch = None
        self._context = None
        self._slot = None
        self._retirement_token = None
        self._revoked = False
        self._next_playback_poll = 0.
        self._portable_panel_pool = None
        self._history_selectors = None
        self.poll_urgent = False
        self._requested_at = self._dispatch_entered_at = None
        self._dispatch_phases = {}
        self._dispatch_reader = None

    def management(self):
        return ModDefinition('sdk.cinematics', 'Cinematics', version='0.2.4-dispatch',
            description='Browse the original cinematic library and use explicitly supported replay routes.',
            options=(Option('original_story_actions', 'Allow original-map story actions (save/progression effects)',
                            'bool', False, on_change=self._set_original_actions),),
            actions=(Action('open', 'Open Cinematics', self.open),
                     Action('stop', 'Stop owned replay', self.request_stop),
                     Action('refresh', 'Refresh cinematic history', self.discover),
                     Action('status', 'Cinematic status', self.status)),
            keybinds=(Keybind('open', 'Open Cinematics', None, self.open),
                      Keybind('stop', 'Stop owned replay', None, self.request_stop)))

    def _set_original_actions(self, value):
        if type(value) is not bool:
            raise ManagementError('Original story playback requires an explicit Boolean setting')
        self.allow_original_actions = value
        self._pending_refresh = True

    def _catalog_inputs(self):
        root = self._installation or game_root()
        paths = Path(__file__).with_name('catalog.json'), root / 'Manifest_UFSFiles_Win64.txt'
        if paths != self._catalog_store_paths:
            self._catalog_store, self._catalog_store_paths = CatalogStore(*paths), paths
        return self._catalog_store.read()

    def prepare_startup(self, context):
        try:
            catalog, manifest = self._catalog_inputs()
            self.library = tuple(catalog_scenes({}, False, catalog, manifest,
                                                gameplay_world_available=False))
            self.library += tuple(installed_movie_clips(manifest))
            self.discovery = {'state': 'catalog_ready', 'all': list(self.library), 'confirmed': [],
                              'definition_catalog_complete': True}
            self.static_preparation_error = None
        except (OSError, UnicodeError, ValueError, KeyError, RuntimeError) as error:
            self.static_preparation_error = str(error)
            self.reason = 'Library preparation: ' + str(error)

    def enable(self, session):
        from expedition33._reader import active_reader
        started=time.perf_counter()
        # Share one read worker across anchor, history and pool adoption. The
        # observations stay fresh; repeated process handshakes do not.
        loading=getattr(self,'_loading_replay',None)
        reader=getattr(loading,'reader',None)
        operation=(reader.bind() if reader is not None and active_reader() is None
                   else shared_operation(session.pid,_executable=session._session._transport._executable))
        with operation:
            self._enable(session)
        LOG.info('Cinematics activation ready in %.1f ms (loading pool=%s)',
                 (time.perf_counter()-started)*1000,getattr(self,'_loading_replay',None) is not None)

    def _enable(self, session):
        from expedition33.pause_menu import PauseMenuEntry
        self.session = session
        self.controller.enable()
        self._revoked = False
        shared = getattr(session._session, '_native_menu_service', None)
        if shared is None:
            raise RuntimeError('Cinematics requires SDK Management')
        self.native = shared.for_view(lambda registry: WorkspaceBrowserView(registry, self))
        self.pause = PauseMenuEntry(session, self.native, label='Cinematics')
        self._pending_refresh = True
        session.actions.register('cinematics.status', self.status, mutates=False)
        session.actions.register('cinematics.discover', self.discover, mutates=False)
        session.console.register('cinematics', self.command, owner=self)
        loading=getattr(self,'_loading_replay',None)
        prepared_pool=loading.take(session) if loading is not None else None
        if prepared_pool is not None and loading.pause is not None:
            if loading.pause.state!='attached':raise RuntimeError('Cinematic loading pause entry is not ready')
            self.pause=loading.pause
        self._controller_anchor=None
        if prepared_pool is not None:
            from expedition33.cinematics.controller_anchor import for_scope
            self._controller_anchor=for_scope(prepared_pool.scope)
            self._history_selectors=loading.history
        capability=getattr(session._session._transport,'stable_lease_protocol',0)
        if prepared_pool is None and type(capability) is int and capability==1:
            from expedition33.cinematics.controller_anchor import for_scope
            for_scope(session)
            from expedition33.cinematics.history import PreparedHistorySelectors
            self._history_selectors=PreparedHistorySelectors(session)
        if portable_available(session._session._transport):
            from expedition33._cinematic_panel_pool import CinematicPanelPool
            self._portable_panel_pool=prepared_pool
            if self._portable_panel_pool is None:
                self._portable_panel_pool=CinematicPanelPool(session)
                self._portable_panel_pool.prepare()
            from expedition33._reader import ReadBatch
            self._dispatch_reader=loading.take_reader() if prepared_pool is not None else None
            if self._dispatch_reader is None:self._dispatch_reader=ReadBatch(session.pid,share=True,_executable=session._session._transport._executable)
            self._dispatch_reader.warm()

    def prepare_loading_ui(self,session):
        from .loading import LoadingReplay
        return LoadingReplay(self,session)

    def prepare_loading_pause(self,scope):
        from expedition33.pause_menu import PauseMenuEntry
        shared=scope._session._native_menu_service
        native=shared.for_view(lambda registry:WorkspaceBrowserView(registry,self))
        return PauseMenuEntry(scope,native,label='Cinematics',readiness=lambda:True)

    def startup_ready(self):
        return self.session is not None and self.native is not None

    def discover(self, _=None):
        self._pending_refresh = True
        return self.status()

    def _refresh_now(self):
        self.session._check()
        self._pending_refresh = False
        self._context, self._last_epoch, self._slot = None, None, None
        history, current = {}, {}
        try:
            with shared_operation(self.session.pid,
                           _executable=self.session._session._transport._executable):
                context = self._context_now()
                current = (read_current_history(self.session,prepared=self._history_selectors)
                           if self._history_selectors is not None else read_current_history(self.session))
            if tuple(current['context_identities']['world']) != tuple(context['world']):
                raise ManagementError('History belongs to another world')
            history = dict(current.pop('history').items)
            self._context, self._last_epoch = context, _epoch(context)
            self._slot = current['selected_slot']
            error = None
        except Exception as failure:
            LOG.exception('Cinematics current-history observation failed')
            error = observation_error_reason(failure)
        transport = self.session._session._transport
        try:
            catalog, manifest = self._catalog_inputs()
            self.library = tuple(catalog_scenes(history,
                protocol(transport, 'media_owner_protocol'), catalog, manifest,
                title_profile_ids=tuple(p.profile_id for p in TITLE_PROFILES.values() if p.available(transport)),
                original_action_available=original_available(transport),
                allow_original_actions=self.allow_original_actions,
                owned_preview_available=preview_available(transport),
                portable_scene_available=portable_available(transport),
                gameplay_world_available=self._context is not None,
                current_world_path=self._context['world_path'] if self._context else None))
            self.library += tuple(installed_movie_clips(manifest,
                available=protocol(transport, 'media_owner_protocol') and
                          protocol(transport, 'media_retirement_protocol'),
                gameplay=self._context is not None))
            catalog_error = None
        except (OSError, UnicodeError, ValueError, KeyError, RuntimeError) as failure:
            self.library = tuple(dict(id=name, title=name, saved_id=name, unlocked=value,
                supported=False, reason='No verified catalog mapping', replay_kind=None, controls=())
                for name, value in history.items())
            catalog_error = str(failure)
        confirmed = [dict(row) for row in self.library if row.get('unlocked') is True]
        self.discovery = dict(current, state='history_verified' if error is None else 'history_unavailable',
            all=[dict(row) for row in self.library], confirmed=confirmed, error=error, catalog_error=catalog_error,
            definition_catalog_complete=catalog_error is None)
        self.reason = (f'{len(self.library)} library entries; {len(confirmed)} unlocked in current-session history. '
                       'Availability and visual qualification are listed separately.')
        if error:
            self.reason += ' History unavailable: ' + error
        if catalog_error:
            self.reason += ' Catalog unavailable: ' + catalog_error
        return self.discovery

    def open(self, _=None):
        self._pending_open = True
        return 'Opening Cinematics'

    def request_stop(self, _=None):
        self._want_stop = True
        self.poll_urgent = True
        return 'Stopping owned replay'

    def stop(self):
        if self._detaching_browser:
            return True
        if not self.controller.status().busy:
            return True
        self._want_stop = True
        return False

    def _current_epoch(self):
        if self._revoked:
            return ('retired', self.controller.status().generation)
        with shared_operation(self.session.pid,
                       _executable=self.session._session._transport._executable):
            return _epoch(self._context_now())

    def _context_now(self):
        if getattr(self,'_controller_anchor',None) is not None:return self._controller_anchor.context()
        capability=getattr(self.session._session._transport,'stable_lease_protocol',0)
        if type(capability) is int and capability==1:
            from expedition33.cinematics.controller_anchor import for_scope
            return for_scope(self.session).context()
        return controller_context(self.session,project=True)

    def _menu(self):
        menu = self.native.menu if self.native else None
        if menu is None or menu.panel.state != 'open' or menu.panel.uncertain:
            raise ManagementError('The cinematic browser is not attached to the current context')
        return menu

    def _admit(self, scene_id, token, expected_slot, expected_epoch, signature):
        fresh = self._refresh_now()
        if self._slot != expected_slot or self._last_epoch != expected_epoch:
            raise ManagementError('Save slot or world changed after cinematic selection')
        row = next((s for s in self.library if s['id'] == scene_id), None)
        if row is None or (row.get('definition_sha256'), row.get('sequence')) != signature:
            raise ManagementError('Cinematic definition changed after selection')
        self._check_route(row, token)
        return dict(row)

    @staticmethod
    def _check_route(scene, token):
        if token == 13:
            admitted = scene.get('original_supported') is True
        elif token == 14:
            admitted = scene.get('portable_supported') is True and scene.get('unlocked') is True
        elif token == 11:
            admitted = scene.get('preview_supported') is True and scene.get('unlocked') is True
        elif token == 1 and scene.get('replay_kind') in ('preview', 'original_action'):
            admitted = scene.get('original_supported') is True
        elif token == 1 and scene.get('replay_kind') == 'movie_clip':
            admitted = scene.get('supported') is True
        else:
            admitted = (token == 1 and scene.get('replay_kind') in ('title', 'movie') and
                        scene.get('supported') is True and scene.get('unlocked') is True)
        if not admitted:
            raise ManagementError('This cinematic route is unavailable; refresh the library for details')

    def control(self, scene_id, token):
        if token == 4:
            self.request_stop()
            return
        if token not in (1, 11, 13, 14):
            raise ManagementError('This replay route supports only Play and Stop')
        if self.controller.status().busy:
            raise ManagementError('Finish the current replay cleanup before starting another')
        row = next((s for s in self.library if s['id'] == scene_id), None)
        if row is None:
            raise ManagementError('Cinematic selection is no longer available')
        self._check_route(row, token)
        if self._last_epoch is None or self._slot is None:
            raise ManagementError('A loaded save is required for cinematic playback')
        kind = ('portable' if token == 14 else 'preview' if token == 11 else 'original_action'
                if token == 13 or row['replay_kind'] in ('preview', 'original_action') else row['replay_kind'])
        expected_slot, expected_epoch = self._slot, self._last_epoch
        signature = row.get('definition_sha256'), row.get('sequence')
        def factory(scene):
            if kind == 'title':
                return TitleAdapter(self.session, scene, self._menu, self._refresh_now)
            if kind in ('movie', 'movie_clip'):
                return MediaAdapter(self.session, scene, self._menu, self._refresh_now, self.request_stop)
            if kind == 'preview':
                return PreviewAdapter(self.session, scene)
            if kind == 'portable':
                return PortableSceneAdapter(self.session,scene,panel_pool=self._portable_panel_pool)
            return OriginalActionAdapter(self.session, scene, original_profiles()[scene_id])
        requested_at=time.perf_counter()
        self._requested_at=requested_at;self._dispatch_phases={}
        self.controller.queue(scene_id, lambda: AdmittedReplay(
            lambda: self._admit(scene_id, token, expected_slot, expected_epoch, signature), factory,requested_at=requested_at),
            expected_epoch, engine_owned=kind == 'original_action')
        self._want_stop = False
        self._route = kind
        self.playback_status = 'Queued: ' + row['title']
        self.poll_urgent = True

    def command(self, arguments):
        command = arguments.strip().split(maxsplit=1)
        verb = command[0].casefold() if command else 'open'
        if verb == 'open':
            return self.open()
        if verb == 'stop':
            return self.request_stop()
        if verb == 'refresh':
            return self.discover()
        if verb == 'status':
            return self.status()
        if verb == 'search' and len(command) == 2:
            menu = self._menu()
            menu.view.search(command[1])
            self.native.parent.refresh()
            return 'Cinematic search updated'
        raise ManagementError('Use cinematics open | stop | refresh | status | search TEXT')

    def poll(self):
        if self.session is None or self._revoked:
            return
        playback=self.controller.status()
        if playback.busy and (playback.state is ControllerState.QUEUED or self._want_stop or self._pending_open):
            # An accepted play/stop intent precedes routine menu maintenance.
            # Admission, browser detachment and epoch checks still run below
            # in the normal playback path, on this same owner thread.
            if self._pending_open:self._want_stop=True
            self._advance_playback()
            return
        if self._pending_refresh and not self.controller.status().busy:
            self._refresh_now()
            menu = self.native.menu if self.native else None
            view = getattr(menu, 'view', None)
            if (isinstance(view, BrowserView) and view.model is self and
                    menu.panel.state == 'open' and not getattr(menu, '_presentation_suspended', False)):
                view.status = ('Current-save discovery refreshed' if not self.discovery.get('error')
                               else 'Current-save history unavailable')
                self.native.parent.refresh()
        if self.pause is not None:
            self.pause.poll()
        if self.native is not None:
            self.native.poll()
        if self._pending_open:
            if self.controller.status().busy:
                self._want_stop = True
            else:
                active = self.native.menu
                if active is not None and active.panel.state == 'open':
                    self._pending_open = False
                else:
                    previous = getattr(self.native.parent, 'menu', None)
                    if previous is not None and previous.panel.state == 'open':
                        self.native.parent.close_menu()
                    if previous is None or previous.panel.state != 'open':
                        self.native.open()
                        self._pending_open = False
        self._advance_playback()

    def _advance_playback(self):
        now = time.monotonic();playback=self.controller.status()
        urgent=playback.state is ControllerState.QUEUED or self._want_stop
        if not playback.busy or (not urgent and now < self._next_playback_poll):
            return
        self._next_playback_poll = now + .2
        if playback.state is ControllerState.QUEUED:
            self._dispatch_entered_at=time.perf_counter()
            requested=getattr(self,'_requested_at',None)
            self._dispatch_phases={'queue_wait_ms':(self._dispatch_entered_at-requested)*1000 if requested is not None else 0.}
        try:
            # One short-lived worker spans context, fresh admission and native
            # preparation. Runtime observations are still read on every step.
            queued_portable=(self.controller.status().state is ControllerState.QUEUED and self._route=='portable')
            from expedition33._reader import active_reader
            reader=getattr(self,'_dispatch_reader',None)
            operation=(reader.bind() if queued_portable and reader is not None and active_reader() is None else
                       shared_operation(self.session.pid,_executable=self.session._session._transport._executable)
                       if queued_portable else nullcontext())
            with operation:self._poll_playback()
        except Exception as error:
            if self.controller.status().state is ControllerState.QUEUED:
                # No backend exists yet. Cancel a failed worker/context setup
                # rather than leaving an intent queued forever or retrying IO.
                self.controller.request_stop(None)
            self.playback_status = 'Cinematic lifecycle error: ' + str(error)
            LOG.exception('Cinematic lifecycle error')

    def _poll_playback(self):
        queued=self.controller.status().state is ControllerState.QUEUED
        entered=time.perf_counter()
        current = self._current_epoch()
        context_ready=time.perf_counter()
        if queued:
            phases=self._dispatch_phases
            phases['worker_ms']=(entered-(self._dispatch_entered_at or entered))*1000
            phases['context_ms']=(context_ready-entered)*1000
        previous = self.playback_status
        if self._want_stop:
            self.controller.request_stop(current)
            self._want_stop = False
            snapshot = self.controller.status()
            self.playback_status = ('Playback stopped' if not snapshot.busy
                                    else snapshot.detail or snapshot.state.value)
        else:
            if self.controller.status().state is ControllerState.QUEUED and self._route in ('portable','preview', 'original_action'):
                self._detaching_browser = True
                try:
                    self.native.parent.close_menu()
                finally:
                    self._detaching_browser = False
            if queued:self._dispatch_phases['browser_detach_ms']=(time.perf_counter()-context_ready)*1000
            snapshot = self.controller.poll(current, presentation_ready=True)
            self.playback_status = snapshot.detail or snapshot.state.value
        if previous != self.playback_status and self.native and self.native.menu:
            menu = self.native.menu
            view = getattr(menu, 'view', None)
            if isinstance(view, BrowserView) and view.model is self and menu.panel.state == 'open' and not getattr(menu, '_presentation_suspended', False):
                view.status = self.playback_status
                self.native.parent.refresh()

    def status(self, _=None):
        snapshot = asdict(self.controller.status())
        snapshot['state'] = snapshot['state'].value
        return dict(playback=snapshot, discovery=dict(self.discovery), reason=self.reason,
                    playback_supported=any(s.get('supported') or s.get('original_supported') for s in self.library),
                    catalog_count=len(self.library), original_story_actions=self.allow_original_actions,
                    static_preparation_error=self.static_preparation_error,
                    dispatch_phases=dict(self._dispatch_phases))

    def revoke_world(self, context):
        self._close_dispatch_reader()
        self._retirement_token = context.previous_token
        self._revoked = True
        self._pending_open = self._pending_refresh = False

    def begin_world_retirement(self, context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self, context):
        if context.previous_token != self._retirement_token:
            return 'unknown'
        self.controller.poll(('retired', self.controller.status().generation))
        if self.controller.status().busy:
            return 'pending'
        if self._portable_panel_pool is not None:
            result=self._portable_panel_pool.retire_world()
            if result!='ack':return result
            self._portable_panel_pool=None
        if self.pause is not None:
            result = self.pause.retire_world()
            if result != 'ack':
                return result
            self.pause = None
        self.native = self.session = None
        self._context = self._last_epoch = self._slot = None
        self.library = ()
        self.discovery = {'state': 'world_retired', 'all': [], 'confirmed': []}
        return 'ack'

    def disable(self):
        self._close_dispatch_reader()
        if not self.controller.close(self._current_epoch() if self.controller.status().busy else None):
            from expedition33._sequence_owner import SequenceCleanupDeferred
            raise SequenceCleanupDeferred('Cinematic cleanup is not yet acknowledged')
        if self._portable_panel_pool is not None:
            if not self._portable_panel_pool.close():
                from expedition33._sequence_owner import SequenceCleanupDeferred
                raise SequenceCleanupDeferred('Cinematic panel cleanup is not yet acknowledged')
            self._portable_panel_pool=None
        if self.native is not None:
            self.native.close()
            self.native = None
        if self.pause is not None:
            self.pause.close()
            self.pause = None
        self.session = None

    def _close_dispatch_reader(self):
        reader=getattr(self,'_dispatch_reader',None)
        if reader is not None:
            reader.close();self._dispatch_reader=None
