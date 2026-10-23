"""Cinematic browser with isolated adapters and mapped original game actions."""
import logging
import json
import hashlib
import time
from pathlib import Path
from expedition33.paths import game_root
from expedition33.catalog import capture_matching
from expedition33.values import read_values, read_object_reference, StoredMap
from expedition33._reader import ReadBatch
from expedition33.management import Action, ModDefinition, ManagementError
from expedition33.management_view import MenuControl, MenuFrame
from expedition33.pause_menu import PauseMenuEntry
from expedition33.cinematics.title_replay import DEFINITION, SEQUENCE, SAVE_ID
from expedition33.cinematics.title_profiles import TITLE_PROFILES, PROLOGUE
from expedition33.cinematics.media_profiles import MEDIA_PROFILES
from expedition33.cinematics.original_game_action import profiles as original_profiles, profile_matches, available as original_available, OriginalActionReplay

LOG = logging.getLogger('expedition33.cinematics')
TITLE_PROTOCOLS = PROLOGUE.required_protocols

# Representative live results recorded in research/CINEMATICS_COMPLETION.md.
LIVE_ORIGINAL_ACTIONS = frozenset((
    'Sandfall/Content/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro.uasset',
    'Sandfall/Content/Cinematics/Camp/Forced/LuneCampFairytales/DA_GA_CIN_LuneCampFairytales.uasset',
))


def availability_label(scene):
    if not scene.get('supported'):
        return 'Unavailable'
    if scene.get('validation') == 'live_partial':
        return 'Available - partial'
    if (scene.get('validation') == 'live_mechanism_verified' or
            (scene.get('replay_kind') == 'original_action' and scene.get('id') in LIVE_ORIGINAL_ACTIONS)):
        return 'Available - tested'
    return 'Available - unverified'


def menu_scene_label(scene):
    title = scene['title']
    for suffix in (' [unlocked]', ' [locked]', ' [unlock unknown]'):
        title = title.removesuffix(suffix)
    return f'[{availability_label(scene)}] {title}'


def title_available(transport, definition=DEFINITION):
    profile=TITLE_PROFILES.get(definition)
    return profile is not None and profile.available(transport)


def exact_title(scene):
    profile=TITLE_PROFILES.get(scene.get('id'))
    return profile is not None and profile.matches(scene)


def catalog_scenes(history, media_available, catalog, manifest_bytes, *, title_profile_ids=(), original_action_available=False):
    if catalog.get('version') != 1 or catalog.get('manifest_sha256') != hashlib.sha256(manifest_bytes).hexdigest():
        raise ValueError('Cinematic catalog does not match the installed manifest')
    scenes=[]; identities=set();actions=original_profiles() if original_action_available else {}
    for item in catalog['scenes']:
        identity=item['id']
        if identity in identities: raise ValueError('Duplicate cinematic definition')
        identities.add(identity)
        saved_id=item.get('saved_id')
        unlocked=history.get(saved_id) if saved_id else None
        if type(unlocked) is not bool: unlocked=None
        # Only independently verified exact adapters grant playback.
        media_profile=MEDIA_PROFILES.get(identity)
        mapped=media_profile is not None and media_profile.matches(item)
        title_mapped=exact_title(item)
        original=actions.get(identity)
        original_mapped=original is not None and profile_matches(original,item) and not title_mapped
        if original_mapped:mapped=False
        supported=bool(unlocked is True and ((mapped and media_available) or (title_mapped and TITLE_PROFILES[identity].profile_id in title_profile_ids)))
        if original_mapped:supported=True
        title=media_profile.label if mapped else item['title']
        label='unlocked' if unlocked is True else 'locked' if unlocked is False else 'unlock unknown'
        reason=(f"Save ID: {saved_id}. " if saved_id else 'No verified saved unlock ID. ')
        reason+=('Reviewed isolated title adapter; per-scene live validation is reported separately. Play and Stop are supported; pause, restart and speed are unavailable.' if title_mapped else
                 media_profile.limitation if mapped else
                 'In-engine replay is not implemented for this definition. Playback is unavailable.')
        if title_mapped and TITLE_PROFILES[identity].validation == 'static_admitted_live_pending': reason+=' Live playback of this profile is not yet verified.'
        if mapped and media_profile.validation == 'static_mapping_live_pending': reason+=' Live playback of this segment is not yet verified.'
        if title_mapped and TITLE_PROFILES[identity].profile_id not in title_profile_ids: reason+=' Required native title/audio cleanup capabilities are unavailable.'
        if unlocked is not True: reason+=' This entry cannot be replayed without a verified current-save unlock.'
        if original_mapped:reason=f"Original game cinematic action. Play travels to {original['exact_map']}, restores the native spawn and starts the action. Experimental per-scene playback; Stop is not yet available. Game story transitions may run."
        scenes.append(dict(id=identity,saved_id=saved_id,title=title+f' [{label}]',
            supported=supported,unlocked=unlocked,reason=reason,sequence=item.get('sequence'),
            definition_sha256=item.get('sha256'), title_profile=TITLE_PROFILES[identity].profile_id if title_mapped else None,
            media_profile=identity if mapped else None, full_scene=False if mapped else None, validation=media_profile.validation if mapped else TITLE_PROFILES[identity].validation if title_mapped else 'original_action_live_pending' if original_mapped else 'unsupported', replay_kind='title' if title_mapped else 'movie' if mapped else 'original_action' if original_mapped else None))
    return scenes


def installed_cinematics(lines):
    """Manifest candidates, never evidence of a save unlock or safe playback."""
    found = {}
    for line in lines:
        path = line.split('\t', 1)[0].replace('\\', '/')
        name = Path(path).stem
        if path.startswith('Sandfall/Content/Movies/CS_') and path.endswith('.mp4'):
            kind, prefix = 'Video', 'CS_'
        elif path.startswith('Sandfall/Content/') and name.startswith('DA_GA_CIN_') and path.endswith('.uasset'):
            kind, prefix = 'Cinematic entry', 'DA_GA_CIN_'
        else:
            continue
        title = name.removeprefix(prefix).replace('_', ' ')
        found.setdefault(path.casefold(), dict(id=path, title=f'{title} [{kind}; unlock unknown]',
            supported=False, unlocked=None,
            reason=f'Installed {kind.lower()}. Its saved cinematic ID is not mapped yet; '
                   'unlock status and isolated playback remain unverified. Showing all does not unlock it.'))
    return sorted(found.values(), key=lambda scene: (scene['title'].casefold(), scene['id']))


class BrowserView:
    def __init__(self, registry, model):
        self.registry, self.model = registry, model
        self.closed = False
        self.revision = 0
        self.status = ''
        self.page = 0
        self.selected = None

    def scenes(self):
        key = 'all' if self.model.show_all else 'confirmed'
        return self.model.discovery.get(key, [])

    def render(self):
        self.registry._check()
        if self.closed:
            raise ManagementError('Cinematics browser is closed')
        self.revision += 1
        controls = [MenuControl(0, 'Refresh current-save history')]
        controls.append(MenuControl(10, 'Show: All cinematics' if self.model.show_all else 'Show: Unlocked only'))
        # Original-action routes use the latest user-authorized history override;
        # isolated title/media routes retain their current-history requirements.
        scenes = self.scenes()
        pages = max(1, (len(scenes) + 5) // 6)
        self.page = min(self.page, pages - 1)
        available = sum(bool(scene.get('supported')) for scene in scenes)
        description = (f'{available} of {len(scenes)} listed cinematics available to Play.\n'
                       'Tested = observed in-game; unverified = enabled but not individually tested; '
                       'partial = only part of the cinematic. Unlock history is separate from playback availability.\n\n'
                       + self.model.reason)
        if self.selected is None:
            controls.extend(MenuControl(100 + index, menu_scene_label(scene)) for index, scene in
                            enumerate(scenes) if self.page * 6 <= index < (self.page + 1) * 6)
            controls.extend((MenuControl(7, 'Previous', self.page > 0),
                             MenuControl(8, 'Next', self.page + 1 < pages)))
        else:
            scene = next((s for s in scenes if s['id'] == self.selected), None)
            if scene is None:
                self.selected = None
                return self.render()
            description = availability_label(scene) + '\n' + scene['title'] + '\n' + scene['id'] + '\n\n' + scene['reason']
            controls.extend(MenuControl(token, label, bool(scene.get('supported')))
                for token, label in (((1,'Travel and Play'),) if scene.get('replay_kind')=='original_action' else ((1, 'Play'), (4, 'Stop')) if scene.get('replay_kind') in ('title','movie') else
                    ((1, 'Play'), (2, 'Pause / Resume'), (3, 'Restart'), (4, 'Stop'), (5, 'Playback speed'))))
            controls.append(MenuControl(9, 'Back to cinematics'))
        controls.append(MenuControl(6, 'Close'))
        return MenuFrame(self.revision, 'Cinematics', description,
                         tuple(controls), self.page, pages,
                         self.model.playback_status if self.selected in TITLE_PROFILES or self.selected in MEDIA_PROFILES else self.status, False)

    def activate(self, revision, token, **_):
        self.registry._check()
        if self.closed or revision != self.revision:
            raise ManagementError('Stale cinematic control')
        scenes = self.scenes()
        if token == 10:
            self.model.show_all = not self.model.show_all
            self.selected, self.page = None, 0
            return self.render()
        if token >= 100 and self.selected is None and self.page * 6 <= token - 100 < min(len(scenes), (self.page + 1) * 6):
            self.selected = scenes[token - 100]['id']
            return self.render()
        if token in (7, 8) and self.selected is None:
            new_page = self.page + (-1 if token == 7 else 1)
            if not 0 <= new_page < max(1, (len(scenes) + 5) // 6):
                raise ManagementError('Cinematic page is unavailable')
            self.page = new_page
            return self.render()
        if token == 9 and self.selected is not None:
            if hasattr(self.model,'stop') and self.model.stop() is False:
                self.status = 'Finishing cinematic cleanup'
                return self.render()
            self.selected = None
            return self.render()
        if token in range(1,6) and self.selected is not None:
            scene = next((s for s in scenes if s['id']==self.selected),None)
            if not scene or not scene.get('supported') or (scene.get('replay_kind')!='original_action' and not scene.get('unlocked')):
                raise ManagementError('This cinematic has no verified playback mapping')
            if scene.get('replay_kind') in ('title','movie') and token not in (1, 4):
                raise ManagementError('Reviewed replay supports only Play and Stop')
            self.model.control(self.selected,token)
            if self.closed:return MenuFrame(self.revision,'Cinematics','',(),0,1,'Traveling to cinematic',True)
            self.status = self.model.playback_status
            return self.render()
        if token not in (0, 6):
            raise ManagementError('Replay is unavailable: isolation has not been verified')
        self.revision += 1
        if token == 6:
            self.close()
            return MenuFrame(self.revision, 'Cinematics', '', (), 0, 1, '', True)
        self.model.discover()
        self.status = 'Current-save discovery refreshed'
        return self.render()

    def close(self):
        # Travel disposes the old menu tree. The original game action owns its
        # playback independently; disposing this view must not try to stop it.
        original=getattr(self.model,'original_replay',None)
        game_owned=original is not None and original.status().get('active') is True
        if not game_owned and hasattr(self.model,'stop') and self.model.stop() is False:
            raise ManagementError('Cinematic cleanup is still finishing; close again when it completes')
        self.closed = True
        self.revision += 1


class Mod:
    def __init__(self):
        self.session = self.native = self.pause = None
        self.reason = 'Current-save cinematic history has not been read.'
        self.discovery = {'state': 'not_scanned', 'confirmed': []}
        self.show_all = True
        self.video = None
        self.title_replay = None
        self.original_replay = None
        self.playback_status = 'Stopped'
        self._next_media_poll = 0.
        self._opening_deadline = 0.
        self._play_started = False
        self._paused = False
        self._rate = 1.
        self._static_catalog_inputs=None
        self.static_preparation_error=None

    def management(self):
        return ModDefinition('sdk.cinematics', 'Cinematics', version='0.1-browser',
            description='Mapped original cinematic travel/play plus isolated title and video adapters. Save history is shown separately.',
            actions=(Action('status', 'Cinematic discovery status', self.status),
                     Action('refresh', 'Refresh current-save history', self.discover)))

    def prepare_startup(self, context):
        # Files/profile validation needs no process or world. A missing local
        # manifest must not prevent current-save history discovery later.
        try:self._catalog_inputs()
        except (OSError,UnicodeError,ValueError,KeyError,RuntimeError) as error:
            self.static_preparation_error=str(error)

    def _catalog_inputs(self):
        manifest=game_root() / 'Manifest_UFSFiles_Win64.txt'
        source=Path(__file__).with_name('catalog.json')
        signature=tuple((str(path),path.stat().st_mtime_ns,path.stat().st_size)
                        for path in (source,manifest))
        cached=self._static_catalog_inputs
        if cached is None or cached[0]!=signature:
            catalog=json.loads(source.read_text(encoding='utf8'))
            manifest_bytes=manifest.read_bytes()
            # Validate installed mapping, duplicates and exact static profiles
            # before publishing the cache. Current history is always read live.
            catalog_scenes({},False,catalog,manifest_bytes,original_action_available=True)
            self._static_catalog_inputs=(signature,catalog,manifest_bytes)
            self.static_preparation_error=None
        return self._static_catalog_inputs[1:]

    def enable(self, session):
        self.session = session
        self.discover()
        shared = getattr(session._session, '_native_menu_service', None)
        if shared is None:
            raise RuntimeError('Enable SDK Management before Cinematics')
        self.native = shared.for_view(lambda registry: BrowserView(registry, self))
        self.pause = PauseMenuEntry(session, self.native, label='Cinematics')
        session.actions.register('cinematics.status', self.status, mutates=False)
        session.actions.register('cinematics.discover', self.discover, mutates=False)
        session.console.expose('cinematics', self)

    def discover(self, _=None):
        self.discovery = {'state': 'unavailable', 'confirmed': []}
        try:
            with ReadBatch(self.session.pid):
                from expedition33.cinematics.history import read_current_history
                current = read_current_history(self.session)
                history = current.pop('history')
                self.discovery.update(current)
                self.discovery['state'] = 'history_verified'
                self.discovery['confirmed'] = [dict(id=name, title=name.replace('CS_', '').replace('_', ' '),
                    supported=False, unlocked=True, reason='Seen in current-session game history. Replay disabled: asset mapping and isolated playback have not been verified.')
                    for name, seen in history.items.items() if seen is True]
                transport = getattr(getattr(self.session,'_session',None),'_transport',None)
                # Current game history and the installed catalog have independent failure
                # modes: a missing manifest must not discard verified history.
                all_scenes = list(self.discovery['confirmed'])
                all_scenes.extend(dict(id=name, title=name.replace('CS_', '').replace('_', ' ') + ' [locked]',
                    supported=False, unlocked=False, reason='Not unlocked in current-session game history. Replay is disabled.')
                    for name, seen in history.items.items() if seen is False)
                try:
                    catalog,manifest_bytes=self._catalog_inputs()
                    all_scenes=catalog_scenes(history.items,
                        type(getattr(transport,'media_owner_protocol',0)) is int and transport.media_owner_protocol==1,
                        catalog,manifest_bytes, title_profile_ids=tuple(p.profile_id for p in TITLE_PROFILES.values() if p.available(transport)),original_action_available=original_available(transport))
                    mapped_ids={s['saved_id'] for s in all_scenes}
                    self.discovery['unmapped_history']=[s for s in self.discovery['confirmed'] if s['id'] not in mapped_ids]
                    self.discovery['confirmed']=[s for s in all_scenes if s['unlocked'] is True]
                    self.discovery['definition_catalog_complete']=True
                except (OSError, UnicodeError, ValueError, KeyError) as error:
                    self.discovery['catalog_error'] = str(error)
                self.discovery['all'] = all_scenes
                self.discovery['catalog_complete'] = False
                self.reason = (f"{len(all_scenes)} installed cinematic definitions. "
                    f"{len(self.discovery['confirmed'])} entries are unlocked in current-session game history.\n\n"
                    'This is the active game history, not a persisted save snapshot. '
                    'Select a scene for playback availability. Most scenes require in-engine replay support. '
                    'Unlock unknown does not mean unlocked. Related definitions can share a saved ID.')
        except Exception as error:
            self.reason = 'Cinematic history is unavailable. ' + str(error)
            self.discovery['error'] = str(error)
            # Original action travel was explicitly authorized independently of
            # history. Exact installed catalog/map/runtime checks still apply.
            transport=getattr(getattr(self.session,'_session',None),'_transport',None)
            if original_available(transport):
                try:
                    catalog,manifest_bytes=self._catalog_inputs()
                    self.discovery['all']=catalog_scenes({},False,catalog,manifest_bytes,original_action_available=True)
                except (OSError,UnicodeError,ValueError,KeyError) as catalog_error:self.discovery['catalog_error']=str(catalog_error)
        LOG.info('Cinematic discovery: %s', self.discovery)
        return self.status()

    def status(self, _=None):
        return dict(discovery=self.discovery, reason=self.reason,
                    pause_state=self.pause.state if self.pause else 'not_attached',
                    pause_error=self.pause.error if self.pause else None,
                    menu=self.native.status() if self.native else None,
                    playback_supported=any(s.get('supported') for s in self.discovery.get('confirmed',())),
                    playback=self.playback_status,
                    title_candidate=self.title_replay.status() if self.title_replay else None,
                    original_action=self.original_replay.status() if self.original_replay else None)

    def prepare_title(self, scene_id=DEFINITION):
        """Prepare the exact unlocked title; this candidate command never plays."""
        from expedition33.cinematics.title_replay import ExactTitleReplay
        from expedition33.cinematics.title_adapters import OwnedTitleAdapters
        from expedition33.cinematics.presentation import MenuPresentation
        if not title_available(self.session._session._transport, scene_id):
            raise ManagementError('Verified native title and audio cleanup capabilities are required')
        if self.video is not None:
            raise ManagementError('Stop the current movie first')
        profile = TITLE_PROFILES[scene_id]
        if self.title_replay is not None and self.title_replay.profile is not profile:
            if self.title_replay.status().get('active'):
                raise ManagementError('Wait for the previous title cleanup to finish')
            self.title_replay = None
        if self.title_replay is None:
            def fresh_discovery():
                self.discover()
                return self.discovery
            self.title_replay=ExactTitleReplay(self.session,
                lambda:self.native.menu.panel if self.native and self.native.menu else None,
                fresh_discovery,adapter_factory=lambda session,panel:OwnedTitleAdapters(session,panel,profile=profile),
                profile=profile,
                presentation_factory=lambda:MenuPresentation(self.native.menu))
        return self.title_replay.start()

    def stop_title(self):
        return self.title_replay.stop() if self.title_replay else {'state':'idle'}

    def stop(self):
        if self.original_replay is not None and self.original_replay.status()['active']:
            self.playback_status='Original game cinematic is active; native Stop unavailable'
            return False
        had_media = self.video is not None
        result = self.stop_title()
        if result.get('active'):
            self.playback_status = 'Finishing cinematic cleanup'
            return False
        if self.video is not None:
            if self.video.close() is False:
                self.playback_status = "Finishing media cleanup"
                return False
            self.video = None
        self._play_started = self._paused = False
        self.playback_status = 'Stopped'
        if had_media and self.native and self.native.menu and self.native.menu.panel.state == 'open':
            self.native.parent.refresh()
        return True

    def control(self, scene_id, token):
        if token == 4:
            self.stop(); return
        if token == 1:
            if self.stop() is False:
                raise ManagementError('Wait for the previous cinematic cleanup to finish')
            discovery_started = time.perf_counter()
            try:
                self.discover() # Recheck current save immediately before starting.
            finally:
                LOG.info('Cinematic preparation phase menu_discovery: %.3fs', time.perf_counter() - discovery_started)
            candidates=self.discovery.get('all',self.discovery.get('confirmed',()))
            scene=next((s for s in candidates if s['id']==scene_id
                        and (s.get('unlocked') is True or s.get('replay_kind')=='original_action')),None)
            if scene is None:
                raise ManagementError('Cinematic is not unlocked in the current save')
            if scene.get('replay_kind')=='original_action':
                profile=original_profiles().get(scene_id)
                if profile is None or not profile_matches(profile,scene):raise ManagementError('Exact original-action mapping required')
                menu=self.native.menu
                self.native.parent.dispose_menu()
                if menu.panel.state!='closed':raise ManagementError('Menu must fully dispose before native travel')
                self.original_replay=OriginalActionReplay(self.session,scene,profile)
                self.native.parent.travel_recovery=self.original_replay
                self.original_replay.start()
                self.playback_status='Traveling to original cinematic'
                return
            if not scene.get('supported'):
                raise ManagementError('Cinematic is unlocked, but replay is unavailable: ' +
                                      scene.get('reason', 'No verified playback adapter for this definition'))
            if scene.get('replay_kind') == 'title':
                if not exact_title(scene) or not title_available(self.session._session._transport, scene_id):
                    raise ManagementError('Exact title mapping and verified native cleanup are required')
                self.prepare_title(scene_id)
                self.title_replay.play() # Performs another fresh unlock/context check after arming.
                self.playback_status = 'Starting title'
                return
            from expedition33.cinematics.fullscreen_media import FullscreenMedia
            self.video = FullscreenMedia(self.session)
            try:
                panel = self.native.menu.panel
                profile=MEDIA_PROFILES.get(scene_id)
                if profile is None or not profile.matches(scene):
                    raise ManagementError('Exact media profile mapping is required')
                self.video.build(self.native.menu,profile.movie_path,self.stop)
                from expedition33.cinematics.media_audio_adapter import MediaAudioAdapter,admitted_audio_profile
                audio_profile=admitted_audio_profile(profile)
                if audio_profile is not None:
                    self.video.audio_dependency=MediaAudioAdapter(self.session,panel,audio_profile)
                    self.video.audio_dependency.prepare()
                    self.discover()
                    fresh=next((s for s in self.discovery.get('confirmed',()) if s['id']==scene_id),None)
                    if fresh is None or not fresh.get('unlocked') or not profile.matches(fresh):
                        raise ManagementError('Current cinematic unlock changed during preparation')
                self.video.play()
                self._opening_deadline = time.monotonic()+10
                self._rate = 1.
                self.playback_status = 'Opening intro segment'
            except BaseException:
                LOG.exception('Cinematic playback setup failed')
                self.stop()
                raise
            return
        if scene_id in TITLE_PROFILES or scene_id in MEDIA_PROFILES:
            raise ManagementError('Reviewed replay supports only Play and Stop')
        if self.video is None or not self._play_started:
            raise ManagementError('Start the cinematic segment first')
        if token == 2:
            if self._paused:
                if not self.video.resume(): raise ManagementError('Resume was not accepted')
            elif not self.video.pause(): raise ManagementError('Pause was not accepted')
            self._paused = not self._paused
            self.playback_status = 'Paused' if self._paused else 'Playing'
        elif token == 3:
            self.video.restart(); self._paused = False
            self.playback_status = 'Restarted intro segment'
        elif token == 5:
            rate = .5 if self._rate == 1 else 1.
            if not self.video.set_rate(rate): raise ManagementError('Playback rate was not accepted')
            self._rate = rate; self._paused = False
            self.playback_status = f'Playing at {rate:g}x'

    def _poll_media(self):
        if self.video is None or time.monotonic() < self._next_media_poll: return
        self._next_media_poll = time.monotonic()+.1
        if self.native.menu is None or self.native.menu.panel.state != 'open':
            self.stop(); return
        if self.video.state == 'cleanup_pending':
            self.stop(); return
        state = self.video.playback_status(opening=not self._play_started)
        if not self._play_started:
            if state.get('IsReady'):
                if not self.video.resume(): raise RuntimeError('Media playback was rejected')
                self._play_started = True
                self.playback_status = 'Playing intro segment'
                # The opening observation predates Play. Observe the acknowledged
                # running state now so audio need not wait a complete poll cycle.
                state = self.video.playback_status()
            elif time.monotonic() >= self._opening_deadline:
                if self.stop():self.playback_status = 'Movie could not be opened'
        elif not self._paused and not state.get('IsPlaying') and not state.get('IsPaused'):
            if self.stop():self.playback_status = 'Playback ended'
        if (self.video is not None and self._play_started and state.get('IsPaused') and
                getattr(self.video,'audio_dependency',None) is not None):
            # This composition supports Play/Stop only. A native/external pause
            # must not leave its independently owned audio advancing silently.
            if self.stop():self.playback_status = 'Playback stopped after native media pause'
            return
        if self.video is not None and self._play_started and state.get('IsPlaying'):
            audio=getattr(self.video,'audio_dependency',None)
            if audio is not None:
                try:audio.poll(self.video,True)
                except BaseException:
                    LOG.exception('Synchronized audio failed; stopping owned playback')
                    if self.stop():self.playback_status='Audio playback failed; cleanup completed'

    def poll(self):
        previous_playback_status = self.playback_status
        if self.original_replay is not None:
            original=self.original_replay.poll()
            self.playback_status='Original cinematic: '+original['state']
            if original['active']:return
        if self.title_replay is not None:
            title_state = self.title_replay.poll()
            if self.video is None:
                self.playback_status = 'Title: ' + title_state['state']
        self._poll_media()
        if self.pause:
            previous = self.pause.state
            self.pause.poll()
            if previous == 'attached' and self.pause.state == 'new':
                self.discovery = {'state': 'unavailable_after_travel', 'confirmed': []}
                self.reason = 'Zone changed. Refresh current-save cinematic history.'
            if self.pause.state != 'attached':
                return
        if self.native:
            menu = self.native.menu
            if (self.playback_status != previous_playback_status and menu is not None and
                    not getattr(menu,'_presentation_suspended',False) and
                    menu.panel.state == 'open' and isinstance(menu.view, BrowserView) and
                    menu.view.model is self and menu.view.selected in (*TITLE_PROFILES,*MEDIA_PROFILES)):
                # Only state transitions repaint. During presentation suspension
                # the shared menu defers the newest frame until cleanup.
                self.native.parent.refresh()
            self.native.poll()

    def revoke_world(self,context):
        self._retirement_token=context.previous_token
        self.playback_status='World retired; gameplay callbacks revoked'

    def begin_world_retirement(self,context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if getattr(self,'_retirement_token',None)!=context.previous_token:return 'unknown'
        # Ordinary stop restores presentation, original music and camera/input.
        # Never invoke that compensation against a retired epoch.
        if self.video is not None:return 'unknown'
        replay=self.title_replay
        if replay is not None and any(getattr(replay,key,None) is not None for key in ('sequence','adapters','presentation')):
            return 'unknown'
        if self.pause is not None:
            result=self.pause.retire_world()
            if result!='ack':return result
            self.pause=None
        if self.original_replay is not None:
            prepared=self.original_replay.prepared
            if prepared is not None:prepared.close();self.original_replay.prepared=None
            # Original actions are game-owned. Revoke polling/travel progression,
            # not the campaign action itself; no Stop or new target is invoked.
            self.original_replay=None
        self.title_replay=self.native=self.session=None
        self.discovery={'state':'world_retired','confirmed':[]}
        return 'ack'

    def disable(self):
        if self.stop() is False:
            from expedition33._sequence_owner import SequenceCleanupDeferred
            raise SequenceCleanupDeferred('Cinematic cleanup must finish before disabling its menu')
        if self.native:
            self.native.close()
            self.native = None
        if self.pause:
            self.pause.close()
            self.pause = None
        self.session = None
