"""Exact movie-source metadata for simple game-authored pre-rendered timelines."""
import re
from .authored_cast import bindings


def _constant_source(channel):
    """Accept redundant keys only when every value equals the default movie.

    Shipping credit timelines include a key at zero even though the same movie
    is also their default. Such a channel never switches clips. A null default,
    changed movie, incomplete array or malformed key is a different timeline.
    """
    if type(channel) is not dict or channel.get('complete') is not True or channel.get('errors'):
        raise ValueError('Complete authored media channel required')
    data=channel.get('fields',{})
    arrays=[]
    for name in ('Times','Values'):
        rows=data.get(name,{})
        if (rows.get('complete') is not True or type(rows.get('array')) is not list or
                type(rows.get('length')) is not int or not 0<=rows['length']<=4096 or
                rows['length']!=len(rows['array'])):
            raise ValueError('Keyed movie sources require complete matching arrays')
        arrays.append(rows['array'])
    times,values=arrays
    if len(times)!=len(values):raise ValueError('Keyed movie sources require complete matching arrays')
    def path(value):
        if type(value) is not dict or value.get('complete') is not True or value.get('errors'):
            raise ValueError('Complete default movie source required')
        hard=value.get('fields',{}).get('HardPtr',{})
        result=hard.get('object_path')
        if hard.get('class')!='FileMediaSource' or type(result) is not str or not result.startswith('/Game/'):
            raise ValueError('An exact game FileMediaSource is required')
        return result
    result=path(data.get('DefaultValue',{}));previous=None
    for time,value in zip(times,values):
        at=time.get('fields',{}).get('Value') if type(time) is dict else None
        if (type(time) is not dict or time.get('complete') is not True or time.get('errors') or
                time.get('struct')!='/Script/CoreUObject.FrameNumber' or type(at) is not int or
                not -(1<<31)<=at<(1<<31) or (previous is not None and at<=previous)):
            raise ValueError('Keyed movie sources require ordered complete frame keys')
        if path(value)!=result:raise ValueError('Keyed movie sources require a media timeline adapter')
        previous=at
    return result


def _media_actor(graph):
    """Find the single root movie actor without confusing it with scene cast.

    Other cast and camera actors may coexist. A nested movie requires one
    proven unit-speed occurrence; repeated movies need a separate adapter.
    """
    actors=[row for row in bindings(graph) if row['kind']=='spawnable' and row['template'] and
            row['template']['class']=='BP_MediaPlayer_C']
    if not actors:return None
    if len(actors)!=1:raise ValueError('Multiple authored movies require a media timeline adapter')
    if actors[0]['sequence']!=graph['sequence']:
        from .authored_media_occurrence import occurrence
        occurrence(graph,actors[0]['sequence'])
    return actors[0]


def source(document):
    """Return the sole constant FileMediaSource, or None for an in-engine scene.

    A root movie can coexist with regular scene actors and camera cuts.
    Switching or multiple movies need a timeline adapter. Do not silently select
    a clip from an ambiguous channel or an unreachable child shot.
    """
    graph=document['source'];nodes=graph['nodes']
    # Most sources are in-engine. Do not make their existing playback depend
    # on decoding unrelated cast fields just to discover they have no movie.
    media_declared=False
    for node in nodes.values():
        declarations=node.get('fields',{}).get('Spawnables',{}).get('array',())
        for declaration in declarations:
            template=declaration.get('fields',{}).get('ObjectTemplate')
            # Some authored bindings have no template. They are not media
            # declarations and must not prevent an in-engine scene opening.
            if type(template) is dict and template.get('class')=='BP_MediaPlayer_C':media_declared=True
    if not media_declared:return None
    actor=_media_actor(graph)
    if actor is None:return None
    if graph.get('pending'):raise ValueError('Complete media source graph required')
    candidates=[]
    for track in actor['tracks']:
        node=nodes.get(track,{})
        if node.get('class_name')!='MovieSceneObjectPropertyTrack':continue
        fields=node['fields'];binding=fields.get('PropertyBinding',{})
        if binding.get('fields',{}).get('PropertyName')!='MediaSource':continue
        if binding.get('fields',{}).get('PropertyPath')!='MediaSource':raise ValueError('Exact media property path required')
        if binding.get('complete') is not True or binding.get('errors'):raise ValueError('Complete media property binding required')
        refs=fields.get('Sections',{})
        if refs.get('complete') is not True or refs.get('length')!=1 or len(refs.get('array',()))!=1:
            raise ValueError('One constant authored media section required')
        section=nodes.get(refs['array'][0].get('object_path'),{})
        if section.get('class_name')!='MovieSceneObjectPropertySection':raise ValueError('Authored media section is unavailable')
        channel=section['fields'].get('ObjectChannel',{})
        candidates.append(_constant_source(channel))
    if len(candidates)!=1:raise ValueError('The authored movie source is missing or ambiguous')
    return candidates[0]


def movie_path(value):
    """Accept direct installed-content movie paths; never follow developer paths."""
    if type(value) is not str or re.fullmatch(r'\./Movies/[A-Za-z0-9_ .-]+\.mp4',value) is None or '..' in value:
        raise ValueError('The media source must name a direct installed Movies MP4')
    return value


def resolve(scope,path):
    """Read the current retained asset, rather than trusting a saved filename."""
    from ..assets import load_asset
    from ..values import capture_selected_values
    asset=load_asset(scope,path).return_value
    if asset is None or asset.class_name!='FileMediaSource':raise ValueError('Authored FileMediaSource is unavailable')
    _,rows=capture_selected_values(scope.pid,((asset.index,asset.serial,asset.address),),fields=('FilePath',))
    row=rows.get(asset.index)
    if row is None or row.errors or row.truncated or len(row.values)!=1:raise ValueError('Complete current media file path required')
    values=[value for key,value in row.values.items() if key[1]=='FilePath']
    if len(values)!=1:raise ValueError('Authored media file path is unavailable')
    return movie_path(values[0])


def suppression_sections(document):
    """Find keyless, default-visible movie sections needing private activity edits."""
    actor=_media_actor(document['source'])
    if actor is None:return ()
    nodes=document['source']['nodes'];result=[]
    for track in actor['tracks']:
        node=nodes.get(track,{})
        if node.get('class_name')!='MovieSceneSpawnTrack':continue
        refs=node.get('fields',{}).get('Sections',{})
        from .authored_media_occurrence import _array
        for ref in _array(refs):
            path=ref.get('object_path');section=nodes.get(path,{})
            if section.get('class_name')!='MovieSceneSpawnSection':raise ValueError('Movie spawn section required')
            curve=section.get('fields',{}).get('BoolCurve',{})
            if curve.get('complete') is not True or curve.get('errors'):raise ValueError('Complete movie spawn curve required')
            fields=curve.get('fields',{})
            if fields.get('DefaultValue') is not True:continue
            if fields.get('bHasDefaultValue') is not True or _array(fields.get('Times',{})) or _array(fields.get('Values',{})):
                raise ValueError('Default-visible keyed movies require another spawn adapter')
            if section['fields'].get('bIsActive') is not True:raise ValueError('Active movie spawn section required')
            result.append(path)
    if len(result)>1:raise ValueError('One default-visible movie spawn interval required')
    return tuple(result)


def _default_spawn_interval(document,actor,section):
    from .authored_media_occurrence import _range
    nodes=document['source']['nodes']
    start,end=_range(nodes[actor['scene']]['fields'].get('PlaybackRange',{}))
    scene_start,scene_end=start,end
    bounds=nodes[section]['fields'].get('SectionRange',{})
    if bounds.get('complete') is not True or bounds.get('errors'):raise ValueError('Complete movie spawn range required')
    rows=bounds.get('frame_range',{})
    for name,kind in (('lower','inclusive'),('upper','exclusive')):
        row=rows.get(name,{})
        if row.get('kind')=='open':continue
        if row.get('kind')!=kind or type(row.get('value')) is not int:raise ValueError('Half-open movie spawn range required')
        if name=='lower':start=max(start,row['value'])
        else:end=min(end,row['value'])
    edit=document.get('section_edits',{}).get(section)
    if edit is not None:
        if type(edit.get('start')) is not int or type(edit.get('end')) is not int or edit['end']<=edit['start']:
            raise ValueError('Finite edited movie range required')
        start,end=max(scene_start,edit['start']),min(scene_end,edit['end'])
    if end<=start:raise ValueError('Movie spawn interval is empty')
    return start,end


def playback_document(document):
    """Suppress the original media actor only in the private playback copy.

    Its original Blueprint must not race the separately owned video widget.
    The audio/event timeline and the user's saved document remain unchanged.
    Existing curve-edit validation proves the exact source keys before writes.
    """
    if source(document) is None:raise ValueError('A simple authored movie is required')
    from . import authored_timeline
    result=authored_timeline.validate(document);nodes=result['source']['nodes']
    actor=_media_actor(result['source'])
    sections=[]
    for track in actor['tracks']:
        node=nodes.get(track,{})
        if node.get('class_name')!='MovieSceneSpawnTrack':continue
        refs=node['fields'].get('Sections',{})
        if refs.get('complete') is not True or refs.get('length')!=len(refs.get('array',())):
            raise ValueError('Complete media spawn sections required')
        sections.extend(row['object_path'] for row in refs['array'])
    if not sections:raise ValueError('An authored media spawn track is required')
    activity_sections=suppression_sections(result)
    for section in sections:
        if section in activity_sections:continue
        node=nodes.get(section,{})
        if node.get('class_name')!='MovieSceneSpawnSection':raise ValueError('An authored media spawn section is required')
        curve=node['fields'].get('BoolCurve',{});fields=curve.get('fields',{})
        if curve.get('complete') is not True or curve.get('errors') or fields.get('bHasDefaultValue') is not True or fields.get('DefaultValue') is not False:
            raise ValueError('A complete default-hidden media spawn channel is required')
        kind,keys=authored_timeline.channel(result,section,['BoolCurve'])
        if kind!='MovieSceneBoolChannel':raise ValueError('A Boolean media spawn channel is required')
        edits={e['index']:e for e in document.get('key_edits',()) if e['section']==section and e['path']==['BoolCurve']}
        for index,key in enumerate(keys):
            result=authored_timeline.edit_key(result,section,['BoolCurve'],index,at=edits.get(index,key)['at'],value=False)
    return result


def playback_clock(document,rate):
    """Return visible start/end and the original film origin in player frames.

    A missing end means the movie's duration is the endpoint. More than one
    interval is not a single-clock movie and needs a separate adapter. A parent
    may clip the visible start without resetting the film's playback clock.
    """
    from fractions import Fraction
    from .authored_timeline import channel
    if source(document) is None:raise ValueError('A simple authored movie is required')
    if len(rate)!=2 or any(type(v) is not int or v<=0 for v in rate):raise ValueError('Positive player frame rate required')
    actor=_media_actor(document['source'])
    nodes=document['source']['nodes'];scene=nodes[actor['scene']]['fields']
    resolution=scene.get('TickResolution',{});fields=resolution.get('fields',{})
    n,d=fields.get('Numerator'),fields.get('Denominator')
    if resolution.get('complete') is not True or resolution.get('errors') or any(type(v) is not int or v<=0 for v in (n,d)):
        raise ValueError('Complete positive movie tick resolution required')
    starts=[];stops=[]
    activity_sections=suppression_sections(document)
    for track in actor['tracks']:
        node=nodes.get(track,{})
        if node.get('class_name')!='MovieSceneSpawnTrack':continue
        refs=node['fields'].get('Sections',{})
        if refs.get('complete') is not True or refs.get('length')!=len(refs.get('array',())):raise ValueError('Complete media spawn track required')
        for ref in refs['array']:
            section=ref['object_path'];curve=nodes[section]['fields']['BoolCurve']
            if section in activity_sections:
                start,end=_default_spawn_interval(document,actor,section)
                starts.append(start);stops.append(end);continue
            if curve.get('complete') is not True or curve.get('errors') or curve['fields'].get('DefaultValue') is not False or curve['fields'].get('bHasDefaultValue') is not True:
                raise ValueError('Default-hidden media spawn channel required')
            kind,keys=channel(document,section,['BoolCurve'])
            edits={e['index']:e for e in document.get('key_edits',()) if e['section']==section and e['path']==['BoolCurve']}
            keys=[dict(at=edits.get(i,key)['at'],value=edits.get(i,key)['value']) for i,key in enumerate(keys)]
            if kind!='MovieSceneBoolChannel':raise ValueError('Boolean movie spawn channel required')
            previous=False
            for key in keys:
                if key['value'] and not previous:starts.append(key['at'])
                if not key['value'] and previous:stops.append(key['at'])
                previous=key['value']
    if len(starts)!=1:raise ValueError('One authored movie start is required')
    if len(stops)>1 or (stops and stops[0]<=starts[0]):raise ValueError('One authored movie interval is required')
    convert=lambda tick:float(Fraction(tick*d*rate[0],n*rate[1]))
    start=convert(starts[0]);end=convert(stops[0]) if stops else None
    origin=start
    if actor['sequence']!=document['source']['sequence']:
        from .authored_media_occurrence import occurrence
        offset,lower,upper=occurrence(document['source'],actor['sequence'],section_edits=document.get('section_edits',{}))
        factor=Fraction(rate[0],rate[1]);start+=float(offset*factor)
        origin=start
        end=min(float(upper*factor),float(offset*factor)+end) if end is not None else float(upper*factor)
        start=max(start,float(lower*factor))
        if end<=start:raise ValueError('Authored movie is outside its nested occurrence')
    return start,end,origin


def playback_window(document,rate):
    """Return visible bounds; playback_clock also preserves the film origin."""
    return playback_clock(document,rate)[:2]


def start_frame(document,rate):
    """Return the movie start for existing callers."""
    return playback_window(document,rate)[0]
