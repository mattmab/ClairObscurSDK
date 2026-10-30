"""Project root authored sections onto the native player's frame ruler.

Nested sections keep their own time spaces in the property picker. They need
subsequence offset/rate/loop transforms before they can share this ruler.
"""
from fractions import Fraction
from expedition33.cinematics.authored_timeline import source_range


def _scene(nodes,sequence):
    path=nodes[sequence]['fields'].get('MovieScene',{}).get('object_path')
    scene=nodes.get(path)
    if scene is None or scene['class_name']!='MovieScene':raise ValueError('MovieScene metadata is unavailable')
    rate=scene['fields'].get('TickResolution',{})
    fields=rate.get('fields',{});n=fields.get('Numerator');d=fields.get('Denominator')
    if rate.get('complete') is not True or rate.get('errors'):raise ValueError('Tick resolution is incomplete')
    if any(type(v) is not int or v<=0 for v in (n,d)):raise ValueError('Tick resolution is invalid')
    return path,scene,Fraction(n,d)


def _range(document,path):
    start,end=source_range(document,path)
    edit=document.get('section_edits',{}).get(path)
    return (edit['start'],edit['end']) if edit else (start,end)


def project_sections(document,player_rate):
    """Return bounded sections in root player frames and explicit omissions.

    Each shot instance carries its own affine transform and visible interval.
    Positive, nonlooping subsequences use their own playback lower bound and
    native start offset. Unsupported loop/reverse/hold mappings stay explicit.
    """
    n,d=player_rate
    if any(type(v) is not int or v<=0 for v in player_rate):raise ValueError('Invalid player frame rate')
    graph=document['source'];nodes=graph['nodes'];root=graph['sequence']
    _,_,root_rate=_scene(nodes,root)
    # Index by exact MovieScene path prefix once per projection. A reused shot
    # still receives a separate timing transform on each visit; only immutable
    # source rows are shared within this call. Never retain edits across draws.
    sections={path:[] for path,node in nodes.items() if node['class_name']=='MovieScene'}
    for path,node in nodes.items():
        if 'Section' not in node['class_name']:continue
        parts=path.split('.')
        for i in range(1,len(parts)):
            scene_path='.'.join(parts[:i])
            if scene_path in sections:sections[scene_path].append((path,node))
    rows=[];issues=[]
    def visit(sequence,scale,origin,window,ancestry,instance):
        if sequence in ancestry or len(ancestry)>=16:
            issues.append('Recursive or excessively nested shot: '+sequence);return
        try:scene_path,scene,rate=_scene(nodes,sequence)
        except (ValueError,KeyError) as error:issues.append(str(error)+': '+sequence);return
        for path,node in sections[scene_path]:
            if len(rows)>=2048:raise ValueError('Projected section limit exceeded')
            try:start,end=_range(document,path)
            except ValueError:continue
            if start is None or end is None:continue
            left,right=scale*start+origin,scale*end+origin
            if window is not None:left,right=max(left,window[0]),min(right,window[1])
            if right<=left:continue
            rows.append(dict(path=path,name=node['class_name'].removeprefix('MovieScene'),
                start=left,end=right,instance=instance,depth=len(ancestry)))
            child=node['fields'].get('SubSequence',{}).get('object_path')
            if not child:continue
            try:
                _,child_scene,child_rate=_scene(nodes,child)
                params=node['fields'].get('Parameters',{});fields=params.get('fields',{})
                required=('TimeScale','StartFrameOffset','bCanLoop')
                if any(k not in fields or k in params.get('errors',{}) for k in required):raise ValueError('Incomplete shot timing')
                speed=fields['TimeScale']
                if type(speed) not in (float,int) or not 0<speed<=10000:raise ValueError('Unsupported shot playback rate')
                if fields['bCanLoop'] is not False:raise ValueError('Looping shot timing is not projected')
                offset=fields['StartFrameOffset']
                if offset.get('complete') is not True or offset.get('errors'):raise ValueError('Incomplete shot start offset')
                offset=offset.get('fields',{}).get('Value')
                if type(offset) is not int:raise ValueError('Invalid shot start offset')
                bounds=child_scene['fields'].get('PlaybackRange',{}).get('frame_range',{})
                lower=bounds.get('lower',{})
                if lower.get('kind') not in ('inclusive','exclusive') or type(lower.get('value')) is not int:
                    raise ValueError('Finite child playback start required')
                child_start=lower['value']+int(lower['kind']=='exclusive')+offset
                ratio=child_rate/rate*Fraction(str(speed))
                child_scale=scale/ratio
                child_origin=origin+scale*start-child_scale*child_start
            except (ValueError,KeyError,TypeError) as error:
                issues.append(str(error)+': '+path);continue
            visit(child,child_scale,child_origin,(left,right),ancestry+(sequence,),instance+(path,))
    visit(root,Fraction(n,d)/root_rate,Fraction(0),None,(),())
    if graph.get('pending'):issues.append('Source graph is incomplete')
    return tuple(rows),tuple(issues)


def root_sections(document, player_rate):
    numerator,denominator=player_rate
    if any(type(v) is not int or v<=0 for v in player_rate):
        raise ValueError('A positive native player frame rate is required')
    graph=document['source'];nodes=graph['nodes'];root=nodes[graph['sequence']]
    scene_path=root['fields'].get('MovieScene',{}).get('object_path')
    scene=nodes.get(scene_path)
    if scene is None or scene['class_name']!='MovieScene':
        raise ValueError('Root MovieScene metadata is unavailable')
    rate=scene['fields'].get('TickResolution',{})
    if rate.get('complete') is not True or rate.get('errors'):
        raise ValueError('Root tick resolution is incomplete')
    fields=rate.get('fields',{});tick_n=fields.get('Numerator');tick_d=fields.get('Denominator')
    if any(type(v) is not int or v<=0 for v in (tick_n,tick_d)):
        raise ValueError('Root tick resolution is invalid')
    scale=Fraction(numerator*tick_d,denominator*tick_n)
    rows=[]
    for path,node in nodes.items():
        if not path.startswith(scene_path+'.') or 'Section' not in node['class_name']:continue
        try:start,end=source_range(document,path)
        except ValueError:continue  # Open/opaque ranges have no finite marker.
        edit=document.get('section_edits',{}).get(path)
        if edit:start,end=edit['start'],edit['end']
        if start is None or end is None:continue
        rows.append(dict(path=path,name=node['class_name'].removeprefix('MovieScene'),
                         start=Fraction(start)*scale,end=Fraction(end)*scale))
    return tuple(rows)
