"""Stage imported LevelSequences using their own root actor transforms.

The anchor changes only the owned player's instance origin. Source graphs and
assets remain immutable, and no original story GameAction is dispatched.
"""
import math
from statistics import median
from types import SimpleNamespace
from expedition33.cinematics.authored_cast import bindings


def channel_start(channel):
    if type(channel) is not dict or channel.get('errors') or channel.get('complete') is not True:return None
    fields=channel.get('fields',{})
    values=fields.get('Values',{})
    rows=values.get('array',[]) if values.get('complete') is True else []
    if rows:
        row=rows[0]
        value=row.get('fields',{}).get('Value') if row.get('complete') is True and not row.get('errors') else None
    else:value=fields.get('DefaultValue') if fields.get('bHasDefaultValue') is True else None
    return float(value) if type(value) in (int,float) and math.isfinite(value) and abs(value)<=1.e7 else None


def source_anchor(graph):
    """Prefer cinematic characters, then cameras, then other root spawnables.

    Component bindings are deliberately excluded: their local translations
    would drag a scene's inferred world center toward zero. Give every actor
    one vote even when it has multiple shots or transform sections.
    """
    nodes=graph['nodes'];groups=([],[],[])
    for row in bindings(graph):
        if row['kind']!='spawnable' or not row['template']:continue
        cls=row['template']['class'];points=[]
        for track_path in row['tracks']:
            track=nodes.get(track_path,{})
            if track.get('class_name')!='MovieScene3DTransformTrack':continue
            sections=track.get('fields',{}).get('Sections',{})
            if sections.get('complete') is not True:continue
            for reference in sections.get('array',()):
                path=reference.get('object_path','')
                if not path.startswith(track_path+'.'):continue
                node=nodes.get(path,{})
                if node.get('class_name')!='MovieScene3DTransformSection':continue
                channels=node.get('fields',{}).get('Translation',{}).get('static_array',())
                if len(channels)!=3:continue
                point=tuple(channel_start(c) for c in channels)
                if all(v is not None for v in point):points.append(point)
        if points:
            group=0 if cls.startswith('BP_Cine_') else 1 if cls in ('CameraActor','CineCameraActor') else 2
            groups[group].append(tuple(median(p[i] for p in points) for i in range(3)))
    points=next((p for p in groups if p),())
    return tuple(median(p[i] for p in points) for i in range(3)) if points else (0.,0.,0.)


def supports_imported_profile(document):
    if type(document) is not dict:return False
    graph=document.get('source',{});path=graph.get('sequence');nodes=graph.get('nodes',{})
    if type(path) is not str or not path.startswith('/Game/') or type(nodes) is not dict:return False
    return nodes.get(path,{}).get('class_name')=='LevelSequence'


def imported_profile(document):
    if not supports_imported_profile(document):return None
    graph=document['source'];path=graph['sequence']
    try:anchor=source_anchor(graph)
    except (ValueError,KeyError,TypeError):
        # Missing cast metadata is not a reason to disable audio, media or
        # otherwise valid empty sequences. Their native player still validates
        # the actual asset and its frame range before evaluation.
        anchor=(0.,0.,0.)
    return SimpleNamespace(sequence=path,saved_id=path.rsplit('.',1)[-1].removeprefix('MCS_'),anchor=anchor)
