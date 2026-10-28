"""Scope-retained LocalPlayer selector with fresh controller/world observations."""
from ..catalog import capture_matching
from ..values import capture_selected_values
from .original_game_action import NotReady


class ControllerAnchor:
    def __init__(self,scope):
        scope._check();self.scope=scope
        catalog=capture_matching(scope.pid,classes=('LocalPlayer',))
        rows=[o for o in catalog.objects if o.class_name=='LocalPlayer' and not o.object_flags&0x30]
        if len(rows)!=1:raise NotReady('One persistent LocalPlayer required')
        from .._stable_lease import acquire_stable
        self._held,_=acquire_stable(scope,rows[0]);local=self._held.object
        self.identity=(local.index,local.serial,local.address)

    def context(self):
        self.scope._check()
        if self._held.active is not True:raise RuntimeError('Cinematic controller anchor lease is inactive')
        catalog,values=capture_selected_values(self.scope.pid,(self.identity,),fields=('PlayerController',),references=True)
        local=catalog.by_index[self.identity[0]];value=values[local.index]
        keys=[k for k in value.types if k[1]=='PlayerController']
        if local.class_name!='LocalPlayer' or local.object_flags&0x30:raise NotReady('LocalPlayer is retiring')
        if len(keys)!=1 or value.types[keys[0]]!='ObjectProperty':raise RuntimeError('LocalPlayer controller schema changed')
        key=keys[0]
        if value.errors or value.truncated or key not in value.values:raise NotReady('LocalPlayer controller projection is incomplete')
        player=value.values[key]
        if player is None:raise NotReady('Player controller is not available yet')
        if player.object_flags&0x30 or not any(catalog.classes[i].name=='PlayerController' for i in catalog.ancestors(player.class_index)):
            raise NotReady('Current PlayerController required')
        worlds=[o for o in catalog.outer_chain(player) if o.class_name=='World']
        if len(worlds)!=1:raise NotReady('Controller world is not available yet')
        world=worlds[0]
        return dict(controller=(self.scope.pid,player.index,player.serial,player.address),
                    world=(self.scope.pid,world.index,world.serial,world.address),world_path=catalog.path_name(world))


def for_scope(scope):
    anchor=getattr(scope,'_cinematic_controller_anchor',None)
    if anchor is None:
        anchor=ControllerAnchor(scope);scope._cinematic_controller_anchor=anchor
    if type(anchor) is not ControllerAnchor or anchor.scope is not scope:raise ValueError('Unrelated cinematic controller anchor')
    return anchor


def context_observer(scope):
    """Choose a fresh context reader; retain only the LocalPlayer selector."""
    capability=getattr(scope._session._transport,'stable_lease_protocol',0)
    if type(capability) is int and capability==1:
        return for_scope(scope).context
    from .original_game_action import controller_context
    return lambda:controller_context(scope._session,project=True)
