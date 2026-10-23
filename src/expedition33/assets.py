"""Experimental retained asset loading for the independently verified build.

Loading does not authorize playback. Sequence events and bindings require a
separate audit. Missing name-pool entries fail closed without adding names.
"""
import re
import struct
import json
import subprocess
from .catalog import capture_matching
from .reflection import describe
from .invocation import CallPlan, Parameter, UnsupportedInvocation


def load_asset(scope,path):
    """Retain a canonical /Game/Package.Asset through the existing asset loader."""
    return _load_asset(scope,path)


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


def _load_asset(scope,path,*,_generated=False):
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
    query=subprocess.run([str(session._transport._executable),'--resolve-export-names' if _generated else '--resolve-asset-names',str(scope.pid),path],
        capture_output=True,text=True,encoding='utf8',timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
    if query.returncode: raise ValueError('Asset name resolution failed: '+query.stderr.strip())
    records=[json.loads(line) for line in query.stdout.splitlines()]
    if len(records)!=3 or records[0].get('event')!='snapshot_start' or records[-1]!={'event':'snapshot_end','emitted':1}:
        raise ValueError('Incomplete asset name observation')
    start,rows=records[0],records[1:-1]
    names=[r for r in rows if r['event']=='asset_names']
    if start['pid']!=scope.pid or len(names)!=1 or names[0]['package']+'.'+names[0]['asset']!=path:
        raise ValueError('Asset-name observation changed')
    c=capture_matching(scope.pid,names=('KismetSystemLibrary','Default__KismetSystemLibrary','LoadAsset_Blocking'))
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
    struct.pack_into('<I',data,8,names[0]['package_id'])
    struct.pack_into('<I',data,16,names[0]['asset_id'])
    plan=CallPlan(target,function,info['flags'],int(info['entry_rva'],16),info['params_size'],
        d.owners[0]['size'],info['return_offset'],tuple(params),bytes(data),(),6)
    with scope._lease_context():
        return scope._adopt_retained(session._invoke_retained_plan(plan,c,_selected_results=True))
