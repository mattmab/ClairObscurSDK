"""Owned original wall collision and noninteractive portal presentation."""
from .cinematics.blueprint_actor import BlueprintActor
from .catalog import capture_matching,capture_selected
from .values import capture_selected_values,read_values_with_references
from .reflection import describe_selected
from .worldbuilder_maps import pose as validate_pose
from . import story_world_configure

def centered_wall_pose(pose,mesh_location):
    """Represent the source mesh offset in the owned centered wall's root."""
    pose=list(pose)
    if mesh_location is None:return pose
    x,y,z,w=pose[:4];v=[a*b for a,b in zip(mesh_location,pose[8:11])]
    cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    t=[2*a for a in cross((x,y,z),v)];u=cross((x,y,z),t)
    pose[4:7]=[p+a+w*b+c for p,a,b,c in zip(pose[4:7],v,t,u)]
    return pose

class WorldElement:
    def __init__(self,parent):self.actor=BlueprintActor(parent);self.state='new'
    @property
    def identity(self):return self.actor.identity
    def prepare(self,kind,pose,*,mesh_location=None,mesh_scale=None):
        if self.state!='new':raise RuntimeError('World element construction is one-shot')
        if kind not in ('wall','portal'):raise ValueError('Reviewed wall or portal required')
        import math
        for vector in (mesh_location,mesh_scale):
            if vector is not None and (type(vector) not in (list,tuple) or len(vector)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>10000 for v in vector)):
                raise ValueError('Finite bounded source mesh transform required')
        pose=validate_pose(list(pose))
        if kind=='wall':pose=centered_wall_pose(pose,mesh_location)
        unit=list(pose);unit[8:11]=[1.,1.,1.]
        self.state='preparing'
        (self.actor.prepare_collision_wall if kind=='wall' else self.actor.prepare_portal_visual)(unit)
        scope=self.actor.scope
        prepared=getattr(scope._session,'_story_construction_resources',None)
        names=('SetMobility','SetActorScale3D','SetRelativeScale3D',
            'K2_SetRelativeLocation','SetInvisibleWallEnabled','SetActorEnableCollision',
            'SetActorTickEnabled','SetActorHiddenInGame','Vector','Rotator','HitResult','EComponentMobility')
        c=prepared.catalog(scope,names) if prepared is not None else capture_matching(scope.pid,names=names)
        names=('SM_InvisibleWalls','RootComponent') if kind=='wall' else ('RootComponent',)
        observed,rows=capture_selected_values(scope.pid,(self.identity,),fields=names,references=True)
        c=c.with_observations(observed)
        if prepared is None:
            functions=tuple((o.index,o.serial,o.address) for o in c.objects if o.class_name=='Function')
            c=c.with_observations(describe_selected(scope.pid,functions).catalog)
        if c.pid!=scope.pid:raise RuntimeError('World element process changed')
        target=c.by_index[self.identity[0]]
        values=rows[target.index]
        roots=[v for k,v in values.values.items() if k[1]=='RootComponent']
        if values.errors or len(roots)!=1 or roots[0] is None:raise RuntimeError('Owned world element root unavailable')
        root=roots[0]
        root_values,c=read_values_with_references(c,root,fields=('Mobility',))
        mobility=[v for k,v in root_values.values.items() if k[1]=='Mobility']
        if root_values.errors or len(mobility)!=1 or mobility[0] not in (0,1,2):raise RuntimeError('Owned element mobility unavailable')
        mesh=None
        if kind=='wall':
            meshes=[v for k,v in values.values.items() if k[1]=='SM_InvisibleWalls']
            if values.errors or len(meshes)!=1 or meshes[0] is None:raise RuntimeError('Owned wall mesh unavailable')
            mesh=meshes[0]
        with (prepared.movement_planner(scope,c) if prepared is not None
                else scope.invocation_planner(catalog=c,selected_results=True)) as planner:
            batch=story_world_configure.available(scope)
            calls=[]
            def call(obj,path,**arguments):
                prepare=planner.prepare_blueprint if path.startswith('/Game/') else planner.prepare
                invocation=prepare(obj,c.find_path(path),**arguments)
                if batch:calls.append(invocation)
                else:
                    with invocation.invoke():pass
            call(root,'/Script/Engine.SceneComponent:SetMobility',NewMobility=2)
            call(target,'/Script/Engine.Actor:SetActorScale3D',NewScale3D=dict(zip('XYZ',pose[8:11])))
            if kind=='wall':
                if mesh_scale is not None:call(mesh,'/Script/Engine.SceneComponent:SetRelativeScale3D',NewScale3D=dict(zip('XYZ',mesh_scale)))
                # The owned wall mesh is centered at zero. Source relative
                # translation was composed into its root before construction;
                # K2_SetRelativeLocation's opaque HitResult is not invoked.
                # This original Blueprint uses Enabled=True for passage:
                # NavArea_Default and NoCollision. False seals the passage.
                call(target,'/Game/LevelTools/InvisibleWalls/BP_InvisibleWall_NavModifier.BP_InvisibleWall_NavModifier_C:SetInvisibleWallEnabled',Enabled=False)
                call(target,'/Script/Engine.Actor:SetActorEnableCollision',bNewActorEnableCollision=True)
                call(target,'/Script/Engine.Actor:SetActorHiddenInGame',bNewHidden=True)
            else:
                # Travel is owned separately by the SDK's spawn-tag transaction.
                # Never activate the unconfigured stock portal's interaction.
                call(target,'/Script/Engine.Actor:SetActorTickEnabled',bEnabled=False)
                call(target,'/Script/Engine.Actor:SetActorEnableCollision',bNewActorEnableCollision=False)
                call(target,'/Script/Engine.Actor:SetActorHiddenInGame',bNewHidden=False)
            call(root,'/Script/Engine.SceneComponent:SetMobility',NewMobility=mobility[0])
            if batch:
                # Preserve the exact original setters and their order. The
                # owned native transaction validates every plan before the
                # first mutation, then returns an ordered receipt prefix.
                story_world_configure.execute(self,kind,root,mesh,mobility[0],calls)
        if kind=='portal':self.actor.state='visible'
        self.state='ready';return self.identity
    def close(self):
        if not self.actor.close():return False
        self.state='closed';return True
    def retire_world(self):
        if not self.actor.retire_world():return False
        self.state='closed';return True

def set_portal_visual_scale(element,scale):
    """Resize only an owned portal's rendering; never its SDK travel gate."""
    import math
    if element.state!='ready' or element.actor.profile!='portal-visual':raise ValueError('Ready owned portal visual required')
    if getattr(element,'_resize_unknown',False):raise RuntimeError('Previous visual resize has no acknowledgement')
    if type(scale) not in (list,tuple) or len(scale)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or not .05<=v<=5 for v in scale):raise ValueError('Bounded positive portal rendering scale required')
    scope=element.actor.scope
    c=capture_matching(scope.pid,names=('SetMobility','SetActorScale3D','Vector','EComponentMobility'))
    c=c.with_observations(capture_selected(scope.pid,(element.identity,)))
    functions=tuple((o.index,o.serial,o.address) for o in c.objects if o.class_name=='Function')
    c=c.with_observations(describe_selected(scope.pid,functions).catalog)
    if c.pid!=scope.pid:raise RuntimeError('Portal visual process changed')
    target=c.by_index[element.identity[0]]
    values,c=read_values_with_references(c,target,fields=('RootComponent',))
    root=next(v for k,v in values.values.items() if k[1]=='RootComponent')
    values,c=read_values_with_references(c,root,fields=('Mobility',))
    mobility=next(v for k,v in values.values.items() if k[1]=='Mobility')
    with scope.invocation_planner(catalog=c,selected_results=True) as planner:
        calls=[planner.prepare(root,c.find_path('/Script/Engine.SceneComponent:SetMobility'),NewMobility=2),
               planner.prepare(target,c.find_path('/Script/Engine.Actor:SetActorScale3D'),NewScale3D=dict(zip('XYZ',scale))),
               planner.prepare(root,c.find_path('/Script/Engine.SceneComponent:SetMobility'),NewMobility=mobility)]
        element._resize_unknown=True
        for call in calls:
            with call.invoke():pass
    values,c=read_values_with_references(c,root,fields=('RelativeScale3D',))
    observed=next(v for k,v in values.values.items() if k[1]=='RelativeScale3D')
    if values.errors or any(abs(observed.fields[n]-v)>1e-6 for n,v in zip('XYZ',scale)):
        raise RuntimeError('Portal visual scale was not acknowledged')
    element._resize_unknown=False
    return tuple(observed.fields[n] for n in 'XYZ')

def place_portal_visual(element,location,yaw):
    """Move our retained noninteractive visual using normal owned placement."""
    if element.state!='ready' or element.actor.profile!='portal-visual':raise ValueError('Ready owned portal visual required')
    actor=element.actor
    if actor.state=='prepared':
        from .catalog import capture_selected
        c=capture_selected(actor.scope.pid,(actor.identity,))
        values,c=read_values_with_references(c,c.by_index[actor.identity[0]],fields=('bHidden',))
        hidden=[v for k,v in values.values.items() if k[1]=='bHidden']
        if values.errors or hidden!=[False]:raise RuntimeError('Portal visual has not been shown')
        # Earlier candidates showed portals through acknowledged engine setters
        # rather than the character reveal route. Reflect that observed state.
        actor.state='visible'
    actor.move(location,yaw,placement=True)
    return actor.identity
