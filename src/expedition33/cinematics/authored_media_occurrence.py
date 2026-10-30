"""Copied-graph timing for a single, unit-speed nested movie occurrence."""
from fractions import Fraction


def _rate(scene):
    value=scene.get('TickResolution',{})
    fields=value.get('fields',{});n=fields.get('Numerator');d=fields.get('Denominator')
    if value.get('complete') is not True or value.get('errors') or any(type(v) is not int or v<=0 for v in (n,d)):
        raise ValueError('Complete positive nested movie tick resolution required')
    return Fraction(n,d)


def _range(value):
    if value.get('complete') is not True or value.get('errors'):raise ValueError('Complete nested movie range required')
    bounds=value.get('frame_range',{});result=[]
    for key,kind in (('lower','inclusive'),('upper','exclusive')):
        row=bounds.get(key,{})
        if row.get('kind')!=kind or type(row.get('value')) is not int:raise ValueError('Finite half-open nested movie range required')
        result.append(row['value'])
    if result[1]<=result[0]:raise ValueError('Empty nested movie range')
    return result


def _array(value):
    rows=value.get('array')
    if value.get('complete') is not True or type(rows) is not list or type(value.get('length')) is not int or len(rows)!=value['length']:
        raise ValueError('Complete nested movie reference array required')
    return rows


def occurrence(graph,target,*,section_edits=None):
    """Return root-clock offset and visible bounds, in rational seconds.

    Traverse actual scene/track/section links. Shared sequence assets remain
    separate occurrences; cycles and multiple target occurrences are errors.
    This adapter supports unit speed only, with no looping or trim offsets.
    """
    nodes=graph['nodes'];root=graph['sequence'];found=[];visits=0
    reachable={};reach_visits=0
    section_edits={} if section_edits is None else section_edits
    def scene(path):
        node=nodes.get(path,{})
        if node.get('class_name')!='LevelSequence':raise ValueError('Nested movie LevelSequence required')
        ref=node.get('fields',{}).get('MovieScene',{})
        value=nodes.get(ref.get('object_path'),{})
        if ref.get('class')!='MovieScene' or value.get('class_name')!='MovieScene':raise ValueError('Nested movie scene unavailable')
        return value['fields']
    def reaches_target(path,active=()):
        # Clock restrictions belong to the movie's ancestry, not sibling 3D
        # shots whose clocks are evaluated by the native sequence player.
        nonlocal reach_visits
        if path in active:raise ValueError('Cyclic nested movie hierarchy')
        if path in reachable:return reachable[path]
        reach_visits+=1
        if reach_visits>256 or len(active)>=32:raise ValueError('Nested movie occurrence traversal limit')
        fields=scene(path);result=path==target
        for ref in _array(fields.get('Tracks',{})):
            track=nodes.get(ref.get('object_path'),{})
            if track.get('class_name') not in ('MovieSceneCinematicShotTrack','MovieSceneSubTrack'):continue
            for ref in _array(track.get('fields',{}).get('Sections',{})):
                section=nodes.get(ref.get('object_path'),{})
                if section.get('class_name') not in ('MovieSceneCinematicShotSection','MovieSceneSubSection'):
                    raise ValueError('Unsupported nested movie section')
                sf=section.get('fields',{});child=sf.get('SubSequence')
                if child is None:continue
                if child.get('class')!='LevelSequence':raise ValueError('Unsupported nested movie sequence class')
                if type(sf.get('bIsActive')) is not bool:raise ValueError('Known nested movie section activity required')
                if sf['bIsActive']:
                    child_result=reaches_target(child.get('object_path'),active+(path,))
                    result=result or child_result
        reachable[path]=result
        return result
    reaches_target(root)
    def visit(path,offset,window,active):
        nonlocal visits
        visits+=1
        if visits>256 or len(active)>=32:raise ValueError('Nested movie occurrence traversal limit')
        if path in active:raise ValueError('Cyclic nested movie hierarchy')
        fields=scene(path);rate=_rate(fields)
        if path==target:found.append((offset,*window))
        for ref in _array(fields.get('Tracks',{})):
            track=nodes.get(ref.get('object_path'),{})
            if track.get('class_name') not in ('MovieSceneCinematicShotTrack','MovieSceneSubTrack'):continue
            for ref in _array(track.get('fields',{}).get('Sections',{})):
                section=nodes.get(ref.get('object_path'),{})
                if section.get('class_name') not in ('MovieSceneCinematicShotSection','MovieSceneSubSection'):
                    raise ValueError('Unsupported nested movie section')
                sf=section.get('fields',{});child=sf.get('SubSequence',{})
                if child is None:continue
                if child.get('class')!='LevelSequence':raise ValueError('Unsupported nested movie sequence class')
                if type(sf.get('bIsActive')) is not bool:raise ValueError('Known nested movie section activity required')
                if not sf['bIsActive'] or not reachable.get(child.get('object_path'),False):continue
                start,end=_range(sf.get('SectionRange',{}))
                edit=section_edits.get(ref.get('object_path'))
                if edit is not None:
                    start,end=edit.get('start'),edit.get('end')
                    if type(start) is not int or type(end) is not int or end<=start:raise ValueError('Finite edited nested movie range required')
                parameters=sf.get('Parameters',{}).get('fields',{})
                if parameters.get('bCanLoop') is not False or type(parameters.get('TimeScale')) not in (int,float) or parameters['TimeScale']!=1:
                    raise ValueError('Nested movie loops and speed changes require another clock adapter')
                for key in ('StartFrameOffset','EndFrameOffset','FirstLoopStartFrameOffset'):
                    f=parameters.get(key,{})
                    if f.get('complete') is not True or f.get('errors') or type(f.get('fields',{}).get('Value')) is not int or f['fields']['Value']!=0:
                        raise ValueError('Nested movie trim offsets require another clock adapter')
                child_path=child.get('object_path');child_scene=scene(child_path);child_start,_=_range(child_scene.get('PlaybackRange',{}))
                lower=max(window[0],offset+start/rate);upper=min(window[1],offset+end/rate)
                if upper<=lower:continue
                visit(child_path,offset+start/rate-child_start/_rate(child_scene),(lower,upper),active+(path,))
    root_scene=scene(root);lower,upper=_range(root_scene.get('PlaybackRange',{}));rate=_rate(root_scene)
    visit(root,Fraction(0),(lower/rate,upper/rate),())
    if len(found)!=1:raise ValueError('Exactly one reachable authored movie occurrence required')
    return found[0]
