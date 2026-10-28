"""Paused overview of the reviewed player's own spawnable camera.

No extra camera actor or gameplay view target is created. Scrubbing/playing
returns the camera to its authored track; the sequence owner retires it.
"""
import math
from expedition33.catalog import capture_matching,capture_selected


def call(preview,target,owner,name,*,_identity_only=False,**arguments):
    scope=preview.play_scope
    catalog=capture_matching(scope.pid,names=tuple(dict.fromkeys((owner,name,'Vector','Rotator','HitResult','Actor','ActorComponent','CameraComponent','CineCameraComponent','CameraActor','CineCameraActor'))))
    catalog=catalog.with_observations(capture_selected(scope.pid,((target.index,target.serial,target.address),)))
    function=catalog.find_path('/Script/'+('LevelSequence.' if owner=='LevelSequencePlayer' else 'Engine.')+owner+':'+name)
    planner=scope.invocation_planner(catalog=catalog,selected_results=True)
    with planner.prepare(target,function,**arguments).invoke(refresh_from_result=True) as result:
        value=result.return_value
        if hasattr(value,'index'):
            value=_identity(value) if _identity_only else scope.retain(value).object
        return value


def _identity(obj):
    """Compare the full live identity, not a potentially recycled object index."""
    return (obj.index,obj.serial,obj.address)


def _active_camera(preview):
    component=call(preview,preview.sequence.player,'LevelSequencePlayer','GetActiveCameraComponent')
    if component is None:raise ValueError('Seek into a camera shot before opening the 3D view')
    actor=call(preview,component,'ActorComponent','GetOwner')
    if actor is None or actor.class_name not in ('CineCameraActor','CameraActor'):
        raise ValueError('The active shot does not expose an owned camera')
    return component,actor


def _require_current(preview,component,actor):
    current_component=call(preview,preview.sequence.player,'LevelSequencePlayer','GetActiveCameraComponent',_identity_only=True)
    if current_component!=_identity(component):
        raise ValueError('The active shot camera changed; seek to a shot and reopen the 3D view')
    current_actor=call(preview,component,'ActorComponent','GetOwner',_identity_only=True)
    if current_actor!=_identity(actor):
        raise ValueError('The active shot camera changed; seek to a shot and reopen the 3D view')


def overview(preview,action):
    if preview.sequence is None:raise ValueError('Prepare playback before opening the 3D view')
    if getattr(preview.scope._session._transport,'rotator_values_protocol',0)!=1:raise ValueError('The 3D viewport requires native runtime 227 or newer')
    flight=getattr(preview,'flight',None)
    if flight is not None:
        flight.stop();preview.flight=None
    preview.sequence.pause();preview.playing=False
    if getattr(preview,'overview_camera',None) is None:
        component,actor=_active_camera(preview)
        # This declaration is a necessary check, not proof that this exact
        # active camera is the declared spawnable. Native binding ownership
        # proof for arbitrary nested shots remains a separate requirement.
        from expedition33.cinematics.authored_cast import bindings
        if not any(r['kind']=='spawnable' and r['template'] and r['template']['class'] in ('CineCameraActor','CameraActor') for r in bindings(preview.document['source'])):
            raise ValueError('This source has no authored spawnable camera')
        from expedition33.values import capture_selected_values
        _,values=capture_selected_values(preview.scope.pid,((component.index,component.serial,component.address),),fields=('PostProcessBlendWeight',))
        result=values[component.index]
        if result.errors or result.truncated:raise ValueError('The shot camera settings could not be captured')
        weights=[v for k,v in result.values.items() if k[1]=='PostProcessBlendWeight']
        if len(weights)!=1 or type(weights[0]) not in (int,float):raise ValueError('Complete camera blend weight required')
        # Capture must finish before publishing the camera. A failed read used
        # to leave a half-initialized overview and a later orbit skipped setup.
        _require_current(preview,component,actor)
        preview.overview_camera=actor;preview.overview_component=component;preview.overview_weight=weights[0]
        preview.overview_yaw=180.;preview.overview_distance=1800.;preview.overview_height=650.
    else:
        # A shot can change between user actions. Never move a cached camera
        # after the player's current component or its owner changed.
        _require_current(preview,preview.overview_component,preview.overview_camera)
        if action=='overview':
            # Keep the original post-process weight, not the zero set by the
            # first overview, when the user requests overview a second time.
            preview.overview_yaw=180.;preview.overview_distance=1800.;preview.overview_height=650.
    if action=='orbit_left':preview.overview_yaw-=15.
    elif action=='orbit_right':preview.overview_yaw+=15.
    elif action=='closer':preview.overview_distance=max(100.,preview.overview_distance*.8)
    elif action=='farther':preview.overview_distance=min(50000.,preview.overview_distance*1.25)
    elif action=='up':preview.overview_height=min(20000.,preview.overview_height+200.)
    elif action=='down':preview.overview_height=max(-20000.,preview.overview_height-200.)
    angle=math.radians(preview.overview_yaw);distance=preview.overview_distance;height=preview.overview_height
    center=preview.scene_anchor
    location=dict(X=center[0]+distance*math.cos(angle),Y=center[1]+distance*math.sin(angle),Z=center[2]+100.+height)
    rotation=dict(Pitch=-math.degrees(math.atan2(height,distance)),Yaw=preview.overview_yaw+180.,Roll=0.)
    if call(preview,preview.overview_camera,'Actor','K2_TeleportTo',DestLocation=location,DestRotation=rotation) is not True:
        raise ValueError('The overview camera could not move to that position')
    call(preview,preview.overview_component,'CameraComponent','SetPostProcessBlendWeight',InPostProcessBlendWeight=0.)
    preview.menu.view.picker=False
    preview.message='3D overview | Orbit / distance / height controls | Seek or Play restores the shot camera. Scene position moves the whole scene.'


def restore(preview):
    flight=getattr(preview,'flight',None)
    if flight is not None:
        flight.stop();preview.flight=None
    component=getattr(preview,'overview_component',None)
    if component is not None:
        call(preview,component,'CameraComponent','SetPostProcessBlendWeight',InPostProcessBlendWeight=preview.overview_weight)
        preview.sequence.seek_frame(preview.frame,preview.subframe)
    preview.overview_camera=preview.overview_component=None


def fly(preview,pose=None):
    """Use the existing timeline's owned camera with native per-frame flight."""
    if getattr(preview.scope._session._transport,'sequence_flight_protocol',0)!=1:
        raise ValueError('This build does not include sequence flight')
    previous=getattr(preview,'flight',None)
    if previous is not None and previous.active:
        restore(preview);preview.message='Shot camera restored';return
    overview(preview,'overview')
    camera=preview.overview_camera;component=preview.overview_component
    location=call(preview,camera,'Actor','K2_GetActorLocation')
    rotation=call(preview,camera,'Actor','K2_GetActorRotation')
    if pose is not None:
        location=dict(zip(('X','Y','Z'),pose[:3]));rotation=dict(zip(('Pitch','Yaw','Roll'),pose[3:]))
        if call(preview,camera,'Actor','K2_TeleportTo',DestLocation=location,DestRotation=rotation) is not True:
            raise ValueError('Flight camera placement failed')
    scope=preview.play_scope
    catalog=capture_matching(scope.pid,names=('K2_TeleportTo','GetActiveCameraComponent','GetOwner','Vector','Rotator','Actor','ActorComponent','CameraComponent','MovieSceneSequencePlayer','LevelSequencePlayer'))
    ids=tuple((obj.index,obj.serial,obj.address) for obj in (camera,component,preview.sequence.player))
    catalog=catalog.with_observations(capture_selected(scope.pid,ids))
    planner=scope.invocation_planner(catalog=catalog,selected_results=True)
    move=planner.prepare(camera,catalog.find_path('/Script/Engine.Actor:K2_TeleportTo'),DestLocation=dict(location),DestRotation=dict(rotation))._plan
    source=planner.prepare(preview.sequence.player,catalog.find_path('/Script/LevelSequence.LevelSequencePlayer:GetActiveCameraComponent'))._plan
    component_owner=planner.prepare(component,catalog.find_path('/Script/Engine.ActorComponent:GetOwner'))._plan
    status=preview.sequence.planner.prepare(preview.sequence.player,preview.sequence._function('MovieSceneSequencePlayer','IsPlaying'))._plan
    from expedition33._sequence_flight import SequenceFlight
    flight=SequenceFlight(preview.sequence);flight.start(move,status,source,component_owner)
    preview.flight=flight;preview.menu.view.picker=False
    preview.message='Flight | RMB + WASD / E,Q | Numpad 8,2 forward/back; 6,4 right/left; 9,3 up/down | Alt: fine | Backspace: timeline | Save keeps placement'


def place_at_view(preview):
    flight=getattr(preview,'flight',None)
    if flight is None or not flight.active:raise ValueError('Open the flight editor first')
    pose=flight.poll()
    if not flight.active:raise ValueError('Flight view ended; reopen it before placing the scene')
    pitch,yaw=map(math.radians,pose[3:5])
    destination=[pose[0]+1000.*math.cos(pitch)*math.cos(yaw),pose[1]+1000.*math.cos(pitch)*math.sin(yaw),pose[2]+1000.*math.sin(pitch)]
    preview.editor.workspace.place_scene(destination)
    preview.resume_flight_pose=pose;preview.pending='apply'


def nudge_scene(preview,delta):
    """Translate the same paused scene and NPC owners without rebuilding flight."""
    from expedition33.cinematics.authored_timeline import validate
    workspace=preview.editor.workspace
    candidate=validate(workspace.document)
    if {k:v for k,v in candidate.items() if k!='scene_position'}!={k:v for k,v in preview.document.items() if k!='scene_position'}:
        raise ValueError('Apply the staged track or cast edits before moving the scene')
    destination=[preview.scene_anchor[i]+delta[i] for i in range(3)]
    candidate['scene_position']=destination;candidate=validate(candidate)
    from expedition33.cinematics.scene_transform import origin_translation
    yaw=getattr(preview,'scene_yaw',0.)
    translation=origin_translation(preview.profile.anchor,destination,yaw)
    if getattr(preview,'replacements',()):
        from expedition33.cinematics.authored_replacement import validate_reanchor
        validate_reanchor(preview.replacements,candidate,destination,yaw)
    if preview.npcs is not None:
        preview.npcs.validate_reanchor(destination,yaw)
    # From the first native mutation onward, a later validation or dispatch
    # failure can leave only some owners moved.  In particular, do not let a
    # ValueError escape as a recoverable input error: the preview poller would
    # keep this partly moved scene active and allow another nudge.  Retire the
    # preview through the normal owner journals instead of guessing a rollback
    # or replaying an operation whose native outcome may be unknown.
    try:
        if getattr(preview.scope._session._transport,'sequence_origin_transform_protocol',0)==1:
            preview.sequence.move_origin_transform(translation,yaw)
        else:preview.sequence.move_origin(translation)
        if getattr(preview,'replacements',()):
            from expedition33.cinematics.authored_replacement import reanchor
            reanchor(preview.replacements,candidate,destination,yaw)
        if preview.npcs is not None:preview.npcs.reanchor(destination,yaw)
        preview.sequence.seek_frame(preview.frame,preview.subframe)
        preview.flight.restore_pose()
        workspace.place_scene(destination);preview.document=candidate;preview.scene_anchor=tuple(destination)
    except ValueError as error:
        raise RuntimeError('Scene placement failed; closing preview to safely release its owners: '+str(error)) from error
    preview.message='Scene moved: '+', '.join(f'{v:.2f}' for v in destination)+' cm | Alt: fine | Backspace: timeline | Save to keep'
    preview.menu.panel.set_text(preview.menu.panel.detail,preview.detail())
