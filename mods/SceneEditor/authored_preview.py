"""Owned original or private section-edited preview with interactive scrubbing."""
import json,math,time
from expedition33._scope import SessionScope
from expedition33._reader import shared_operation
from expedition33._menu_latency import measure_method
from expedition33._retired_tracking import close_lease_only_scope
from expedition33.cinematics.portable import PROFILES,available
from expedition33.cinematics.title_adapters import OwnedSequenceContext
from expedition33.sequences import OwnedLevelSequence


def profile_for(document):
    path=document['source']['sequence'] if document is not None else None
    reviewed=next((p for p in PROFILES.values() if p.sequence==path),None)
    if reviewed is not None:return reviewed
    from .sequence_profile import imported_profile
    return imported_profile(document)


def preview_supported(document):
    """Pure menu eligibility; calculate the anchor only when preparing playback."""
    if type(document) is not dict:return False
    graph=document.get('source',{})
    if type(graph) is not dict:return False
    if any(p.sequence==graph.get('sequence') for p in PROFILES.values()):return True
    from .sequence_profile import supports_imported_profile
    return supports_imported_profile(document)


def position(text):
    value=json.loads(text)
    if type(value) not in (int,float) or not math.isfinite(value):raise ValueError('Enter a finite player frame')
    frame=math.floor(value)
    if not -(1<<31)<=frame<(1<<31):raise ValueError('Player frame exceeds native range')
    return frame,float(value-frame)


def preview_position(start,end,frame,subframe=0.):
    """Keep an editable cursor inside the player's exclusive playback end."""
    if frame<start:return start,0.
    if frame>=end:return max(start,end-1),0.
    return frame,subframe


class AuthoredPreview:
    sequence_timeline=True
    # The applied document is an independent validated snapshot. Edits are
    # staged on the workspace and replace this object only when applied.
    projection_snapshot=True
    def __init__(self,session,document,*,edited=False,workspace=None,start_at=None,owner=None,editing_only=False,dependencies=None):
        if type(edited) is not bool:raise ValueError('Boolean edited preview mode required')
        self.editing_only=editing_only;self.dependencies=dependencies
        self.edited=edited;self.document=None;self.copied_asset=None;self.owner=owner
        if edited and not editing_only:
            from expedition33.cinematics.authored_timeline import validate
            self.document=validate(document)
            from expedition33.cinematics.authored_copy import require_key_edit_support
            require_key_edit_support(self.document,session._session._transport)
            from expedition33._timeline_actor_channel import validate_count
            validate_count(self.document['cast_edits']+self.document['npc_tracks'],session._session._transport)
        elif not editing_only:
            from expedition33.cinematics.authored_timeline import create
            # The original preview still needs its source graph on the shared
            # ruler, but must not display saved edits as active playback.
            self.document=create(document['source'],document['name'])
        if editing_only:
            from expedition33.cinematics.authored_timeline import validate
            self.document=validate(document)
        # Inspection does not need a playback anchor. Large imported graphs can
        # be expensive to project; resolve the profile when playback is requested.
        profile=None if editing_only else profile_for(document)
        if profile is None and not editing_only:raise ValueError('This source does not yet have a reviewed owned preview adapter')
        seek=getattr(session._session._transport,'sequence_seek_protocol',0)
        if not editing_only and (not available(session._session._transport) or type(seek) is not int or seek!=1):
            raise RuntimeError('Owned cinematic preview and scrubbing runtime required')
        if profile is None:
            from types import SimpleNamespace
            profile=SimpleNamespace(saved_id=document['name'])
        self.profile=profile;self.scope=SessionScope(session)
        from .sequence_properties import SequenceProperties
        self.editor=SequenceProperties(document,workspace);self.restart_frame=None;self.initial_frame=start_at
        self.initial_subframe=self.restart_subframe=0.
        self.menu=self.sequence=self.services=self.media=None;self.replacements=();self.npcs=None;self.play_scope=None;self._rebuilding=False
        self.ready=self.playing=self.closed=False;self.pending=None;self.frame=self.subframe=0
        self.start_frame=self.end_frame=0;self.rate=(30,1);self.message='Preparing original source';self.next_sample=0.;self.error=None
    def detail(self):
        if getattr(self,'editing_only',False):return 'Edit mode | '+self.document['name']+' | '+self.message+' | No playback started'
        mode='Private edited timeline' if self.edited else 'Original source preview; saved edits are not applied'
        return f'Frame {self.frame+self.subframe:g} | {self.rate[0]}/{self.rate[1]} fps | {self.message} | {mode}'
    def queue(self,action):
        if action not in ('toggle','back','forward','start','seek','close','apply','save','overview','orbit_left','orbit_right','closer','farther','up','down','flight','place_view','visibility'):raise ValueError('Unknown authored preview operation')
        if self.pending!='close':self.pending=action
    def playback_available(self):
        transport=self.scope._session._transport
        return preview_supported(self.editor.document) and available(transport) and getattr(transport,'sequence_seek_protocol',0)==1
    def _promote_playback(self):
        from expedition33.cinematics.authored_timeline import validate
        from expedition33.cinematics.authored_copy import require_key_edit_support
        from expedition33._timeline_actor_channel import validate_count
        if not self.playback_available():raise ValueError('Load a complete LevelSequence source and enable the owned cinematic runtime before playback.')
        document=validate(self.editor.document)
        require_key_edit_support(document,self.scope._session._transport)
        validate_count(document['cast_edits']+document['npc_tracks'],self.scope._session._transport)
        self.profile=profile_for(document);self.document=document;self.edited=True
        self.initial_frame=self.frame;self.initial_subframe=self.subframe
        self._prepare_playback()
        self.editing_only=False
    @measure_method('timeline.menu_and_playback')
    def prepare(self):
        from .timeline import TimelineMenu
        if self.menu is not None:raise RuntimeError('Preview has already been prepared')
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            self.menu=TimelineMenu(self.scope,None,self);self.menu.prepare();self.menu.open()
            if getattr(self,'editing_only',False):
                from .sequence_projection import project_sections
                try:rows,_=project_sections(self.document,self.rate)
                except (ValueError,KeyError):rows=()
                self.start_frame=min((int(r['start']) for r in rows),default=0)
                self.end_frame=max(self.start_frame+1,max((math.ceil(r['end']) for r in rows),default=300))
                self.frame=self.start_frame;self.ready=True;self.message='Track library: edit sections, cast and Blueprint NPCs. Save keeps changes.'
                self.menu.view.picker='sequence';self.menu.refresh()
            else:self._prepare_playback()
    @measure_method('timeline.playback_prepare')
    def _prepare_playback(self):
        from expedition33.simon_portable import _snapshot
        from expedition33.cinematics.controller_anchor import context_observer
        if self.play_scope is not None:raise RuntimeError('Previous playback scope is still owned')
        from expedition33.cinematics import authored_media
        movie=authored_media.source(self.document)
        scene_yaw=self.document.get('scene_yaw',0.)
        transform_cap=getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)==1
        if scene_yaw and not transform_cap:raise ValueError('Scene rotation requires the newer native transform runtime')
        if scene_yaw and movie:raise ValueError('A prerecorded movie cannot be rotated as a 3D scene')
        if movie:
            cap=getattr(self.scope._session._transport,'media_seek_protocol',0)
            if type(cap) is not int or cap!=1:raise ValueError('Authored movies require the media Seek runtime')
        self.copied_asset=None
        self.play_scope=SessionScope(self.scope)
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            with self.latency.measure('timeline.context'):
                context,_,anchor=_snapshot(self.play_scope)
            # Prepared selectors are independent of the Cinematics mod. Verify
            # their GameInstance against this fresh world before any playback
            # mutation; an unavailable preparer uses the original path.
            dependencies=getattr(self,'dependencies',None)
            if dependencies is not None:
                from .loading import validate_dependencies
                validate_dependencies(dependencies,self.play_scope,context)
            destination=self.document.get('scene_position') or tuple(anchor[i]+(1500.,0.,500.)[i] for i in range(3))
            self.scene_anchor=tuple(destination)
            self.scene_yaw=scene_yaw
            from expedition33.cinematics.scene_transform import origin_translation
            delta=origin_translation(self.profile.anchor,destination,scene_yaw)
            playback_document=authored_media.playback_document(self.document) if movie else self.document
            if movie or (self.edited and (playback_document.get('section_edits') or playback_document.get('key_edits'))):
                from expedition33.cinematics.authored_copy import duplicate,apply_key_edits,apply_section_edits
                with self.latency.measure('timeline.private_copy'):
                    self.copied_asset=duplicate(self.play_scope,self.profile.sequence,self.menu.panel.tree)
                with self.latency.measure('timeline.key_edits'):
                    apply_key_edits(self.play_scope,self.copied_asset,self.menu.panel.tree,playback_document)
                with self.latency.measure('timeline.section_edits'):
                    apply_section_edits(self.play_scope,self.copied_asset,self.menu.panel.tree,playback_document)
            options={} if dependencies is None else dict(routing_class=dependencies.routing_class,
                widget_dependencies=dependencies.widget_dependencies,music_dependencies=dependencies.music_dependencies)
            self.services=OwnedSequenceContext(self.play_scope,self.menu.panel,**options)
            with self.latency.measure('timeline.music_prepare'):
                self.services.prepare_music()
            options={} if dependencies is None else dict(asset_loader=dependencies.asset_loader,
                metadata=dependencies.sequence_metadata)
            self.sequence=OwnedLevelSequence(self.play_scope,**options)
            with self.latency.measure('timeline.sequence_build'):
                kwargs=dict(origin_yaw=scene_yaw) if transform_cap else {}
                self.sequence.build(self.menu.panel,self.profile.sequence,capture_camera=True,origin_translation=delta,asset=self.copied_asset,**kwargs)
            if self.edited and self.document['cast_edits']:
                # self.document is the independent, validated preview snapshot;
                # this synchronous owner-thread path does not mutate it.
                from expedition33.cinematics.authored_replacement import _apply_snapshot
                with self.latency.measure('timeline.cast'):
                    # Retain actors as they are constructed, including any
                    # whose spawn or binding fails before the call returns.
                    self.replacements=[]
                    self.replacements=_apply_snapshot(self.sequence,self.document,self.scene_anchor,scene_yaw,owners=self.replacements,latency=self.latency)
            with self.latency.measure('timeline.scrub_prepare'):
                self.sequence.prepare_scrubbing()
            with self.latency.measure('timeline.read_range'):
                current=self.sequence._call('GetCurrentTime');end=self.sequence._call('GetEndTime')
            self.start_frame=current['Time']['FrameNumber']['Value'];self.end_frame=end['Time']['FrameNumber']['Value']
            self.rate=(current['Rate']['Numerator'],current['Rate']['Denominator'])
            with self.latency.measure('timeline.context_verify'):
                if context_observer(self.play_scope)()!=context:raise RuntimeError('World changed during authored preview preparation')
            with self.latency.measure('timeline.services_arm'):
                self.services.arm(self.sequence)
            initial,subframe=preview_position(self.start_frame,self.end_frame,
                self.start_frame if self.initial_frame is None else self.initial_frame,
                self.initial_subframe if self.initial_frame is not None else 0.)
            with self.latency.measure('timeline.initial_seek'):
                self.sequence.seek_frame(initial,subframe)
            if self.edited and self.document['npc_tracks']:
                from expedition33.cinematics.blueprint_npc_tracks import BlueprintNpcTracks
                self.npcs=BlueprintNpcTracks._from_snapshot(self.play_scope,self.document,self.scene_anchor,scene_yaw)
                with self.latency.measure('timeline.npcs'):
                    if not self.npcs.sync(initial+subframe):raise RuntimeError('Initial NPC cleanup is pending')
            if movie:
                from expedition33.cinematics.timeline_media import TimelineMedia
                with self.latency.measure('timeline.media_prepare'):
                    path=authored_media.resolve(self.play_scope,movie)
                    start,end=authored_media.playback_window(self.document,self.rate)
                    self.media=TimelineMedia(self.play_scope,self.menu.panel,path,self.rate,start,end)
                    self.media.prepare()
            self.frame=initial;self.subframe=subframe;self.ready=True;self.message='Ready'
            if not self._sync_media():self.message='Opening authored movie; playback waits for its first frame'
            self.menu.panel.set_field(f'{initial+subframe:g}')
            self.menu._sequence_field_key=None
            with self.latency.measure('timeline.initial_paint'):
                self.menu.refresh()
    def _sync_media(self,playing=None):
        media=getattr(self,'media',None)
        if media is None:return True
        opening=not media.ready
        ready=media.sync(self.frame+self.subframe,self.playing if playing is None else playing)
        if ready and opening and self.message=='Opening authored movie; playback waits for its first frame':
            self.message='Paused | Authored movie ready';self.menu.refresh()
        return ready
    def _sync_npcs(self):
        npcs=getattr(self,'npcs',None)
        if npcs is None or not npcs.needs_sync(self.frame+self.subframe):return True
        resume=self.playing
        if resume:
            self.sequence.pause();self.playing=False
            self._sync_media()
            current=self.sequence._call('GetCurrentTime')
            self.frame=current['Time']['FrameNumber']['Value'];self.subframe=current['Time']['SubFrame']
        # Construction/retirement takes place while the source cursor is held.
        # No wall-clock delay is interpreted as sequence position.
        if not npcs.sync(self.frame+self.subframe):
            self.message='NPC cleanup pending; playback paused';return False
        if resume:
            self._sync_media(True);self.sequence.play();self.playing=True
        return True
    def poll(self):
        if self.closed:return True
        action=self.pending;self.pending=None
        if action=='close':return self.close()
        if getattr(self,'_rebuilding',False):return self._apply_rebuild()
        if not self.ready:return False
        if not getattr(self,'editing_only',False) and not self._sync_media():
            self.pending=action
            return False
        if not getattr(self,'editing_only',False) and getattr(self.scope._session._transport,'sequence_placement_input_protocol',0)==1:
            from expedition33._sequence_flight import SequenceFlight
            toggle,delta=SequenceFlight(self.sequence).inputs()
            typing=False
            if toggle or any(delta):
                panel=self.menu.panel
                with panel._planner.prepare(panel.field,panel._function('Widget','HasKeyboardFocus')).invoke() as result:
                    typing=bool(result.return_value)
            if toggle and not typing:self.menu.set_sequence_shown(self.menu.hidden)
            if any(delta) and not typing and getattr(getattr(self,'flight',None),'active',False) and action is None:
                from .sequence_viewport import nudge_scene
                with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                    try:nudge_scene(self,delta)
                    except ValueError as error:self.message=str(error)
                return False
        if action=='visibility':
            self.menu.set_sequence_shown(self.menu.hidden);return False
        # Coalesce pointer motion to the newest native slider position. Never
        # rebuild/rebind the menu during a drag: that would lose Slate capture.
        if action is None:
            scrub=None if getattr(self.menu,'hidden',False) is True else self.menu.poll_scrub()
            if type(scrub) in (int,float) and math.isfinite(scrub):
                cursor=self.start_frame+max(0.,min(1.,scrub))*(self.end_frame-self.start_frame)
                frame,sub=preview_position(self.start_frame,self.end_frame,math.floor(cursor),cursor-math.floor(cursor))
                if not getattr(self,'editing_only',False):
                    with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                        if getattr(self,'overview_component',None) is not None:
                            from .sequence_viewport import restore
                            restore(self)
                        self.sequence.seek_frame(frame,sub)
                        self.frame,self.subframe,self.playing=frame,sub,False
                        self._sync_media();self._sync_npcs()
                else:self.frame,self.subframe=frame,sub
                if not self.menu.view.picker:self.menu.panel.set_field(f'{self.frame+self.subframe:g}')
                self.menu.panel.set_text(self.menu.panel.labels[8],'Play')
                self.message='Paused | Drag the tracks to scrub';self.menu.draw_tracks()
        if action=='save':
            self.editor.workspace.save();self.message='Timeline saved. Apply edits to rebuild playback.';self.menu.refresh();return False
        if getattr(self,'editing_only',False):
            if action in ('start','toggle','apply','overview','flight'):
                try:self._promote_playback()
                except ValueError as error:
                    if self.play_scope is not None:raise
                    self.message=str(error);self.menu.refresh();return False
                if action=='apply':self.menu.refresh();return False
            elif action in ('back','forward','seek'):
                frame,sub=position(self.menu.panel.read_field()) if action=='seek' else (self.frame+(-1 if action=='back' else 1),0.)
                self.frame,self.subframe=preview_position(self.start_frame,self.end_frame,frame,sub);self.menu.refresh()
                return False
            else:return False
        if action in ('flight','place_view'):
            from .sequence_viewport import fly,place_at_view
            try:
                with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                    (fly if action=='flight' else place_at_view)(self)
            except ValueError as error:self.message=str(error);self.menu.view.sequence_error=str(error)
            self.menu.refresh();return False
        if action in ('overview','orbit_left','orbit_right','closer','farther','up','down'):
            from .sequence_viewport import overview
            try:
                with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):overview(self,action)
            except ValueError as error:
                self.message=str(error);self.menu.view.sequence_error=str(error)
            self.menu.refresh();return False
        if action=='apply':
            from expedition33.cinematics.authored_timeline import validate
            from expedition33._timeline_actor_channel import validate_count
            candidate=validate(self.editor.document)
            from expedition33.cinematics.authored_copy import require_key_edit_support
            require_key_edit_support(candidate,self.scope._session._transport)
            validate_count(candidate['cast_edits']+candidate['npc_tracks'],self.scope._session._transport)
            # Translation edits retain the evaluated player, bound cast and NPC
            # interval owners. Source/track/cast edits still rebuild the child.
            if (getattr(self.scope._session._transport,'sequence_origin_update_protocol',0)==1 and
                    {k:v for k,v in candidate.items() if k not in ('scene_position','scene_yaw')}==
                    {k:v for k,v in self.document.items() if k not in ('scene_position','scene_yaw')} and
                    candidate.get('scene_position') is not None):
                yaw=candidate.get('scene_yaw',0.)
                cap=getattr(self.scope._session._transport,'sequence_origin_transform_protocol',0)==1
                if yaw and not cap:
                    self.message='Scene rotation requires the newer native transform runtime';self.menu.refresh();return False
                if yaw and getattr(self,'media',None) is not None:
                    self.message='A prerecorded movie cannot be rotated as a 3D scene';self.menu.refresh();return False
                with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                    if getattr(self,'overview_component',None) is not None:
                        from .sequence_viewport import restore
                        restore(self)
                    self.sequence.pause();self.playing=False
                    current=self.sequence._call('GetCurrentTime')
                    self.frame=current['Time']['FrameNumber']['Value'];self.subframe=current['Time']['SubFrame']
                    destination=tuple(candidate['scene_position'])
                    from expedition33.cinematics.scene_transform import origin_translation
                    translation=origin_translation(self.profile.anchor,destination,yaw)
                    if self.replacements:
                        from expedition33.cinematics.authored_replacement import validate_reanchor
                        validate_reanchor(self.replacements,candidate,destination,yaw)
                    if self.npcs is not None:self.npcs.validate_reanchor(destination,yaw)
                    if cap:self.sequence.move_origin_transform(translation,yaw)
                    else:self.sequence.move_origin(translation)
                    if self.replacements:
                        from expedition33.cinematics.authored_replacement import reanchor
                        reanchor(self.replacements,candidate,destination,yaw)
                    if self.npcs is not None:self.npcs.reanchor(destination,yaw)
                    self.sequence.seek_frame(self.frame,self.subframe)
                    self.scene_anchor=destination;self.scene_yaw=yaw;self.document=candidate
                    self.message='Whole scene moved | Playback and actor identities retained'
                    pose=getattr(self,'resume_flight_pose',None);self.resume_flight_pose=None
                    if pose is not None:
                        from .sequence_viewport import fly
                        fly(self,pose)
                    self.menu.refresh()
                return False
            current=self.sequence._call('GetCurrentTime')
            self.restart_frame=current['Time']['FrameNumber']['Value']
            self.restart_subframe=current['Time']['SubFrame']
            self._rebuild_document=candidate
            self.menu._revoke();self.ready=False;self._rebuilding=True
            return self._apply_rebuild()
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            if action is not None:
                try:
                    if getattr(self,'overview_component',None) is not None:
                        from .sequence_viewport import restore
                        restore(self)
                    if action=='toggle':
                        if self.playing:self.sequence.pause()
                        else:
                            if not self._sync_npcs():return False
                            self._sync_media(True);self.sequence.play()
                        self.playing=not self.playing
                    else:
                        if action=='seek':frame,sub=position(self.menu.panel.read_field())
                        else:frame,sub=(self.start_frame,0.) if action=='start' else (self.frame+(-1 if action=='back' else 1),0.)
                        frame,sub=preview_position(self.start_frame,self.end_frame,frame,sub)
                        self.sequence.seek_frame(frame,sub);self.frame=frame;self.subframe=sub;self.playing=False
                        if not self._sync_npcs():return False
                        if action=='start':self._sync_media(True);self.sequence.play();self.playing=True
                    self._sync_media()
                    self.message='Playing' if self.playing else 'Paused';self.menu.refresh()
                except Exception as error:
                    self.message=str(error)
                    if self.sequence.uncertain:raise
                    self.menu.refresh()
            if time.monotonic()>=self.next_sample:
                self.next_sample=time.monotonic()+.2
                current=self.sequence._call('GetCurrentTime');self.frame=current['Time']['FrameNumber']['Value'];self.subframe=current['Time']['SubFrame']
                playing=self.sequence._call('IsPlaying')
                if playing!=self.playing:
                    self.playing=playing
                    self.message='Playing' if playing else 'Stopped; timeline remains editable'
                    self.menu.refresh()
                self._sync_npcs();self._sync_media()
                # Paint the cursor without revoking/rebinding clickable controls.
                self.menu.draw_tracks()
        return False
    @measure_method('timeline.apply_poll')
    def _apply_rebuild(self):
        # Retain the same UI tree/input owner; retire only the playback child.
        # Use one short-lived worker across cleanup and reconstruction. Queries
        # remain fresh; pending cleanup exits without replaying any dispatch.
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            if not self._close_player():return False
            self.document=self._rebuild_document;self.edited=True;self.initial_frame=self.restart_frame
            self.initial_subframe=self.restart_subframe
            self._prepare_playback()
            self._rebuilding=False;self._rebuild_document=None
        return False
    @measure_method('timeline.playback_close')
    def _close_player(self):
        from expedition33._sequence_owner import SequenceCleanupDeferred
        try:
            if getattr(self,'media',None) is not None:
                if not self.media.close():return False
                self.media=None
            if getattr(self,'flight',None) is not None:
                self.flight.stop();self.flight=None
            if getattr(self,'npcs',None) is not None:
                if not self.npcs.close():return False
                self.npcs=None
            if self.sequence is not None:
                if getattr(self,'replacements',()):
                    # Close the consumer first, then retain actors whose native
                    # cleanup is deferred. A broad scope close would revoke the
                    # retry journal and abort the session on a deferral.
                    if not self.sequence.owner.close():return False
                    for actor in self.replacements:
                        if not actor.close():return False
                self.sequence.close();self.sequence=None;self.replacements=()
            if self.services is not None:self.services.close();self.services=None
        except SequenceCleanupDeferred:return False
        if getattr(self,'play_scope',None) is not None:
            if not close_lease_only_scope(self.play_scope):return False
            self.play_scope=None
        self.copied_asset=None;self.playing=False;self.overview_camera=self.overview_component=None
        return True
    def close(self):
        self.pending=None;self.ready=False
        if self.menu is not None:self.menu._accept_input=False
        if not self._close_player():self.pending='close';return False
        if self.menu is not None:
            if not self.menu.close():self.pending='close';return False
            self.menu=None
        if not close_lease_only_scope(self.scope):self.pending='close';return False
        self._rebuilding=False;self.playing=False;self.closed=True;return True
    def retire_world(self):
        self.pending=None;self.ready=False
        if self.menu is not None:self.menu._accept_input=False
        if getattr(self,'media',None) is not None:
            if not self.media.retire_world():return 'deferred'
            self.media=None
        if getattr(self,'npcs',None) is not None:
            if not self.npcs.retire_world():return 'deferred'
            self.npcs=None
        if self.sequence is not None:
            if getattr(self,'replacements',()):
                # Release the consuming native player before its bound inputs.
                # This ACK does not yet close the Python child-scope journal.
                if not self.sequence.owner.retire_world():return 'deferred'
                for actor in self.replacements:
                    if not actor.retire_world():return 'deferred'
            widgets=getattr(self.services,'widgets',None)
            if not self.sequence.retire_world(closed_dependents=(widgets,) if widgets else ()):return 'deferred'
            self.sequence=None
        if self.services is not None:
            if not self.services.retire_world():return 'deferred'
            self.services=None
        if getattr(self,'play_scope',None) is not None:
            if not close_lease_only_scope(self.play_scope):return 'deferred'
            self.play_scope=None
        if self.menu is not None:
            result=self.menu.retire_world(native_retirement_ack=True)
            if result!='ack':return result
            self.menu=None
        if not close_lease_only_scope(self.scope):return 'deferred'
        self.playing=False;self.closed=True;return 'ack'
