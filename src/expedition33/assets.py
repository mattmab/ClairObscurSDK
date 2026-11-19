"""Experimental retained asset loading for the independently verified build.

Loading does not authorize playback. Sequence events and bindings require a
separate audit. Missing name-pool entries fail closed without adding names.
"""
import re
import struct
from .catalog import capture_matching
from .reflection import describe
from .invocation import CallPlan, Parameter, UnsupportedInvocation


def load_asset(scope,path,*,prepared=None):
    """Retain a canonical /Game/Package.Asset through the existing asset loader."""
    return _load_asset(scope,path,_prepared=prepared)


def _generated_world_path(path):
    if type(path) is not str or len(path)>=1024:return False
    match=re.fullmatch(r'/Game/Levels/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)/_Generated_/([A-Z0-9]{25})\.([A-Za-z0-9_]+)',path)
    return match is not None and match[1].casefold()==match[3].casefold()


def load_generated_world(scope,path):
    """Retain an exact generated-cell World for inspection, without activation.

    No OpenLevel, streaming, InitializeActorsForPlay or BeginPlay is invoked.
    Caller owns the returned retained invocation and must close it or its scope.
    Name creation is forbidden; current player context must remain unchanged.
    """
    from .catalog import capture_selected
    from ._reader import ReadBatch
    from .cinematics.original_game_action import controller_context
    scope._check()
    capability=getattr(scope._session._transport,'generated_world_asset_load_protocol',0)
    if type(capability) is not int or capability!=1:raise UnsupportedInvocation('Generated World export loading capability unavailable')
    if not _generated_world_path(path):raise ValueError('Expected an exact generated-cell World export')
    context=controller_context(scope._session)
    retained=_load_asset(scope,path,_generated=True)
    try:
        obj=retained.return_value
        if obj is None:raise RuntimeError('Generated World export did not load')
        with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
            c=capture_selected(scope.pid,((obj.index,obj.serial,obj.address),))
            current=c.by_index[obj.index]
            cls=c.by_index[current.class_index]
            if c.path_name(current)!=path or c.path_name(cls)!='/Script/Engine.World':
                raise RuntimeError('Generated World returned another export or class')
            if (obj.index,obj.serial,obj.address)==tuple(context['world'][1:]):
                raise RuntimeError('Source World is the active player World')
        if controller_context(scope._session)!=context:raise RuntimeError('Player context changed while retaining source World')
        return retained
    except BaseException:
        retained.close()
        raise



class PreparedAssetLoader:
    """Retained loader selectors; every load still reads a fresh schema."""
    def __init__(self,scope,*,_class=False):
        scope._check()
        self.scope=scope;self._path_names={};self._name_functions=None
        loader='LoadClassAsset_Blocking' if _class else 'LoadAsset_Blocking'
        c=capture_matching(scope.pid,names=('KismetSystemLibrary','Default__KismetSystemLibrary',loader))
        def one(rows):
            rows=tuple(rows)
            if len(rows)!=1:raise ValueError('Ambiguous asset-loading identity')
            return rows[0]
        owner=one(o for o in c.objects if o.name=='KismetSystemLibrary' and o.class_name=='Class')
        target=one(o for o in c.objects if o.name=='Default__KismetSystemLibrary' and o.class_index==owner.index)
        function=one(o for o in c.objects if o.name==loader and o.outer_index==owner.index)
        from ._stable_lease import acquire_stable
        self.leases=tuple(acquire_stable(scope,obj)[0] for obj in (owner,target,function))

    def prepare_path(self,path):
        """Explicitly intern a declared canonical path; load grants no playback."""
        self.scope._check()
        if getattr(self.scope._session._transport,'asset_path_name_protocol',0)!=1:
            raise UnsupportedInvocation('Declared asset path preparation requires SDK runtime 292')
        if path in self._path_names:return
        from ._stable_lease import acquire_stable
        from . import _story_item_wire as wire
        import secrets
        if self._name_functions is None:
            c=capture_matching(self.scope.pid,names=('Conv_StringToName','Default__KismetStringLibrary'))
            self._name_functions=tuple(acquire_stable(self.scope,c.find_path(p))[0] for p in (
                '/Script/Engine.Default__KismetStringLibrary','/Script/Engine.KismetStringLibrary:Conv_StringToName'))
        packet=wire.names(secrets.randbits(64) or 1,*self._name_functions,path,original=True)
        with self.scope._lease_context():reply=self.scope._session._transport.command('mesh',packet)
        values=wire.decode(packet,bytes.fromhex(reply['mesh_packet']))
        package,asset=path.split('.')
        # FName IDs are append-only process metadata. The native asset loader
        # rechecks both entries on every dispatch; UObject observations are fresh.
        a,b=struct.unpack_from('<2Q',bytes.fromhex(reply['mesh_packet']),80)
        self._path_names[path]=dict(event='asset_names',package=package,asset=asset,
            package_id=a&0xffffffff,asset_id=b&0xffffffff,package_number=a>>32,asset_number=b>>32)
    def names_for(self,scope,path):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session:raise RuntimeError('Prepared path belongs to another session')
        from ._asset_names import resolve
        return self._path_names.get(path) or resolve(scope,path)

    def capture(self,scope):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session or not all(lease.active for lease in self.leases):
            raise RuntimeError('Prepared asset loader is no longer owned by this SDK session')
        from .catalog import capture_selected
        return capture_selected(scope.pid,tuple((lease.object.index,lease.object.serial,lease.object.address)
                                                for lease in self.leases))

def _load_asset(scope,path,*,_generated=False,_prepared=None):
    """Return a scoped RetainedInvocation; close it to release the asset lease.

    Accepts only top-level /Game/Package.Asset paths. The native backend verifies
    the function, property class, bounded name entries and live object identities
    on the game thread, then retains the output before acknowledging it.
    """
    scope._check()
    session=scope._session
    if getattr(session._transport,'asset_load_protocol',0)!=1:
        raise UnsupportedInvocation('Verified asset loading requires the sequence candidate runtime')
    if not (_generated_world_path(path) if _generated else type(path) is str and re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.(?i:\1)',path)):
        raise ValueError('Expected a canonical top-level /Game/Package.Asset path')
    from ._asset_names import resolve
    names=[_prepared.names_for(scope,path) if _prepared is not None and not _generated else resolve(scope,path,export=_generated)]
    numbers=tuple(names[0].get(key+'_number',0) for key in ('package','asset'))
    cap=getattr(session._transport,'asset_name_number_protocol',0)
    if any(numbers) and (type(cap) is not int or cap!=1):
        raise UnsupportedInvocation('Numbered asset names require the newer native asset loader')
    c=(_prepared.capture(scope) if _prepared is not None else
       capture_matching(scope.pid,names=('KismetSystemLibrary','Default__KismetSystemLibrary','LoadAsset_Blocking')))
    def one(values):
        values=tuple(values)
        if len(values)!=1: raise ValueError('Ambiguous asset-loading identity')
        return values[0]
    owner=one(o for o in c.objects if o.name=='KismetSystemLibrary' and o.class_name=='Class')
    target=one(o for o in c.objects if o.name=='Default__KismetSystemLibrary' and o.class_index==owner.index)
    function=one(o for o in c.objects if o.name=='LoadAsset_Blocking' and o.outer_index==owner.index)
    d=describe(c,(function,))[function.index]
    info=d.function
    params=[]
    returned=one(p for p in d.properties if p['name']=='ReturnValue' and p['type']=='ObjectProperty')
    for p in d.properties:
        # The current metadata reader does not expose SoftObjectProperty's
        # class field. The native gate checks it against this observed Object
        # return constraint before dispatch, without guessing a pointer here.
        class_row=returned if p['type']=='SoftObjectProperty' else p
        constraint=c.by_index[class_row['property_class_index']]
        if constraint.serial!=class_row['property_class_serial'] or c.path_name(constraint)!='/Script/CoreUObject.Object':
            raise ValueError('Asset loader class constraint changed')
        params.append(Parameter(p['name'],p['type'],p['offset'],p['element_size'],p['dimension'],p['flags'],constraint=constraint))
    data=bytearray(48)
    struct.pack_into('<II',data,8,names[0]['package_id'],numbers[0])
    struct.pack_into('<II',data,16,names[0]['asset_id'],numbers[1])
    plan=CallPlan(target,function,info['flags'],int(info['entry_rva'],16),info['params_size'],
        d.owners[0]['size'],info['return_offset'],tuple(params),bytes(data),(),6)
    with scope._lease_context():
        return scope._adopt_retained(session._invoke_retained_plan(plan,c,_selected_results=True))
