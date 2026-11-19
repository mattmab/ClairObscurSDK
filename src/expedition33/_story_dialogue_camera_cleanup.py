"""Release stale pawn dialogue cameras after the original conversation ends."""
from .story_dialogue import field,identity

def stale_cameras(cameras,states):
    # Leave the game in control if it has not reactivated its gameplay camera.
    if not any(o.name in ('MainCamera','Main_CineCamera') and states[o.index] is True for o in cameras):return ()
    return tuple(o for o in cameras if o.name.startswith('CineCamera_Dialogue') and states[o.index] is True)

def finish(scope,expected_pawn=None):
    from .cinematics.controller_anchor import for_scope
    from .catalog import capture_matching,capture_selected
    from .values import capture_selected_values
    from ._reader import shared_operation
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        ctx=for_scope(scope).context()
        c,v=capture_selected_values(scope.pid,(ctx['controller'][1:],),fields=('Pawn',),references=True)
        pawn=field(v[ctx['controller'][1]],'Pawn')
        if pawn is None or expected_pawn is not None and identity(pawn)!=expected_pawn:return False
        c=capture_matching(scope.pid,classes=('BP_DialogueSystemComponent_C',))
        systems=[o for o in c.objects if o.class_name=='BP_DialogueSystemComponent_C' and
                 (o.outer_index,o.outer_serial)==tuple(ctx['controller'][1:3])]
        if len(systems)!=1:return False
        _,v=capture_selected_values(scope.pid,(identity(systems[0]),),fields=('ActiveDialogue',),references=True)
        if field(v[systems[0].index],'ActiveDialogue') is not None:return False
        # Enumerate only this pawn's complete reflected component arrays.
        # Global CameraComponent discovery exceeds the catalog result bound
        # after Opera streaming and must never block dialogue completion.
        from .values import StoredArray
        _,owned=capture_selected_values(scope.pid,(identity(pawn),),
            fields=('BlueprintCreatedComponents','InstanceComponents'),references=True)
        row=owned[pawn.index]
        if row.errors or row.truncated:return False
        components={}
        for name in ('BlueprintCreatedComponents','InstanceComponents'):
            array=field(row,name)
            if not isinstance(array,StoredArray) or array.length!=len(array.items) or array.length>256:return False
            for obj in array.items:
                if obj is not None and (obj.outer_index,obj.outer_serial)==(pawn.index,pawn.serial):
                    components[identity(obj)]=obj
        cameras=[o for o in components.values() if
                 o.class_name in ('CameraComponent','CineCameraComponent') and
                 (o.name in ('MainCamera','Main_CineCamera') or o.name.startswith('CineCamera_Dialogue'))]
        if not cameras:return False
        _,v=capture_selected_values(scope.pid,tuple(identity(o) for o in cameras),fields=('bIsActive',),references=True)
        selected=stale_cameras(cameras,{o.index:field(v[o.index],'bIsActive') for o in cameras})
        if not selected:return True
        functions=capture_matching(scope.pid,names=('Deactivate',))
        fn=functions.find_path('/Script/Engine.ActorComponent:Deactivate')
        c=capture_selected(scope.pid,tuple(identity(o) for o in selected)+(identity(fn),))
        planner=scope.invocation_planner(catalog=c,selected_results=True)
        try:
            for camera in selected:
                with planner.prepare(c.by_index[camera.index],c.by_index[fn.index]).invoke():pass
        finally:planner.close()
        _,v=capture_selected_values(scope.pid,tuple(identity(o) for o in selected),fields=('bIsActive',),references=True)
        return all(field(v[o.index],'bIsActive') is False for o in selected)
