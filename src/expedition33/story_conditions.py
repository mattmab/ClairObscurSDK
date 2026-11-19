"""Fresh read-only observations of the original campaign condition maps."""
from ._scope import SessionScope
from .catalog import capture_matching,capture_selected
from .assets import load_asset
from .values import capture_selected_values,StoredMap


def _identity(obj):return (obj.index,obj.serial,obj.address)


def _field(catalog,observed,obj,name,kind):
    row=observed[obj.index]
    keys=[key for key in row.types if key[1]==name]
    if len(keys)!=1:raise RuntimeError('Campaign condition field missing or ambiguous: '+name)
    key=keys[0]
    if (key[0] not in catalog.ancestors(obj.class_index) or row.types[key]!=kind
            or key in row.errors or key in row.truncated or key not in row.values):
        raise RuntimeError('Campaign condition field is incomplete: '+name)
    return row.values[key]


def _binding(scope,ctx,prepared):
    """Selectors only. The subsequent map observation proves every live link."""
    visit=tuple(ctx['visit'])
    if len(visit)!=3 or any(type(n) is not int for n in visit):
        raise ValueError('Explicit campaign World identity required')
    token=getattr(scope,'_world_binding_token',None)
    if token is not None:
        from .world_lifecycle import token_copy
        token=token_copy(token)
        if token[0]!=(scope.pid,*visit):raise RuntimeError('Campaign World differs from scope admission')
    if prepared is not None and getattr(prepared,'session',scope._session) is not scope._session:
        raise RuntimeError('Campaign construction resources belong to another session')
    if prepared is not None and hasattr(prepared,'engine') and hasattr(prepared,'viewport'):
        engine,viewport,gi=prepared.engine,prepared.viewport,prepared.resources.gi
    else:
        from .cinematics.history import anchor
        chain,_=anchor(capture_matching(scope.pid,classes=('GameEngine',)),project=True)
        engine,viewport,world,gi=chain
        if _identity(world)!=visit:raise RuntimeError('Campaign World changed during discovery')
    if token is not None:
        if token[1]!=(scope.pid,*_identity(gi)):raise RuntimeError('Campaign instance differs from scope admission')
        manager=token[2][1:]
    else:
        catalog,values=capture_selected_values(scope.pid,(_identity(gi),),fields=('SaveManager',),references=True)
        current=catalog.resolve(gi)
        manager_obj=_field(catalog,values,current,'SaveManager','ObjectProperty')
        if manager_obj is None:raise RuntimeError('Campaign save manager unavailable')
        manager=_identity(manager_obj)
    return (_identity(engine),_identity(viewport),visit,_identity(gi),manager),token

class StoryConditions:
    def __init__(self,parent):self.scope=SessionScope(parent);self.visit=None;self.flags={}
    def persistent_flag(self,path,ctx):
        return self.persistent_flags((path,),ctx)[path]
    def persistent_flags(self,paths,ctx):
        """Copy requested flags from one fresh map, without a game-thread call.

        The original GetPersistentFlagValue is exactly NamedIDsStates.Find with
        False for an absent object key. It neither loads saved GUID maps nor
        changes flags. Only retained asset selectors survive this operation;
        values, active World links and selected-save state are always reread.
        """
        self.scope._check()
        paths=tuple(paths)
        if not 1<=len(paths)<=64 or len(set(paths))!=len(paths) or any(type(p) is not str or not p for p in paths):
            raise ValueError('One to 64 unique campaign flag paths required')
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        binding,token=_binding(self.scope,ctx,prepared)
        visit=tuple(ctx['visit'])
        if self.visit!=visit:
            self.flags={};self.visit=visit
        for path in paths:
            if path not in self.flags:
                flag=prepared.resources.load(path) if prepared is not None else load_asset(self.scope,path).return_value
                if flag is None:raise RuntimeError('Original campaign flag unavailable')
                self.flags[path]=flag
        identities=tuple(dict.fromkeys((*binding,*(_identity(self.flags[path]) for path in paths))))
        fields=('GameViewport','World','OwningGameInstance','SaveManager','GameInstanceReference',
                'SaveLoaded','LoadIsInProgress','SelectedSlot','NamedIDsStates')
        catalog,observed=capture_selected_values(self.scope.pid,identities,fields=fields,references=True)
        if catalog.pid!=self.scope.pid:raise RuntimeError('Campaign condition process changed')
        objects=tuple(catalog.by_index[identity[0]] for identity in binding)
        if tuple(map(_identity,objects))!=binding:raise RuntimeError('Campaign condition identity changed')
        engine,viewport,world,gi,manager=objects
        for obj,kind in zip(objects,('GameEngine','GameViewportClient','World','BP_jRPG_GI_Custom_C','BP_SaveManager_C')):
            if (obj.object_flags&0x40000030 or
                    catalog.find_class(kind).index not in catalog.ancestors(obj.class_index)):
                raise RuntimeError('Campaign condition owner changed')
        for obj,name,target in ((engine,'GameViewport',viewport),(viewport,'World',world),
                (world,'OwningGameInstance',gi),(gi,'SaveManager',manager),(manager,'GameInstanceReference',gi)):
            found=_field(catalog,observed,obj,name,'ObjectProperty')
            if found is None or _identity(found)!=_identity(target):
                raise RuntimeError('Campaign condition live binding changed: '+name)
        loaded=_field(catalog,observed,gi,'SaveLoaded','BoolProperty')
        loading=_field(catalog,observed,manager,'LoadIsInProgress','BoolProperty')
        slot=_field(catalog,observed,manager,'SelectedSlot','IntProperty')
        if (loaded is not True or loading is not False or type(slot) is not int or slot<0
                or (token is not None and slot!=token[3])):
            raise RuntimeError('Campaign condition selected save is not ready')
        states=_field(catalog,observed,gi,'NamedIDsStates','MapProperty')
        if (not isinstance(states,StoredMap) or (states.key_type,states.value_type)!=('ObjectProperty','BoolProperty')
                or states.key_class is None or any(type(v) is not bool for v in states.items.values())):
            raise RuntimeError('Campaign flags are incomplete or not Boolean')
        key_class=catalog.resolve(states.key_class)
        if key_class.index not in catalog.classes:raise RuntimeError('Campaign flag key class is invalid')
        result={}
        for path in paths:
            flag=catalog.resolve(self.flags[path])
            if flag.object_flags&0x40000030:raise RuntimeError('Campaign flag asset is retiring')
            if key_class.index not in catalog.ancestors(flag.class_index):
                raise RuntimeError('Campaign flag asset differs from the reflected NamedID class')
            result[path]=states.items.get(flag,False)
        return result
    def close(self):
        self.flags={};self.scope.close();return True
    def played_cinematic(self,name,ctx):
        """Read the same saved name/Boolean map used by HasPlayedCinematic."""
        from .catalog import capture_matching
        from .values import read_values_with_references,StoredMap
        if type(name) is not str or not name or not all(ch.isascii() and (ch.isalnum() or ch=='_') for ch in name):raise ValueError('Explicit cinematic identifier required')
        self.scope._check()
        prepared=getattr(self.scope._session,'_story_construction_resources',None)
        gi=getattr(getattr(prepared,'resources',None),'gi',None)
        if gi is not None:
            c=capture_selected(self.scope.pid,((gi.index,gi.serial,gi.address),))
        else:
            c=capture_matching(self.scope.pid,classes=('BP_jRPG_GI_Custom_C',))
        instances=[o for o in c.objects if o.class_name=='BP_jRPG_GI_Custom_C' and not o.object_flags&0x30]
        if len(instances)!=1:raise RuntimeError('Current cinematic history unavailable')
        values,c=read_values_with_references(c,instances[0],fields=('InteractedCinematics',))
        maps=[v for k,v in values.values.items() if k[1]=='InteractedCinematics']
        if values.errors or values.truncated or len(maps)!=1 or not isinstance(maps[0],StoredMap):raise RuntimeError('Cinematic history is incomplete')
        value=maps[0].items.get(name,False)
        if type(value) is not bool:raise RuntimeError('Cinematic history returned no Boolean')
        return value
