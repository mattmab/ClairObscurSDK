"""Normal game-owned zone entry, using the live level table's main spawn tag.

The dedicated native operation copies FName/GameplayTag values from the verified
table on the game thread. It does not expose raw FName IDs or arbitrary writes.
"""
import re
import struct
from . import _query
from .catalog import capture_matching, capture_selected
from ._reader import ReadBatch
from .cinematics.original_game_action import controller_context, NotReady
from .invocation import InvocationError

SIZE=432
HEADER=struct.Struct('<4I')
IDENTITY=struct.Struct('<iiQ')
LIB='/Game/jRPGTemplate/Blueprints/Basics/FL_jRPG_CustomFunctionLibrary'
TABLE='/Game/Gameplay/LevelData/DT_LevelData.DT_LevelData'
TEXT=re.compile(r'[A-Za-z0-9_.]+\Z')

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
    with ReadBatch(pid,share=True):
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
    if type(data) is not bytes or len(data)!=SIZE or HEADER.unpack_from(data)[0]!=1 or HEADER.unpack_from(data)[1] not in (0,1) or any(HEADER.unpack_from(data)[2:]):raise ValueError('Invalid zone travel packet')
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

def travel_to_entrance(session,route,*,validate_only=False):
    session._check()
    transport=session._session._transport
    if not available(transport):raise RuntimeError('Normal zone travel requires SDK zone runtime v67 or newer')
    with ReadBatch(session.pid,share=True):
        before=controller_context(session)
        cat=capture_matching(session.pid,names=('DT_LevelData','ChangeMapByName','Default__FL_jRPG_CustomFunctionLibrary_C'),classes=('LocalPlayer','BP_jRPG_GI_Custom_C'))
        cat=cat.with_observations(capture_selected(session.pid,(before['controller'][1:],)))
        objects=(
            _one(o for o in cat.objects if cat.path_name(o)==TABLE),
            _one(o for o in cat.objects if cat.path_name(o)==LIB+'.FL_jRPG_CustomFunctionLibrary_C:ChangeMapByName'),
            _one(o for o in cat.objects if cat.path_name(o)==LIB+'.Default__FL_jRPG_CustomFunctionLibrary_C'),
            _one(o for o in cat.objects if o.class_name=='BP_jRPG_GI_Custom_C' and not o.object_flags&0x30),
            _one(o for o in cat.objects if o.class_name=='LocalPlayer' and not o.object_flags&0x30),
            cat.by_index[before['controller'][1]],
        )
        data=bytearray(SIZE);HEADER.pack_into(data,0,1,0 if validate_only else 1,0,0)
        for i,o in enumerate(objects):IDENTITY.pack_into(data,16+i*16,o.index,o.serial,o.address)
        for key,at,width in (('level_id',112,96),('asset_name',208,96),('entrance_tag',304,128)):
            value=route[key]
            if type(value) is not str or not TEXT.fullmatch(value):raise ValueError('Invalid route '+key)
            encoded=value.encode('ascii')
            if len(encoded)>=width:raise ValueError('Route name too long')
            data[at:at+width]=encoded.ljust(width,b'\0')
    data=bytes(data);validate_request(data)
    try:response=transport._command('zone-travel',data)
    except Exception as error:raise InvocationError('Normal travel transport did not confirm outcome',outcome='unknown') from error
    return decode_reply(data,response)
