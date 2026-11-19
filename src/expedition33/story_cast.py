"""Temporary authored protagonist casting, independent of exploration cosmetics.

The selected pawn is never replaced or written to a save. A disposable authored
stand-in is shown only when its visual role differs; pawn visibility is restored
after the original dialogue releases its camera/input ownership.
"""
from .story_dialogue import identity,field

def matches_profile(mesh_path,profile):
    value=mesh_path.casefold()
    if profile=='gustave':return 'sk_gustave' in value or '/noah/' in value
    return profile.casefold() in value.rsplit('.',1)[-1]

class AuthoredDialogueCast:
    @classmethod
    def for_cinematic(cls,scope):
        """A scene with its own complete cast hides the exploration pawn."""
        from .cinematics.controller_anchor import for_scope
        from .values import capture_selected_values
        ctx=for_scope(scope).context()
        c,v=capture_selected_values(scope.pid,(ctx['controller'][1:],),fields=('Pawn',),references=True)
        pawn=field(v[ctx['controller'][1]],'Pawn')
        if pawn is None:raise RuntimeError('Cinematic exploration pawn unavailable')
        stage=cls(scope,None);stage.pawn=identity(pawn);stage.replacement=True
        return stage
    def __init__(self,scope,profile):
        self.scope=scope;self.profile=profile;self.pawn=None;self.actor=None
        self.replacement=False;self.standin=None;self.saved=None;self.restore=None;self.planner=None;self.held=None
    def resolve_player(self):
        """Use the original player speaker only after fresh role/possession proof.

        A matching visible party role alone is insufficient: it may be an AI
        companion while another character is selected. Resolve the current
        controller, body ownership and mesh exactly as for an authored cast.
        """
        borrowed=getattr(self,'borrowed_actor',None)
        if borrowed is None:return False
        self.resolve(None)
        return not self.replacement and self.actor==self.pawn==tuple(borrowed)
    def resolve(self,standin):
        if self.saved is not None:raise RuntimeError('Cannot recast an active authored scene')
        from .cinematics.controller_anchor import for_scope
        from .values import capture_selected_values
        from .story_animation import body,body_from_observation
        from .story_preflight import observe
        anchor=for_scope(self.scope);context=observe(anchor.context)
        controller=tuple(context['controller'][1:]);borrowed=getattr(self,'borrowed_actor',None)
        # The role resolver just found this original actor. Observe its body
        # alongside the controller, then use it only if the same batch still
        # identifies that actor as the selected pawn. No role/profile result is
        # cached: its current mesh is read and checked below as before.
        selected=(controller,) if borrowed is None else tuple(dict.fromkeys((controller,tuple(borrowed))))
        names=('Pawn',) if borrowed is None else ('Pawn','Body','Mesh')
        c,values=observe(capture_selected_values,self.scope.pid,selected,fields=names,references=True)
        pawn=field(values[context['controller'][1]],'Pawn')
        if pawn is None:raise RuntimeError('Authored scene player unavailable')
        component=(body_from_observation(c,identity(pawn),values[pawn.index])
                   if borrowed is not None and identity(pawn)==tuple(borrowed)
                   else body(self.scope,identity(pawn),defer_reads=True))
        c,values=observe(capture_selected_values,self.scope.pid,(identity(component),),fields=('SkeletalMesh',),references=True)
        mesh=field(values[component.index],'SkeletalMesh')
        if mesh is None:raise RuntimeError('Authored scene player visual unavailable')
        self.pawn=identity(pawn);self.standin=standin
        self.replacement=not matches_profile(c.path_name(mesh),self.profile)
        self.actor=getattr(self,"borrowed_actor",None) or ((standin.visual.identity if standin is not None else None) if self.replacement else self.pawn)
        return self.replacement
    def begin(self):
        if self.saved is not None:return
        from .catalog import capture_matching,capture_selected
        from .values import capture_selected_values
        from ._stable_lease import acquire_stable
        anchor=getattr(self,'borrowed_actor',None) or self.pawn
        c,batch=capture_selected_values(self.scope.pid,(anchor,),fields=('bHidden','RootComponent','CapsuleComponent'),references=True)
        values=batch[anchor[0]]
        hidden=field(values,'bHidden');root=field(values,'RootComponent');capsule=field(values,'CapsuleComponent')
        if type(hidden) is not bool or root is None or capsule is None:raise RuntimeError('Authored scene pawn state unavailable')
        if self.standin is not None:
            c,batch=capture_selected_values(self.scope.pid,tuple(dict.fromkeys((identity(root),identity(capsule)))),
                fields=('RelativeLocation','RelativeRotation','AttachParent','CapsuleHalfHeight'),references=True)
            values=batch[root.index]
            if field(values,'AttachParent') is not None:raise RuntimeError('Finish traversal before the authored scene')
            location=field(values,'RelativeLocation').fields;rotation=field(values,'RelativeRotation').fields
            feet=[location['X'],location['Y'],location['Z']-field(batch[capsule.index],'CapsuleHalfHeight')]
            # A real matching pawn/companion already supplies the visible cast.
            # Move only its empty camera carrier; a hidden fallback visual has
            # no role in this line. A genuine fallback still moves both actors.
            self.standin.move(feet,rotation['Yaw'],visual=self.replacement and getattr(self,'borrowed_actor',None) is None)
        elif not self.replacement:
            # Direct player binding has no private camera carrier to move, but
            # traversal still owns attached actors and must remain excluded.
            c,batch=capture_selected_values(self.scope.pid,(identity(root),),fields=('AttachParent',),references=True)
            if field(batch[root.index],'AttachParent') is not None:raise RuntimeError('Finish traversal before the authored scene')
        if not self.replacement or getattr(self,"preserve_player",False):return
        c=capture_matching(self.scope.pid,names=('SetActorHiddenInGame',))
        if self.held is None or identity(self.held.object)!=self.pawn:
            self.held,_=acquire_stable(self.scope,capture_selected(self.scope.pid,(self.pawn,)).by_index[self.pawn[0]])
        held=self.held;observed=capture_selected(self.scope.pid,(self.pawn,))
        c=c.with_observations(observed)
        self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
        function=c.find_path('/Script/Engine.Actor:SetActorHiddenInGame')
        hide=self.planner.prepare(held.object,function,bNewHidden=True)
        self.restore=self.planner.prepare(held.object,function,bNewHidden=hidden)
        self.saved=self.pawn
        with hide.invoke():pass
    def close(self,*,world_retired=False):
        if self.saved is not None and not world_retired:
            from .cinematics.controller_anchor import for_scope
            from .values import capture_selected_values
            ctx=for_scope(self.scope).context()
            c,v=capture_selected_values(self.scope.pid,(ctx['controller'][1:],),fields=('Pawn',),references=True)
            if identity(field(v[ctx['controller'][1]],'Pawn'))!=self.saved:raise RuntimeError('Authored scene pawn changed before visibility restoration')
            with self.restore.invoke():pass
        self.saved=None;self.restore=None
        if self.planner is not None:self.planner.close();self.planner=None
        return True
