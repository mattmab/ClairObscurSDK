"""Bounded timing observations plus one fixed read-only clock getter; no raw offsets."""
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import math
from expedition33.catalog import capture_matching, capture_selected
from expedition33.reflection import describe
from expedition33.enums import describe_enums, EnumValue
from expedition33._pod_values import NumericStructValue
from expedition33.values import read_values, read_object_reference
from expedition33.cinematics.title_replay import SEQUENCE
from timing_metadata_names import METADATA_NAMES


def copied_json(value, *, depth=0, budget=None):
    if budget is None: budget=[4096]
    budget[0]-=1
    if budget[0]<0 or depth>8: return {'unknown':'serialization bound reached'}
    recurse=lambda v:copied_json(v,depth=depth+1,budget=budget)
    if value is None or type(value) in (bool,int): return value
    if type(value) is float: return value if math.isfinite(value) else {'unknown':'nonfinite float'}
    if type(value) is str: return value if len(value)<=4096 else {'prefix':value[:4096],'truncated':True}
    if is_dataclass(value):
        return {'dataclass':type(value).__name__, **{f.name:recurse(getattr(value,f.name)) for f in fields(value)[:32]}}
    if isinstance(value,Mapping):
        rows=list(value.items())[:128]
        return {'entries':[{'key':recurse(k),'value':recurse(v)} for k,v in rows], 'truncated':len(value)>128}
    if isinstance(value,(tuple,list,set,frozenset)):
        return {'items':[recurse(v) for v in list(value)[:128]],'truncated':len(value)>128}
    return {'unknown':'unsupported copied type '+type(value).__name__}


def _timing(name):
    return any(part in name.casefold() for part in ('time','frame','clock','settings','rate','status','loop','tick','playback'))


def _enrich_structs(catalog, properties):
    """One bounded metadata-preparation pass, before stored values are read."""
    pending=[(p, 0) for p in properties if p.get('type') == 'StructProperty']
    seen=set(); errors=[]
    while pending:
        prop, depth=pending.pop(0)
        index=prop['struct_index']
        if index in seen:continue
        if depth>=4 or len(seen)>=32:
            errors.append('Struct metadata dependency bound reached'); break
        seen.add(index)
        try:
            observed=catalog.by_index[index]
            if observed.serial != prop['struct_serial'] or observed.name != prop['struct_name']:
                raise RuntimeError('Described struct dependency identity changed')
            fresh=capture_selected(catalog.pid,((observed.index,observed.serial,observed.address),))
            catalog=catalog.with_observations(fresh)
            descriptor=describe(catalog,(catalog.by_index[index],))[index]
            pending.extend((p,depth+1) for p in descriptor.properties if p.get('type')=='StructProperty')
        except Exception as error:
            errors.append('Struct dependency '+prop.get('struct_name','?')+': '+str(error))
    return catalog, errors


def _sample(catalog,obj):
    row={'identity':copied_json(obj),'schema':[], 'values':[], 'unknowns':[]}
    try:
        cls=catalog.by_index[obj.class_index]
        descriptor=describe(catalog,(cls,))[cls.index]
        selected=[p for p in descriptor.properties if _timing(p['name'])]
        row['schema']=[copied_json(dict(p)) for p in selected[:96]]
        if len(selected)>96:row['unknowns'].append('Timing field schema exceeds 96-field bound')
    except Exception as error:
        row['unknowns'].append('Fresh descriptor unavailable: '+str(error))
        return row
    try:
        catalog, dependency_errors = _enrich_structs(catalog, selected[:96])
        row['unknowns'].extend(dependency_errors)
        values=read_values(catalog,obj)
        for p in selected[:96]:
            key=(p['owner_index'],p['name'])
            item=dict(owner=p['owner'],name=p['name'],type=p['type'],truncated=key in values.truncated)
            if key in values.values: item['value']=copied_json(values.values[key])
            else:item['unknown']=str(values.errors.get(key,'Stored field not decoded'))
            row['values'].append(item)
        if not any(p['name'] in ('CurrentTime','CurrentPosition','TimeCursorPosition') for p in selected):
            row['unknowns'].append('No supported reflected current-time field identified; playing/status does not prove time advancement')
    except Exception as error:row['unknowns'].append('Stored values unavailable: '+str(error))
    return row


def inspect_current_time(scope, catalog, player):
    """Fixed return-only call; unavailable runtimes are never dispatched."""
    result={'invoked': False}
    planner=None
    try:
        transport=scope._session._transport
        version=getattr(transport,'frame_time_values_protocol',0)
        if type(version) is not int or version!=1 or not getattr(scope,'supports_frame_time_values',False):
            result['unknown']='Verified frame_time_values_protocol=1 is required'
            return result
        owner=catalog.find_class('MovieSceneSequencePlayer').index
        functions=[o for o in catalog.objects if o.outer_index==owner and
            o.name=='GetCurrentTime' and o.class_name=='Function']
        if len(functions)!=1:raise RuntimeError('Expected one exact GetCurrentTime function')
        fn=functions[0]
        descriptor=describe(catalog,(fn,))[fn.index]
        result['schema']=copied_json(descriptor)
        props=descriptor.properties
        if (len(props)!=1 or not props[0]['flags'] & 0x400 or
                props[0].get('type')!='StructProperty' or props[0].get('struct_name')!='QualifiedFrameTime'):
            raise RuntimeError('Current-time getter is not a no-argument QualifiedFrameTime return')
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        call=planner.prepare(player,fn)
        result['attempted']=True
        with call.invoke() as reply:
            value=reply.return_value
            if not isinstance(value,NumericStructValue) or value.path!='/Script/CoreUObject.QualifiedFrameTime':
                raise RuntimeError('Current-time getter returned an unsupported copied value')
            frame=value['Time']['FrameNumber']['Value']; sub=value['Time']['SubFrame']
            numerator=value['Rate']['Numerator']; denominator=value['Rate']['Denominator']
            result.update(invoked=True,frame=frame,subframe=sub,numerator=numerator,denominator=denominator)
            if (type(frame) is not int or type(sub) not in (int,float) or not math.isfinite(sub) or
                    not 0<=sub<1 or type(numerator) is not int or type(denominator) is not int or
                    numerator<=0 or denominator<=0):
                result['seconds_unknown']='Invalid frame fraction or nonpositive frame rate'
            else:result['seconds']=(frame+sub)*denominator/numerator
    except Exception as error:
        result['unknown']=str(error)
        result['outcome']=getattr(error,'outcome',None)
    finally:
        if planner is not None:planner.close()
    return result


def inspect_clock_source(scope, catalog, movie):
    """One exact no-argument reflected getter, if this build exposes it."""
    result={'invoked': False}
    planner=None
    try:
        owner=catalog.find_class('MovieScene').index
        functions=[o for o in catalog.objects if o.outer_index==owner and
            o.name=='GetClockSource' and o.class_name=='Function']
        if len(functions)!=1:
            result['unknown']='MovieScene.GetClockSource is not exposed exactly once as a reflected function'
            return result
        fn=functions[0]
        descriptor=describe(catalog,(fn,))[fn.index]
        result['schema']=copied_json(descriptor)
        props=descriptor.properties
        if (len(props)!=1 or not props[0]['flags'] & 0x400 or
                props[0].get('type') not in ('EnumProperty','ByteProperty') or
                props[0].get('enum_name')!='EUpdateClockSource'):
            raise RuntimeError('Clock getter is not the verified no-argument EUpdateClockSource return')
        prop=props[0]
        enum=catalog.by_index[prop['enum_index']]
        if enum.serial!=prop['enum_serial']:
            raise RuntimeError('Clock return enum identity changed')
        members=describe_enums(catalog,(enum,))[enum.index].members
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        call=planner.prepare(movie,fn)
        result['attempted']=True
        with call.invoke() as reply:
            value=reply.return_value
            if isinstance(value,EnumValue):
                if value.enum != enum:raise RuntimeError('Clock getter returned another enum')
                number=value.value
            elif type(value) is int:number=value
            else:raise RuntimeError('Clock getter returned unsupported copied value')
            names=[m.name for m in members if m.value==number]
            if not names:raise RuntimeError('Clock getter returned unknown enum member')
            result.update(invoked=True,value=number,names=names)
    except Exception as error:
        result['unknown']=str(error)
        result['outcome']=getattr(error,'outcome',None)
    finally:
        if planner is not None:planner.close()
    return result


def inspect_title_timing(mod):
    replay=mod.title_replay
    sequence=getattr(replay,'sequence',None)
    if sequence is None or sequence.uncertain or sequence.state not in ('ready','playing','paused','stopped'):
        raise RuntimeError('A known owned title sequence is required')
    scope=sequence.scope;scope._check()
    player,actor=sequence.player,sequence.actor
    if player is None or actor is None:raise RuntimeError('Owned player/actor identities unavailable')
    catalog=capture_matching(scope.pid,names=tuple(dict.fromkeys((*METADATA_NAMES,'GetCurrentTime','QualifiedFrameTime','FrameTime','GetClockSource',
        'MovieSceneSequenceTickInterval','MovieSceneSequenceLoopCount','EMovieSceneCompletionModeOverride'))))
    catalog=catalog.with_observations(capture_selected(scope.pid,tuple((o.index,o.serial,o.address) for o in (player,actor))))
    result={'read_only':True,'atomic':False,'pid':scope.pid,'sequence_state':sequence.state,
        'session_identity':getattr(scope._session._transport,'button_action_session',None),'objects':{},'unknowns':[]}
    result['objects']['player']=_sample(catalog,player)
    result['objects']['actor']=_sample(catalog,actor)
    result['current_time_getter']=inspect_current_time(scope,catalog,player)
    result['frame_time_struct_schemas']={}
    for name in ('FrameNumber','FrameTime','FrameRate','QualifiedFrameTime'):
        try:
            types=[o for o in catalog.objects if o.name==name and o.class_name=='ScriptStruct']
            if len(types)!=1:raise RuntimeError('Expected one exact frame-time ScriptStruct')
            result['frame_time_struct_schemas'][name]=copied_json(describe(catalog,(types[0],))[types[0].index])
        except Exception as error:
            result['frame_time_struct_schemas'][name]={'unknown':str(error)}
    objects=[player,actor]
    try:
        asset,catalog=read_object_reference(catalog,player,catalog.by_index[catalog.find_class('MovieSceneSequencePlayer').index],'Sequence')
        if asset is None or catalog.path_name(asset)!=SEQUENCE:raise RuntimeError('Player asset is not the exact Prologue title')
        movie,catalog=read_object_reference(catalog,asset,catalog.by_index[catalog.find_class('LevelSequence').index],'MovieScene')
        if movie is None or movie.class_name!='MovieScene':raise RuntimeError('Exact asset MovieScene reference unavailable')
        objects.extend((asset,movie))
        result['objects']['asset']=_sample(catalog,asset)
        result['objects']['movie_scene']=_sample(catalog,movie)
        result['clock_source_getter']=inspect_clock_source(scope,catalog,movie)
    except Exception as error:result['unknowns'].append('Asset clock path unavailable: '+str(error))
    scope._check()
    if mod.title_replay is not replay or replay.sequence is not sequence or sequence.player is not player or sequence.actor is not actor:
        raise RuntimeError('Replay ownership changed during observation')
    capture_selected(scope.pid,tuple((o.index,o.serial,o.address) for o in objects))
    return result

