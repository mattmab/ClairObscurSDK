"""Normal game-owned zone entry, using the live level table's main spawn tag.

The dedicated native operation copies FName/GameplayTag values from the verified
table on the game thread. It does not expose raw FName IDs or arbitrary writes.
"""
import re
import struct
from . import _query
from .catalog import capture_matching, capture_selected
from .values import capture_selected_values
from ._reader import ReadBatch,active_reader
from .cinematics.original_game_action import controller_context, NotReady
from .invocation import InvocationError

SIZE=432
HEADER=struct.Struct('<4I')
IDENTITY=struct.Struct('<iiQ')
LIB='/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary'
TABLE='/Game/Gameplay/LevelData/DT_LevelData.DT_LevelData'
TEXT=re.compile(r'[A-Za-z0-9_.]+\Z')
ROUTE_NAMES=('DT_LevelData','ChangeMapByName','Default__FL_jRPG_CustomFunctionLibrary_C')

def available(transport):
    return type(getattr(transport,'zone_travel_protocol',0)) is int and transport.zone_travel_protocol==2

def _one(values):
    values=tuple(values)
    if len(values)!=1:raise NotReady('Normal travel requires one current '+str(len(values))+' matching context')
    return values[0]

def parse_routes(records):
    """Copy only ID, package basename and main entrance tag; reject partial rows."""
    rows=[];row=None
    for record in records:
        if record.get('event')=='table_row':
            row={'level_id':record['name']};rows.append(row)
        elif row is not None and record.get('event')=='stored_value':
            name=record.get('name','');value=record.get('value')
            if name.startswith('LevelAssetName_'):row['asset_name']=value
            elif name.startswith('MainSpawnPoint_'):
                st=value.get('$struct',{}) if isinstance(value,dict) else {}
                if st.get('truncated') is False:
                    row['entrance_tag']=_one(f['value'] for f in st.get('fields',()) if f['name']=='TagName')
    if len({r['level_id'] for r in rows})!=len(rows):raise ValueError('Duplicate level IDs')
    return tuple(r for r in rows if all(type(r.get(k)) is str and TEXT.fullmatch(r[k]) for k in ('level_id','asset_name','entrance_tag')) and r['entrance_tag']!='None')

def routes(pid):
    with ReadBatch(pid,share=active_reader() is None):
        cat=capture_matching(pid,names=('DT_LevelData',))
        table=_one(o for o in cat.objects if cat.path_name(o)==TABLE and o.class_name=='DataTable')
        _,records=_query(['--read-table',str(pid),f'{table.index}:{table.serial}:{table.address:x}'])
        return parse_routes(records)

def attach_routes(maps, entries):
    """Keep the entire menu; disable ambiguous/missing normal routes."""
    by_asset={}
    for entry in entries:by_asset.setdefault(entry['asset_name'],[]).append(entry)
    package_counts={}
    for row in maps:
        name=row['package'].rsplit('/',1)[-1];package_counts[name]=package_counts.get(name,0)+1
    for row in maps:
        name=row['package'].rsplit('/',1)[-1];matches=by_asset.get(name,())
        row['normal_route']=dict(matches[0]) if len(matches)==1 and package_counts[name]==1 else None
    return maps

def validate_request(data):
    if type(data) is not bytes or len(data)!=SIZE or HEADER.unpack_from(data)[0] not in (1,2) or HEADER.unpack_from(data)[1] not in (0,1) or any(HEADER.unpack_from(data)[2:]):raise ValueError('Invalid zone travel packet')
    for i in range(6):
        index,serial,address=IDENTITY.unpack_from(data,16+i*16)
        if index<0 or serial<0 or address<=0:raise ValueError('Invalid zone identity')
    for at,width in ((112,96),(208,96),(304,128)):
        field=data[at:at+width];raw=field.split(b'\0',1)[0]
        if len(raw)>=width or field!=raw.ljust(width,b'\0') or not TEXT.fullmatch(raw.decode('ascii')):raise ValueError('Invalid zone name')

def decode_reply(sent,response):
    try:
        raw=bytes.fromhex(response['zone_packet'])
        if len(raw)!=SIZE or raw[:8]!=sent[:8] or raw[16:]!=sent[16:]:raise ValueError('Mismatched zone reply')
        _,_,outcome,error=HEADER.unpack_from(raw)
        if outcome not in (0,1,2) or (outcome==1 and error):raise ValueError('Invalid zone outcome')
    except (KeyError,ValueError,TypeError) as exc:
        raise InvocationError('Zone reply not verified',outcome='unknown') from exc
    if outcome!=1 or error:
        raise InvocationError('Normal travel rejected ('+str(error)+')',outcome='not_dispatched' if outcome==0 else 'unknown',native_error=error)
    return {'outcome':'validated' if HEADER.unpack_from(sent)[1]==0 else 'dispatch_returned'}

def _travel_objects(session,*,registration=False):
    construction=getattr(session._session,'_story_construction_resources',None)
    if construction is None:
        before=controller_context(session)
        cat=capture_matching(session.pid,names=ROUTE_NAMES,classes=('LocalPlayer','BP_jRPG_GI_Custom_C'))
        cat=cat.with_observations(capture_selected(session.pid,(before['controller'][1:],)))
        gi=_one(o for o in cat.objects if o.class_name=='BP_jRPG_GI_Custom_C' and not o.object_flags&0x30)
        local=_one(o for o in cat.objects if o.class_name=='LocalPlayer' and not o.object_flags&0x30)
    else:
        # Retain selectors and static schemas only. Every route preparation
        # re-observes the admitted controller/world and its actual GI, instead
        # of scanning the entire UObject registry twice per portal.
        cat=construction.catalog(session,ROUTE_NAMES)
        before=construction.anchor.context()
        world_id=before['world'][1:];local_id=construction.anchor.identity
        fields=('OwningGameInstance',)
        if registration:fields+=('PlayerController','BP_DialogueSystemComponent')
        current,values=capture_selected_values(session.pid,
            (world_id,local_id,before['controller'][1:]),fields=fields,references=True)
        world=current.by_index[world_id[0]];local=current.by_index[local_id[0]]
        if world.class_name!='World' or world.object_flags&0x30 or local.class_name!='LocalPlayer' or local.object_flags&0x30:
            raise NotReady('Current world and LocalPlayer required for normal travel')
        value=values[world.index]
        keys=[key for key in value.types if key[1]=='OwningGameInstance']
        if len(keys)!=1 or value.types[keys[0]]!='ObjectProperty':raise NotReady('World game instance schema changed')
        if value.errors or value.truncated or keys[0] not in value.values:raise NotReady('World game instance observation incomplete')
        gi=value.values[keys[0]];owned=construction.resources.gi
        if (gi is None or gi.class_name!='BP_jRPG_GI_Custom_C' or gi.object_flags&0x30
                or (gi.index,gi.serial,gi.address)!=(owned.index,owned.serial,owned.address)):
            raise NotReady('World game instance differs from retained story resources')
        token=getattr(session,'_world_binding_token',None)
        if token is not None and token[0]!=before['world']:raise NotReady('Normal travel world differs from scope admission')
        if registration:
            # Recheck the exact LocalPlayer link in this same fresh batch,
            # together with the controller-owned dialogue component. No later
            # context/identity rereads are needed just to assemble registration.
            from .story_dialogue import field,identity
            local_value=values[local.index];pc=current.by_index[before['controller'][1]]
            links=[key for key in local_value.types if key[1]=='PlayerController']
            if (len(links)!=1 or local_value.types[links[0]]!='ObjectProperty'
                    or local_value.errors or local_value.truncated or pc.object_flags&0x30
                    or identity(field(local_value,'PlayerController'))!=before['controller'][1:]):
                raise NotReady('Normal travel controller changed during preparation')
            worlds=[o for o in current.outer_chain(pc) if o.class_name=='World']
            if len(worlds)!=1 or identity(worlds[0])!=world_id:
                raise NotReady('Normal travel controller changed world')
            pc_value=values[pc.index]
            if pc_value.errors or pc_value.truncated:raise NotReady('Current dialogue controller is unavailable')
            system=field(pc_value,'BP_DialogueSystemComponent')
            if (system is None or system.class_name!='BP_DialogueSystemComponent_C' or system.object_flags&0x30
                    or (system.outer_index,system.outer_serial)!=identity(pc)[:2]):
                raise NotReady('Current controller dialogue component differs')
        elif construction.anchor.context()!=before:raise NotReady('Normal travel context changed during preparation')
        cat=cat.with_observations(current)
    objects=(
        _one(o for o in cat.objects if cat.path_name(o)==TABLE),
        _one(o for o in cat.objects if cat.path_name(o)==LIB+'.FL_jRPG_CustomFunctionLibrary_C:ChangeMapByName'),
        _one(o for o in cat.objects if cat.path_name(o)==LIB+'.Default__FL_jRPG_CustomFunctionLibrary_C'),
        gi,local,cat.by_index[before['controller'][1]],
    )
    if not registration:return objects
    if construction is None:
        from .story_dialogue import controller_dialogue_system,identity
        observed,system=controller_dialogue_system(session.pid,identity(objects[5]))
        cat=cat.with_observations(observed)
    return objects,cat,system

def travel_to_entrance(session,route,*,validate_only=False,_spawn_tag=None,_packet_only=False,_registration=False):
    session._check()
    transport=session._session._transport
    if _registration and not (_packet_only and validate_only):raise ValueError('Registration observations are read-only')
    if not available(transport):raise RuntimeError('Normal zone travel requires SDK zone runtime v67 or newer')
    if _spawn_tag is not None:
        if getattr(transport,'zone_spawn_travel_protocol',0)!=1:raise RuntimeError('Named spawn travel requires the updated SDK runtime')
        if type(_spawn_tag) is not str or not _spawn_tag.startswith('Level.SpawnPoint.') or not TEXT.fullmatch(_spawn_tag) or len(_spawn_tag)>=96:raise ValueError('Existing named game spawn tag required')
        route=dict(route,entrance_tag=_spawn_tag)
    with ReadBatch(session.pid,share=active_reader() is None):
        if _registration:objects,catalog,system=_travel_objects(session,registration=True)
        else:objects=_travel_objects(session)
        data=bytearray(SIZE);HEADER.pack_into(data,0,2 if _spawn_tag is not None else 1,0 if validate_only else 1,0,0)
        for i,o in enumerate(objects):IDENTITY.pack_into(data,16+i*16,o.index,o.serial,o.address)
        for key,at,width in (('level_id',112,96),('asset_name',208,96),('entrance_tag',304,128)):
            value=route[key]
            if type(value) is not str or not TEXT.fullmatch(value):raise ValueError('Invalid route '+key)
            encoded=value.encode('ascii')
            if len(encoded)>=width:raise ValueError('Route name too long')
            data[at:at+width]=encoded.ljust(width,b'\0')
    data=bytes(data);validate_request(data)
    if _packet_only:return (data,catalog,system) if _registration else data
    try:response=transport._command('zone-travel',data)
    except Exception as error:raise InvocationError('Normal travel transport did not confirm outcome',outcome='unknown') from error
    return decode_reply(data,response)


def travel_to_spawn(session,route,spawn_tag,*,validate_only=False):
    """Normal game transition to an existing named spawn point in a verified level.

    This dispatch does not prove arrival. The caller must await the next admitted
    world visit and verify the resulting pawn before advancing story state.
    """
    return travel_to_entrance(session,route,validate_only=validate_only,_spawn_tag=spawn_tag)


def prepare_spawn_packet(session,route,spawn_tag):
    """Read-only preparation; the native receiver still validates before dispatch."""
    return travel_to_entrance(session,route,validate_only=True,_spawn_tag=spawn_tag,_packet_only=True)


def prepare_spawn_registration(session,route,spawn_tag):
    """Return fresh route/component observations for immediate portal setup.

    Nothing is retained between calls. Native registration still validates the
    selected save, current world/controller and every packet identity.
    """
    return travel_to_entrance(session,route,validate_only=True,_spawn_tag=spawn_tag,
        _packet_only=True,_registration=True)


def dispatch_prepared_packet(session,packet):
    """Dispatch once after preparation. Native code revalidates current context."""
    session._check()
    transport=session._session._transport
    if not available(transport):raise RuntimeError('Normal zone travel capability unavailable')
    validate_request(packet)
    data=bytearray(packet);HEADER.pack_into(data,0,HEADER.unpack_from(packet)[0],1,0,0);data=bytes(data)
    try:response=transport._command('zone-travel',data)
    except Exception as error:raise InvocationError('Normal travel transport did not confirm outcome',outcome='unknown') from error
    return decode_reply(data,response)
