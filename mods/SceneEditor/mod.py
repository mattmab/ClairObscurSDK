"""First Scene Editor milestone, independently owned from WorldBuilder."""
import copy,json,time,uuid,logging
from contextlib import nullcontext
from expedition33._reader import ReadBatch,active_reader
from pathlib import Path
from expedition33.management import ModDefinition,Action,Keybind
from expedition33.cinematics.original_game_action import controller_context
from .scene import SceneStore,sample,blank,validate,number,capture_camera,ACTOR_TEMPLATES,ROLES,CLIPS,MAX_ACTORS
from .runtime import Runtime
from .palette import CHARACTERS
from .authored import AuthoredWorkspace

class Mod:
    def __init__(self):
        self._disable_preparing=False
        self.session=self.shared=self.native=None
        self.saved_menu=None;self.want_saved=False;self.next_screen=None;self.want_photo=False;self.photo_transfer=None
        self.hud=self.timeline=None;self.want_timeline=self.want_author=self.want_stop=False;self.next_hud=0.
        self.runtime=Runtime();self.document=None;self.key=None;self.dirty=False
        self.authored=AuthoredWorkspace(background_import=True);self.pending_authored=None;self.pending_timeline_source=None;self.timeline_return=None
        self.authored_preview=None;self.pending_authored_preview=False;self.pending_authored_edited=False
        self._scene_loading=None
        self.pending_clip=None;self.photo_author=False;self.want_visibility=False;self.timeline_shown=True
        self.audio_paths=None;self.want_audio_library=False;self.pending_audio_preview=None
        self.pending_edit=None;self.timeline_selection=None;self.cursor_pinned=False
        self.want_open=self.want_play=False;self.reopen=False;self.message='Create a new scene, open a saved scene, or load the sample.'
        self.store=SceneStore(Path(__file__).resolve().parents[2]/'settings/SceneEditor/scenes')
    def management(self):
        return ModDefinition('e33.scene-editor','Scene Editor',version='0.17.0-authored-cast-pool',
            description='Edit scene timelines, browse game-authored sequence sources and inspect their nested tracks and bindings.',
            actions=(Action('open','Open Scene Editor',self.open),Action('stop','Stop scene safely',self.stop)),
            keybinds=(Keybind('open','Open Scene Editor / return from preview','Insert',self.open),Keybind('stop','Stop scene preview','End',self.stop),Keybind('timeline','Pin / release timeline cursor','Home',self.toggle_timeline),Keybind('timeline_visibility','Show / hide timeline','Backspace',self.toggle_timeline_visibility),Keybind('audition','Preview selected animation','PageDown',self.preview_selected),Keybind('snap_camera','Snap flight to frame camera','PageUp',self.snap_camera),Keybind('capture_camera','Place camera at current view','.',self.capture_camera)))
    def prepare_startup(self,context):
        self._prepare_static()
    def prepare_loading_ui(self,session):
        from .loading import LoadingPreview
        return LoadingPreview(self,session)
    def _prepare_static(self):
        if getattr(self,'_scene_view',None) is None:
            from .view import SceneView
            self._scene_view=SceneView
    def enable(self,session):
        self._disable_preparing=False
        if getattr(session._session._transport,'runtime_scene_protocol',0)!=7:raise RuntimeError('Scene Editor requires its v27 or newer isolated native candidate backend')
        self.shared=getattr(session._session,'_native_menu_service',None)
        if self.shared is None:raise RuntimeError('Enable SDK Management before Scene Editor')
        self._prepare_static()
        self.native=self.shared.for_view(lambda registry:self._scene_view(registry,self))
        self.session=session;self.runtime.session=session
        session.console.expose('scene_editor',self)
        session.console.register('scene.editor',lambda arg:self.open() if arg.strip() in ('','open') else self.stop() if arg.strip()=='stop' else self.status(),owner=self)
    def snap_camera(self,_=None):
        if not self.runtime.authoring:return 'Enter live editing first'
        self.runtime.editor_control(6)
        self.message='Photo camera snapped to the current frame.' if getattr(self.runtime,'photo_mode',False) else 'Frame camera view (including FOV). Move to resume 90-degree flight.'
        return self.message
    def startup_ready(self):
        # Feature entry is available; scene-specific assets remain demand-loaded.
        return self.session is not None and self.shared.ui_ready is True
    def capture_camera(self,_=None):
        if not self.runtime.authoring:return 'Enter live editing first'
        self.runtime.editor_control(7)
        self.document=self.runtime.sync_document(self.document);self.dirty=True
        self.message='Camera key placed from this view at the current frame. Save to keep changes.'
        return self.message
    def toggle_timeline(self,_=None):
        if not self.runtime.authoring:return 'Enter live editing first'
        self.want_timeline=True;return 'Switching timeline cursor pin'
    def toggle_timeline_visibility(self,_=None):
        if not self.runtime.authoring:return 'Enter live editing first'
        self.want_visibility=True;return 'Switching timeline visibility'
    def _set_timeline_shown(self, shown):
        if not self.timeline or shown==self.timeline_shown:return
        self.cursor_pinned=False
        if not shown:
            self.timeline.set_shown(False)
            self.runtime.editor_control(5,1)
        else:self.timeline.set_shown(True)
        if self.hud is not None:
            if self.runtime.photo_mode:self.hud.set_photo_help_compact(shown)
            self.hud._render_call(self.hud.widget,'Widget' if not shown else 'UserWidget','RemoveFromParent' if not shown else 'AddToViewport',**({} if not shown else dict(ZOrder=10001)))
        self.timeline_shown=shown
        self.message='Timeline visible | Backspace: hide | Home: cursor' if shown else 'Photo controls active | Tab: photo settings | Backspace: timeline' if self.runtime.photo_mode else 'Timeline hidden | Backspace: show'

    def preview_selected(self,_=None):
        if not self.runtime.authoring:return 'Enter live editing first'
        return self.runtime.audition(self.runtime.last.get('selected',0))
    def queue_timeline_edit(self,action,key=None):
        if not self.runtime.authoring:raise ValueError('Enter live editing first')
        if action!='music':
            event=next((e for e in self.document['events'] if e['id']==key),None)
            if event is None or event['type'] not in ('animation','audio'):raise ValueError('Select an animation or audio start marker first')
            if action!='delete' and event['type']!='audio':raise ValueError('Select an audio start marker to adjust its volume')
        if action not in ('delete','quieter','louder','music'):raise ValueError('Unknown timeline edit')
        self.pending_edit=(action,key)
    def _apply_pending_edit(self):
        action,key=self.pending_edit;self.pending_edit=None;r=self.runtime
        r.editor_control(0);current=r.sync_document(self.document);candidate=copy.deepcopy(current)
        slot=r.audio_event_slots.get(key)
        if action=='music':candidate['mute_game_music']=not current.get('mute_game_music',False)
        else:
            event=next(e for e in candidate['events'] if e['id']==key)
            if action=='delete':candidate['events']=[e for e in candidate['events'] if e['id']!=key]
            else:event['params']['volume']=min(2.,max(0.,round(event['params']['volume']+(-.05 if action=='quieter' else .05),4)))
        candidate=validate(candidate)
        timeline_open=self.timeline is not None and self.timeline.panel.state=='open'
        if timeline_open:self.timeline.hide();self.timeline.view.closed=False
        try:
            if action=='music':r.set_music_quiet(candidate['mute_game_music'])
            else:r.apply(candidate)
            self.document=r.sync_document(candidate);self.dirty=True
            if action=='delete' and slot is not None:r.drop_audio(slot)
            self.message='Clip deleted. Save to keep changes.' if action=='delete' else ('Game music paused for this scene.' if candidate.get('mute_game_music') else 'Game music restored.') if action=='music' else f'Clip volume: {event["params"]["volume"]:.0%}. Save to keep changes.'
        finally:
            if timeline_open and not r.uncertain and r.authoring:r.editor_control(5,0);self.timeline.open()
    def queue_clip(self,kind,asset=None):
        if not self.runtime.authoring:raise ValueError('Enter live editing first')
        r=self.runtime;r.editor_control(0)
        current=r.sync_document(self.document);candidate=copy.deepcopy(current)
        at=min((int((candidate['duration']-.001)*30))/30,round(r.last.get('playhead',0)*30)/30)
        if kind=='animation':
            if asset not in CLIPS:raise ValueError('Choose a verified animation')
            slot=r.last.get('selected',0)
            if slot>=len(candidate['actors']):raise ValueError('Select a character first')
            self.check_animation(candidate['actors'][slot],asset)
            event=dict(id='useranim-'+uuid.uuid4().hex[:12],type=kind,target=candidate['actors'][slot]['id'],at=at,params=dict(asset=asset,speed=1.,loop=False))
        elif kind=='audio':
            reference=next(e for e in sample(candidate['target_map'])['events'] if e['type']=='audio')
            event=dict(id='useraudio-'+uuid.uuid4().hex[:12],type=kind,target='camera',at=at,params=copy.deepcopy(reference['params']))
            if asset is not None:
                if self.audio_paths is None or asset not in self.audio_paths:raise ValueError('Choose a sound from the audio library')
                event['params']['asset']=asset
        else:raise ValueError('Unsupported clip type')
        candidate['events'].append(event);candidate=validate(candidate)
        self.document=current;self.pending_clip=(candidate,kind)
        self.message='Adding clip at the playhead...'
    def _add_pending_clip(self):
        candidate,kind=self.pending_clip;self.pending_clip=None;r=self.runtime
        if kind=='audio':
            timeline_open=self.timeline is not None and self.timeline.panel.state=='open'
            # The game's menu routing can hide the cursor after a button click
            # followed by a scene update. Reacquire the existing menu input owner
            # outside the callback, exactly as after animation insertion.
            if timeline_open:self.timeline.hide()
            try:
                if getattr(r,'preview_scope',None) is not None:r.stop_audio_preview()
                r.configure_audio(candidate)
                r.apply(candidate);self.document=r.sync_document(candidate);self.dirty=True
            finally:
                if timeline_open and not r.uncertain and r.authoring:
                    r.editor_control(5,0);self.timeline.open()
        else:
            previous={e['id'] for e in self.document['events']}
            event=next(e for e in candidate['events'] if e['id'] not in previous and e['type']=='animation')
            with ReadBatch(self.session.pid) if active_reader() is None else nullcontext():
                r.insert_animation(candidate,event['id'])
            self.document=r.sync_document(candidate);self.dirty=True
        self.message='Clip added at the playhead. Drag its start marker to retime; Save keeps changes.'
    def camera_key(self,action):
        if not self.runtime.authoring:raise ValueError('Enter live editing first')
        r=self.runtime;r.editor_control(0)
        r.seek(min(self.document['duration'],round(r.last.get('playhead',0)*30)/30))
        current=r.sync_document(self.document);keys=current.get('camera_keys',[])
        index=r.last.get('selected_camera',-1)
        if action in ('update','delete') and not 0<=index<len(keys):raise ValueError('Click a camera key on the CAM track first')
        if getattr(r,'photo_mode',False) and action in ('add','update'):
            if action=='update':r.seek(keys[index]['at'])
            return self.capture_camera()
        if action=='delete':
            candidate=copy.deepcopy(current);candidate['camera_keys'].pop(index);candidate=validate(candidate)
        elif action in ('add','update'):
            candidate=capture_camera(current,r.last['editor_camera'],r.last.get('playhead',0),r.author_plan[141],replace=keys[index]['id'] if action=='update' else None)
        else:raise ValueError('Unknown camera key action')
        r.apply(candidate);self.document=r.sync_document(candidate);self.dirty=True
        self.message='Camera key '+{'add':'captured at the playhead','update':'updated from the flight view','delete':'removed'}[action]+'. Save to keep changes.'
        return self.status()
    def start_authoring(self):
        # Reuse one read-only worker for this operation. Every query still reads
        # fresh identities; no object observations or mutation results are cached.
        reader=active_reader()
        if reader is not None:
            reader._check()
            if reader.pid!=self.session.pid:raise RuntimeError('Scene read context belongs to another process')
        started=time.perf_counter()
        with ReadBatch(self.session.pid) if reader is None else nullcontext():
            try:return self._start_authoring()
            finally:logging.getLogger(__name__).info('Scene editor startup total: %.3fs',time.perf_counter()-started)
    def _start_authoring(self):
        if self.runtime.scope is not None:raise ValueError('Stop current playback first')
        if self.document is None:self.load_sample()
        self.runtime.check_host(self.photo_author)
        if self.shared.menu is not None and self.shared.menu.panel.state=='open':self.shared.close_menu()
        self.want_open=self.want_play=self.reopen=False
        try:
            result=self.runtime.start(self.document,authoring=True,photo_mode=self.photo_author)
            synced=self.runtime.sync_document(self.document)
            if synced!=self.document:self.dirty=True
            self.document=synced
            from .hud import SceneHUD
            self.hud=SceneHUD(self.session);self.hud.photo_runtime=self.runtime;self.hud.build()
            if self.runtime.photo_mode:self.hud.show_photo_help();self.hud.set_photo_help_compact(True)
            self.hud._render_call(self.hud.widget,'UserWidget','AddToViewport',ZOrder=10000)
            from .timeline import TimelineMenu
            self.timeline=TimelineMenu(self.session,self.shared.registry,self)
            self.cursor_pinned=False;self.timeline_shown=True;self.want_visibility=False
            if self.runtime.photo_mode and self.runtime.photo_settings_open():
                self.timeline.prepare();self.timeline.set_cursor(False);self._set_timeline_shown(False)
            else:self.timeline.open();self.timeline.set_cursor(False)
            self.runtime.editor_control(5,1)
            self.message='PHOTO MODE TIMELINE | Backspace: hide | Home: cursor | Page Up: snap | Period: capture | Page Down: animation preview' if self.runtime.photo_mode else 'Hold Right Alt to edit the timeline; release to fly. Aim at the camera body to move it.'
            return result
        except BaseException:
            logging.getLogger(__name__).exception('Scene startup failed before cleanup')
            self.stop();raise
    def _close_author_ui(self):
        try:
            if self.timeline is not None:self.timeline.close();self.timeline=None
        finally:
            if self.hud is not None:self.hud.close();self.hud=None
    def open(self,_=None):
        self.timeline_return=None
        if self.authored_preview is not None:self.authored_preview.queue('close')
        self.want_open=True;return 'Opening Scene Editor'
    def load_sample(self):
        self._editable();self.document=sample(controller_context(self.session)['world_path']);self.key=None;self.dirty=False
        self.message='Sample loaded without playback. Save creates a separate user scene.'
    def open_sequence_library(self):
        # Defer ownership changes to poll, rather than tearing down the panel
        # from inside its own input callback. _stop synchronizes the scene first.
        self.next_screen='scene_authored';self.want_open=True
        if self.runtime.scope is not None:self.want_stop=True
        if self.authored_preview is not None:self.authored_preview.queue('close')
    def load_timeline_source(self,path,*,editing_only=False):
        if path not in {row['path'] for row in self.authored.catalog}:raise ValueError('Choose a game sequence from the library')
        if self.pending_timeline_source is not None or self.pending_authored is not None or self.authored.loading is not None:raise ValueError('Source loading is already queued')
        if self.runtime.authoring:
            self.timeline_return=dict(photo=self.runtime.photo_mode,at=self.runtime.last.get('playhead',0),selected=self.runtime.last.get('selected',0))
        self.pending_timeline_editing_only=editing_only
        self.pending_timeline_source=path
        if self.authored_preview is not None:self.authored_preview.queue('close')
    def _finish_authored_preview(self,error):
        self.authored_preview=None
        self.message='Authored preview failed: '+error if error else 'Source preview closed; gameplay camera and input restored.'
        if not error and self.pending_timeline_source is not None:
            self.want_open=self.want_author=False;return
        if not error and self.timeline_return is not None:
            self.photo_author=self.timeline_return['photo'];self.want_author=True;self.want_open=False
        else:
            self.timeline_return=None;self.want_open=True;self.next_screen=getattr(self,'authored_return_screen',None) or 'scene_authored_timeline';self.authored_return_screen=None
    def new_scene(self):
        self._editable();self.document=blank(controller_context(self.session)['world_path']);self.key=None;self.dirty=True
        self.next_screen='scene_setup';self.message='New scene: choose its length and add actors, then enter Flight or Photo timeline.'
    def _editable(self):
        if self.runtime.scope is not None or self.want_play or self.authored_preview is not None or self.pending_authored_preview or self.authored.loading is not None:
            raise ValueError('Stop playback before editing or loading')
    def queue_authored_preview(self,*,edited=False,editing_only=False):
        self._editable()
        if type(edited) is not bool:raise ValueError('Boolean edited preview mode required')
        from .authored_preview import preview_supported
        if not editing_only and not preview_supported(self.authored.document):raise ValueError('This source does not yet have a reviewed owned preview adapter')
        if edited and not editing_only:
            from expedition33.cinematics.authored_copy import require_key_edit_support
            require_key_edit_support(self.authored.document,self.session._session._transport if self.session is not None else None)
            from expedition33._timeline_actor_channel import validate_count
            validate_count(self.authored.document.get('cast_edits',[])+self.authored.document.get('npc_tracks',[]),self.session._session._transport if self.session is not None else None)
        self.pending_authored_editing_only=editing_only;self.pending_authored_edited=edited;self.pending_authored_preview=True
        self.message='Preparing private edited timeline.' if edited else 'Preparing original source preview; saved edits are not applied.'
    def queue_authored(self,path):
        self._editable()
        if self.pending_authored is not None or self.pending_timeline_source is not None:raise ValueError('Source loading is already queued')
        if path not in {row['path'] for row in self.authored.catalog}:raise ValueError('Choose a game sequence from the library')
        if self.authored.source==path and self.authored.graph is not None and self.authored.document is not None:
            self.message='Source already loaded; current edits retained.';return
        self.pending_authored=path;self.message='Reading game sequence tracks and bindings...'
    def unload_authored(self):
        self._editable()
        if not self.authored.close():raise RuntimeError('Source release is pending')
        self.message='Game sequence source released.'
    def edit_authored_range(self,path,field,value):
        if field not in ('start','end'):raise ValueError('Invalid section range field')
        from expedition33.cinematics.authored_timeline import source_range
        start,end=source_range(self.authored.document,path)
        previous=self.authored.document['section_edits'].get(path)
        if previous:start,end=previous['start'],previous['end']
        self.authored.retime(path,value if field=='start' else start,value if field=='end' else end)
        self.message='Timeline range edited. Save keeps changes; owned preview support is in development.'
    def _change(self,edit):
        self._editable()
        if self.document is None:raise ValueError('Load a scene first')
        candidate=copy.deepcopy(self.document);edit(candidate);self.document=validate(candidate);self.dirty=True
        self.message='Unsaved changes. Play reconstructs the edited scene.'
    def actor(self,key):return next(a for a in self.document['actors'] if a['id']==key)
    def event(self,key):return next(e for e in self.document['events'] if e['id']==key)
    def add_character(self,assembly):
        if assembly not in ROLES:raise ValueError('Choose a verified character assembly')
        key=assembly+'-'+uuid.uuid4().hex[:12]
        def change(d):
            if len(d['actors'])>=MAX_ACTORS:raise ValueError('Six character instances maximum')
            actor=copy.deepcopy(ACTOR_TEMPLATES[assembly]);actor['id']=key
            actor['transform']['position']=[-100,160*(len(d['actors'])-2),CHARACTERS[assembly].get('spawn_height',0)]
            if 'spawn_rotation' in CHARACTERS[assembly]:actor['transform']['rotation']=list(CHARACTERS[assembly]['spawn_rotation'])
            if 'spawn_scale' in CHARACTERS[assembly]:actor['transform']['scale']=[CHARACTERS[assembly]['spawn_scale']]*3
            d['actors'].append(actor)
            d['events'].append(dict(id='anim-'+key,type='animation',target=key,at=1.,params=dict(asset=CHARACTERS[assembly].get('default_animation') or ('bind_pose' if CHARACTERS[assembly].get('raw') else 'target_idle'),speed=1.,loop=True)))
        self._change(change);return key
    def remove_character(self,key):
        self.actor(key)
        def change(d):
            d['actors']=[a for a in d['actors'] if a['id']!=key]
            def keep(e):
                if e['target']==key:return False
                if e['id'].startswith(('audio-','impact-','recoil-')):
                    attacker='maelle' if int(e['id'].split('-')[1]) in (1,3,6) else 'lune'
                    if key in (attacker,'target'):return False
                return True
            d['events']=[e for e in d['events'] if keep(e)]
        self._change(change)
        self.message='Character removed, including its animation and dependent sample attack events.'
    def animation_context(self,key):
        actor=self.actor(key)
        return actor['assembly'],self.runtime.character_skeleton(actor['assembly'])
    def check_animation(self,actor,clip):
        if clip!='bind_pose':
            from .palette import ANIMATIONS
            if self.runtime.character_skeleton(actor['assembly'])!=ANIMATIONS[clip]['skeleton']:
                raise ValueError('This animation uses a different skeleton from '+actor['name']+'. Choose one of this actor’s compatible sets.')
    def clear_incompatible_clips(self,key):
        issues=[e['id'] for a,e in self.runtime.incompatible_animations(self.document) if a['id']==key]
        def clear(d):
            for event in d['events']:
                if event['id'] in issues:event['params']['asset']='bind_pose'
        self._change(clear)
        self.message=f'{len(issues)} incompatible clips changed to Bind pose. Actor and clip timing kept. Save to keep this repair.'
    def choose_animation(self,key,clip):
        if clip not in (*CLIPS,'bind_pose'):raise ValueError('Choose a verified animation')
        self.check_animation(self.actor(key),clip)
        def change(d):
            event=next((e for e in d['events'] if e['id']=='anim-'+key),None)
            if event is None:d['events'].append(dict(id='anim-'+key,type='animation',target=key,at=1.,params=dict(asset=clip,speed=1.,loop=True)))
            else:event['params']['asset']=clip
        self._change(change)
    def toggle_loop(self,key):
        self._change(lambda d:next(e for e in d['events'] if e['id']=='anim-'+key)['params'].update(loop=not self.event('anim-'+key)['params']['loop']))
    def edit(self,field,value):
        kind,*parts=field.split(':')
        if kind=='name':self._change(lambda d:d.update(name=value))
        elif kind=='duration':
            value=number(value,2,120)
            def resize(d):
                latest=max((e['at'] for e in d['events'] if e['id']!='camera-orbit'),default=-1)
                last_key=max((k['at'] for k in d.get('camera_keys',[])),default=0)
                if latest>value-.001 or last_key>value:
                    raise ValueError(f'Clips or camera keys reach {max(latest,last_key):g}s. Move them earlier before shortening the scene.')
                orbit=next(e for e in d['events'] if e['id']=='camera-orbit')
                if orbit['at']>=value:raise ValueError('The camera movement starts after the requested scene end')
                orbit['params']['end']=min(orbit['params']['end'],value)
                d['duration']=value
            self._change(resize)
        elif kind=='event':
            self._change(lambda d:next(e for e in d['events'] if e['id']==parts[0]).update(at=value))
        elif kind=='actor_name':
            self._change(lambda d:next(a for a in d['actors'] if a['id']==parts[0]).update(name=value))
        elif kind=='pose':
            key,component,axis=parts
            def change(d):
                pose=next(a for a in d['actors'] if a['id']==key)['transform']
                if component=='scale':pose['scale']=[value]*3
                else:pose[component][int(axis)]=value
            self._change(change)
        else:raise ValueError('Unsupported editor field')
    def save(self,name=None,save_as=False):
        if self.runtime.authoring:self.document=self.runtime.sync_document(self.document)
        else:self._editable()
        if self.document is None:raise ValueError('Load a scene first')
        candidate=copy.deepcopy(self.document)
        if name is not None:candidate['name']=name
        candidate=validate(candidate);self.key=self.store.save(candidate,None if save_as else self.key)
        self.document=candidate;self.dirty=False;self.message='Saved '+candidate['name']
        return self.key
    def load(self,key):
        self._editable();candidate=self.store.read(key);self.document=candidate;self.key=key;self.dirty=False
        self.message='Scene loaded. Playback has not started.'
    def play(self):
        if self.document is None:raise ValueError('Load a scene first')
        validate(self.document)
        if self.runtime.scope is not None:self.stop()
        self.want_play=True;self.message='Preparing scene preview... End stops; Insert returns to editor.'
    def stop(self,_=None):
        if self.authored.loading is not None:
            self.pending_authored=self.pending_timeline_source=None;self.timeline_return=None
            if not self.authored.close():
                self.want_open=True;self.next_screen='scene_authored_timeline'
                self.message='Cancelling source import; existing draft preserved.'
                return self.message
            self.want_open=True;self.next_screen='scene_authored_timeline'
            self.message='Source import cancelled; existing draft preserved.'
            return self.message
        self.pending_authored_preview=False
        if self.authored_preview is not None:
            self.authored_preview.queue('close');return 'Closing authored preview'
        reader=active_reader()
        with ReadBatch(self.session.pid) if self.session is not None and reader is None else nullcontext():
            return self._stop(_)
    def _stop(self,_=None):
        self.want_photo=False;self.photo_transfer=None
        self.want_play=self.want_author=False;self.photo_author=False;self.want_timeline=False;self.want_visibility=False;self.pending_clip=None;self.pending_audio_preview=None;self.want_audio_library=False;self.pending_edit=None
        if self.runtime.authoring:self.document=self.runtime.sync_document(self.document);self.dirty=True
        try:self._close_author_ui()
        finally:result=self.runtime.stop()
        self.message='Playback stopped; temporary resources released.' if self.runtime.scope is None else 'Cleanup pending; scene owner retained.'
        if self.reopen and self.runtime.scope is None:self.want_open=True;self.reopen=False
        return result
    def status(self):return dict(playback=self.runtime.status(),scene=self.document['name'] if self.document else None,saved_id=self.key,dirty=self.dirty,message=self.message)
    def transfer_to_photo(self):
        r=self.runtime
        if not r.authoring or r.photo_mode:raise ValueError('Photo mode switch needs an active flight timeline')
        r.editor_control(0)
        document=r.sync_document(self.document);at=r.last.get('playhead',0);slot=r.last.get('selected',0)
        camera=r.camera_view()
        recovery=copy.deepcopy(document);recovery['name']=(document['name'][:60]+' (before photo)')
        self.store.save(recovery)
        self.document=document
        self.stop()
        if r.scope is not None:raise RuntimeError('Flight cleanup is pending; Photo mode was not requested')
        r.enter_photo_mode()
        self.photo_transfer=dict(at=at,slot=slot,camera=camera,deadline=time.monotonic()+20,next_check=0.)
        self.message='Opening game Photo mode; preserving this scene and timeline time...'
    def _poll_photo_transfer(self):
        transfer=self.photo_transfer
        if time.monotonic()<transfer['next_check']:return
        transfer['next_check']=time.monotonic()+.25
        try:self.runtime.check_host(True)
        except ValueError:
            if time.monotonic()>transfer['deadline']:
                self.photo_transfer=None;self.message='Photo mode did not become ready. Scene preserved; no second entry request was sent.';self.want_open=True
            return
        self.photo_transfer=None;self.photo_author=True
        self.start_authoring();self.runtime.seek(transfer['at'])
        if self.document['actors']:self.runtime.editor_control(4,min(transfer['slot'],len(self.document['actors'])-1))
        actual=self.runtime.camera_view(transfer['camera'])
        logging.getLogger(__name__).info('Photo camera transfer requested=%s actual=%s frame=%s',transfer['camera'],actual,transfer['at'])
        self.message='Photo timeline ready at the same frame. Backspace toggles timeline; Home pins cursor.'
    def poll(self):
        if self.session is None:return
        # A loader shutdown barrier may wait across polls for read-only work to
        # exit.  Do not create another job while shutdown is being prepared.
        if self._disable_preparing:return
        if self.authored.cleanup_pending:
            if not self.authored.close():return
            if self.message=='Cancelling source import; existing draft preserved.':
                self.message='Source import cancelled; existing draft preserved.'
        if self.pending_timeline_source is not None and self.authored_preview is None:
            if self.runtime.scope is not None:
                self.stop()
                if self.runtime.scope is not None:return
            path=self.pending_timeline_source
            try:
                if self.authored.loading is None:
                    self._editable();self.authored.begin_load(self.session,path)
                    self.message='Reading game sequence tracks and bindings...';return
                if not self.authored.poll_load(self.session):
                    self.message=f'Reading game sequence: {self.authored.loaded_nodes} objects';return
                self.pending_timeline_source=None
                self.queue_authored_preview(edited=True,editing_only=getattr(self,'pending_timeline_editing_only',False))
                self.want_open=False
            except Exception as error:
                self.pending_timeline_source=None;self.timeline_return=None;self.message='Sequence timeline: '+str(error);self.want_open=True;self.next_screen='scene_authored_timeline'
        if self.pending_authored_preview:
            self.pending_authored_preview=False
            from .authored_preview import AuthoredPreview
            try:
                self._editable()
                if self.shared.menu is not None and self.shared.menu.panel.state=='open':self.shared.close_menu()
                loading=getattr(self,'_scene_loading',None)
                dependencies=loading.available(self.session) if loading is not None else None
                self.authored_preview=AuthoredPreview(self.session,self.authored.document,edited=self.pending_authored_edited,
                    workspace=self.authored,owner=self,editing_only=getattr(self,'pending_authored_editing_only',False),dependencies=dependencies)
                self.authored_preview.return_to_scene=self.timeline_return is not None
                self.authored_preview.prepare()
            except Exception as error:
                logging.getLogger(__name__).exception('Authored preview preparation failed')
                self.message='Authored preview failed: '+str(error)
                if self.authored_preview is not None:
                    self.authored_preview.error=str(error);self.authored_preview.queue('close')
                else:self.want_open=True
        if self.authored_preview is not None:
            try:
                if self.authored_preview.poll():
                    error=self.authored_preview.error
                    self._finish_authored_preview(error)
                else:return
            except Exception as error:
                self.message='Authored preview: '+str(error);self.authored_preview.error=str(error);self.authored_preview.queue('close');return
        if self.pending_authored is not None:
            path=self.pending_authored
            try:
                if self.authored.loading is None:
                    self._editable();self.authored.begin_load(self.session,path);return
                if not self.authored.poll_load(self.session):
                    self.message=f'Reading game sequence: {self.authored.loaded_nodes} objects';return
                self.pending_authored=None
                self.message='Game sequence source loaded.'
            except Exception as error:self.pending_authored=None;self.message='Source import failed: '+str(error)
            menu=self.native.menu if self.native is not None else None
            if menu is not None and menu.panel.state=='open':
                if self.authored.graph is not None and menu.view.screen!='scene_authored':menu.view.screen='scene_authored_nodes';menu.view.page=0;menu.view.query=''
                menu.view.status=self.message;self.shared.refresh()
        if self.want_photo:
            self.want_photo=False
            try:self.transfer_to_photo()
            except Exception as error:self.message='Photo switch failed: '+str(error);self.want_open=self.runtime.scope is None
        if self.photo_transfer is not None:
            try:self._poll_photo_transfer()
            except Exception as error:self.photo_transfer=None;self.message='Photo timeline startup failed: '+str(error);self.want_open=self.runtime.scope is None
            return
        if self.want_saved:
            self.want_saved=False
            from .view import SavedSceneMenu
            if self.saved_menu is None:self.saved_menu=SavedSceneMenu(self.session,self.shared.registry,self)
            # Construct the replacement while the existing menu remains visible.
            if self.saved_menu.panel.state=='new':
                with ReadBatch(self.session.pid) if active_reader() is None else nullcontext():self.saved_menu.prepare()
            self.shared.close_menu()
            self.saved_menu.open()
        if self.pending_edit is not None:
            try:self._apply_pending_edit()
            except Exception as error:self.message='Timeline edit failed: '+str(error)
        if self.want_audio_library:
            self.want_audio_library=False
            try:
                self.audio_paths=tuple(self.runtime.registry.audio_catalog());self.message=f'{len(self.audio_paths)} audio assets. Music lists authored cues and sets; Sound files lists individual samples. Select, Preview or Add.'
            except Exception as error:self.message='Audio library unavailable: '+str(error)
            if self.timeline is not None and self.timeline.panel.state=='open':self.timeline.refresh()
        if self.pending_audio_preview is not None:
            path=self.pending_audio_preview;self.pending_audio_preview=None
            timeline_open=self.timeline is not None and self.timeline.panel.state=='open'
            if timeline_open:self.timeline.hide();self.timeline.view.closed=False
            try:
                if path:self.runtime.preview_audio(path);self.message='Previewing '+path.rsplit('.',1)[-1]+' (authored sets: up to 15 seconds).'
                else:self.runtime.stop_audio_preview();self.message='Audio preview stopped.'
            except Exception as error:self.message='Audio preview failed: '+str(error)
            finally:
                if timeline_open and not self.runtime.uncertain and self.runtime.authoring:
                    self.runtime.editor_control(5,0);self.timeline.open()
        if self.pending_clip is not None:
            try:self._add_pending_clip()
            except Exception as error:self.message='Clip was not added: '+str(error)
        if self.want_stop:
            self.want_stop=False;self.stop();return
        was_active=self.runtime.scope is not None
        self.runtime.poll()
        if self.runtime.authoring and time.monotonic()>=self.next_hud:
            self.next_hud=time.monotonic()+.15
            synced=self.runtime.sync_document(self.document)
            if synced!=self.document:self.dirty=True
            self.document=synced
            slot=self.runtime.last.get('selected',0);name=self.document['actors'][slot]['name'] if slot<len(self.document['actors']) else 'None'
            if self.runtime.last.get('camera_selected'):name='Scene camera (CAM key at playhead)'
            if self.hud is not None:self.hud.show_selection(name)
            if self.timeline is not None and (self.timeline.panel.state=='open' or self.timeline.passive):
                selection=self.runtime.last.get('selected_clip',-1)
                if selection!=self.timeline_selection and not self.timeline.passive:self.timeline_selection=selection;self.timeline.refresh()
                else:self.timeline.draw_tracks()
        photo_settings=self.runtime.authoring and self.runtime.photo_mode and self.runtime.photo_settings_open()
        if photo_settings:
            if self.timeline_shown:self._set_timeline_shown(False)
            self.want_timeline=self.want_visibility=False
        if self.want_visibility:
            self.want_visibility=False;self._set_timeline_shown(not self.timeline_shown)
        if self.want_timeline:
            if not self.timeline_shown:self._set_timeline_shown(True)
            self.want_timeline=False;self.cursor_pinned=not self.cursor_pinned
        if self.runtime.authoring and self.timeline is not None and self.timeline_shown:
            cursor=self.cursor_pinned or self.runtime.last.get('cursor_held',False)
            if cursor==self.timeline.passive:
                # Stop flight before acquiring UI focus; restore it after releasing focus.
                if cursor:self.runtime.editor_control(5,0)
                self.timeline.set_cursor(cursor)
                if not cursor:self.runtime.editor_control(5,1)
        if was_active and self.runtime.scope is None:self._close_author_ui()
        if was_active and self.runtime.scope is None and self.reopen:
            self.reopen=False;self.want_open=True;self.message='Preview ended; gameplay camera and input restored.'
        if self.want_open:
            # Process UI can temporarily revoke admission while the cinematic
            # releases camera/input ownership. Preserve the request until its
            # shared shell is ready; do not fail the SDK poll or replay open.
            if not getattr(self.shared,'ui_ready',True):return
            self.want_open=False
            if self.runtime.scope is not None:self.stop();self.reopen=False
            if self.shared.menu is not None and self.shared.menu.panel.state=='open':self.shared.close_menu()
            menu=self.native.menu
            if menu is not None:
                # The shared shell retains this presenter while playback owns
                # input. Recreate navigation only for an explicit destination;
                # otherwise preserve the user's page and refresh its status.
                if self.next_screen is not None:menu.view.closed=True
                else:menu.view.status=self.message
            self.native.open()
        if self.want_author:
            self.want_author=False
            resume=self.timeline_return;self.timeline_return=None
            try:
                self.start_authoring()
                if resume is not None:
                    self.runtime.seek(resume['at'])
                    if self.document['actors']:self.runtime.editor_control(4,min(resume['selected'],len(self.document['actors'])-1))
            except Exception as error:self.message='Live editing failed: '+str(error);self.want_open=self.runtime.scope is None
        if self.want_play:
            self.want_play=False
            if self.shared.menu is not None and self.shared.menu.panel.state=='open':self.shared.close_menu()
            self.reopen=True
            try:self.runtime.start(self.document)
            except Exception as error:
                self.message='Preview failed: '+str(error)+' | If the game is paused, resume gameplay and reopen with Insert.'
                self.want_open=self.runtime.scope is None;self.reopen=False
    def _revoke_world_intents(self):
        # Revocation precedes cleanup: a deferred native owner must not replay
        # old editor input when its scope is later activated again.
        self.want_open=self.want_play=self.reopen=False
        self.want_saved=self.want_photo=self.want_timeline=self.want_author=self.want_stop=False
        self.want_visibility=self.want_audio_library=False
        self.photo_transfer=self.next_screen=self.pending_clip=None
        self.pending_audio_preview=self.pending_edit=None
        self.pending_authored=self.pending_timeline_source=None
        self.timeline_return=None
        self.pending_authored_preview=False
        if self.authored_preview is not None:self.authored_preview.pending=None
        self.timeline_selection=None;self.cursor_pinned=False;self.photo_author=False

    def revoke_world(self,context):
        self._revoke_world_intents();self.authored.cancel_load();self._retirement_token=context.previous_token

    def begin_world_retirement(self,context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if getattr(self,'_retirement_token',None)!=context.previous_token:return 'unknown'
        if self.authored_preview is not None:
            result=self.authored_preview.retire_world()
            # Preview owners use "deferred" internally; the lifecycle
            # coordinator accepts "pending" for a known retryable wait.
            if result!='ack':return 'pending' if result=='deferred' else result
            self.authored_preview=None
        loading=getattr(self,'_scene_loading',None)
        if loading is not None:
            from expedition33.ui_shell_proof import UiProofPending
            try:loading.release()
            except UiProofPending:return 'pending'
        if not self.authored.close():return 'pending'
        if any(getattr(self.runtime,name,None) is not None for name in ('scope','preview_scope','audio_load_scope')):
            result=self.runtime.retire_world()
            if result!='ack':return result
        if self.timeline is not None:
            # Native retirement already revoked the timeline binding. Do not
            # unregister through editor_control or touch borrowed photo help.
            self.timeline.registered=False
            result=self.timeline.retire_world(native_retirement_ack=True)
            if result!='ack':return result
            if self.timeline.mirror is not None:
                result=self.timeline.mirror.retire_world(native_retirement_ack=True)
                if result!='ack':return result
                self.timeline.mirror=None
            self.timeline=None
        if self.saved_menu is not None:
            result=self.saved_menu.retire_world(native_retirement_ack=True)
            if result!='ack':return result
            self.saved_menu=None
        if self.hud is not None:
            self.hud.photo_help=None
            result=self.hud.retire_world(native_retirement_ack=True)
            if result!='ack':return result
            self.hud=None
        self.saved_menu=self.timeline=self.native=None;self.shared=None
        self.session=None;self.runtime.session=None
        return 'ack'

    def prepare_disable(self):
        """Settle retryable consumers before the one-shot domain disable."""
        self._disable_preparing=True
        job=self.authored.load_job
        if job is not None:
            self.authored.cancel_load()
            # Keep the import's lease-only scope until disable executes.
            if not job.close():return False
        if self.authored_preview is not None:
            if not self.authored_preview.close():return False
            self.authored_preview=None
        loading=getattr(self,'_scene_loading',None)
        if loading is not None:
            from expedition33.ui_shell_proof import UiProofPending
            try:loading.release()
            except UiProofPending:return False
        return True

    def cancel_disable_preparation(self):
        """Honor a new Enable choice while read-only cancellation finishes."""
        self._disable_preparing=False

    def disable(self):
        if getattr(self,'_scene_loading',None) is not None:
            raise RuntimeError('Scene Editor disable preparation is incomplete')
        self._revoke_world_intents()
        if self.authored_preview is not None:
            if not self.authored_preview.close():raise RuntimeError('Authored preview cleanup is pending')
            self.authored_preview=None
        if not self.authored.close():raise RuntimeError('Authored source release is pending')
        self._close_author_ui()
        if self.saved_menu is not None:self.saved_menu.close();self.saved_menu=None
        self.runtime.disable()
        if self.native is not None:self.native.close()
        self.session=None
