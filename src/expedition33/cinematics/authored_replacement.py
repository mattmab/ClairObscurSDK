"""Apply saved actor replacements to an owned original or copied timeline."""
from ..assets import load_asset
from ..values import capture_selected_values
from .authored_source import copied
from .authored_copy import signature
from .authored_references import reachable_sequences
import math
from contextlib import nullcontext


def placement_pose(edit,anchor,index,scene_yaw=0.):
    from .blueprint_actor import transform
    from .scene_transform import actor_placement
    placement=edit.get('placement',dict(offset=[300.,150.*index,0.],yaw=0.))
    location,yaw=actor_placement(anchor,placement['offset'],placement['yaw'],scene_yaw)
    half=math.radians(yaw)/2
    return transform((0.,0.,math.sin(half),math.cos(half),
        *location,0.,1.,1.,1.,0.))


def guid_fields(text):
    import re
    if type(text) is not str or re.fullmatch('[0-9a-f]{32}',text) is None or int(text,16)==0:
        raise ValueError('Canonical nonempty authored binding GUID required')
    def signed(n):return n-(1<<32) if n>=(1<<31) else n
    return {name:signed(int(text[i*8:(i+1)*8],16)) for i,name in enumerate('ABCD')}


def _sequence_signatures(scope,sequences):
    """Two fresh bounded projections instead of per-sequence reader round trips."""
    sequences=tuple(sequences)
    if not sequences or len(sequences)>128:raise ValueError('Bounded reachable sequence set required')
    key=lambda obj:(obj.index,obj.serial,obj.address)
    if len({key(o) for o in sequences})!=len(sequences):raise ValueError('Duplicate reachable sequence identity')
    catalog,values=capture_selected_values(scope.pid,tuple(key(o) for o in sequences),fields=('MovieScene',),references=True)
    def field(rows,index,name):
        value=rows.get(index)
        if value is None or value.errors or value.truncated or len(value.values)!=1:raise ValueError('Complete source '+name+' required')
        entries=[v for k,v in value.values.items() if k[1]==name]
        if len(entries)!=1 or entries[0] is None:raise ValueError('Complete source '+name+' required')
        return entries[0]
    if set(values)!={o.index for o in sequences}:raise ValueError('Incomplete sequence signature batch')
    scenes=[]
    for obj in sequences:
        scene=field(values,obj.index,'MovieScene')
        if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(obj.index,obj.serial):
            raise ValueError('Sequence MovieScene ownership changed')
        scenes.append(scene)
    catalog,values=capture_selected_values(scope.pid,tuple(key(o) for o in scenes),fields=('Signature',),references=True)
    if set(values)!={o.index for o in scenes}:raise ValueError('Incomplete sequence signature batch')
    return tuple(signature({'fields':{'Signature':copied(field(values,scene.index,'Signature'),catalog)}}) for scene in scenes)


def sources_for(scope,root,graph,paths):
    """Resolve all edited cast sources against one fresh playback hierarchy.

    This lookup is local to a single apply operation. Source signatures and
    reachable membership are re-read for every rebuild; no runtime handles or
    observed graph membership survive into the next preview.
    """
    paths=tuple(dict.fromkeys(paths))
    if not paths or len(paths)>128:raise ValueError('Bounded authored source set required')
    expected={};originals=[]
    for path in paths:
        node=graph['nodes'].get(path)
        if node is None or node['class_name']!='LevelSequence':raise ValueError('Imported source sequence required')
        scene_path=node['fields'].get('MovieScene',{}).get('object_path')
        expected[path]=signature(graph['nodes'].get(scene_path,{}))
        original=load_asset(scope,path).return_value
        if original is None:raise ValueError('Authored source sequence is unavailable')
        originals.append(original)
    # Observe originals and playback copies together after resolving membership.
    # Deduplicate exact identities only; a recycled index remains a distinct
    # requested identity and is rejected by the reader. No observations survive
    # this apply operation, and each bounded batch checks MovieScene ownership.
    key=lambda obj:(obj.index,obj.serial,obj.address)
    reachable=reachable_sequences(scope,root)
    unique={key(obj):obj for obj in (*originals,*reachable)}
    objects=tuple(unique.values());observed={}
    for offset in range(0,len(objects),128):
        batch=objects[offset:offset+128]
        observed.update(zip((key(obj) for obj in batch),_sequence_signatures(scope,batch)))
    if any(observed[key(obj)]!=expected[path] for path,obj in zip(paths,originals)):
        raise ValueError('Authored source signature changed since import')
    matches={}
    for obj in reachable:
        matches.setdefault(observed[key(obj)],[]).append(obj)
    result={}
    for path in paths:
        candidates=matches.get(expected[path],())
        if len(candidates)!=1:raise ValueError('Source signature is absent or ambiguous in the playback hierarchy')
        result[path]=candidates[0]
    return result


def source_for(scope,root,graph,path):
    """Resolve one source using the same signature and membership checks."""
    return sources_for(scope,root,graph,(path,))[path]


def apply(sequence,document,anchor,scene_yaw=0.):
    from .authored_timeline import validate
    # Public callers may still own and mutate their input.  Take an independent
    # validated snapshot before observing or creating any engine objects.
    return _apply_snapshot(sequence,validate(document),anchor,scene_yaw)


def _apply_snapshot(sequence,document,anchor,scene_yaw=0.,*,owners=None,latency=None):
    """Apply a preview-owned snapshot already validated by its owner thread.

    This internal path must not be used with a caller-owned document.  Preview
    preparation runs synchronously on the owner thread and owns its snapshot;
    avoiding a second full graph copy there matters for large sequences.
    Fresh native hierarchy and source-signature checks are still mandatory.
    """
    from .blueprint_actor import BlueprintActor
    from .binding_overrides import bind_actor
    # Keep every owner reachable before construction or binding can dispatch.
    # Retirement must still know about partially built actors on failure.
    if owners is None:owners=[]
    if type(owners) is not list or owners:raise ValueError('Empty replacement owner journal required')
    edits=document['cast_edits']
    if not edits:return ()
    from .._timeline_actor_channel import validate_count
    validate_count(edits,sequence.scope._session._transport)
    # Resolve every source before constructing the first replacement actor.
    measure=latency.measure if latency is not None else lambda _:nullcontext()
    with measure('timeline.cast.sources'):
        sources=sources_for(sequence.scope,sequence._asset,document['source'],(e['sequence'] for e in edits))
    targets=[(edit,sources[edit['sequence']],guid_fields(edit['guid'])) for edit in edits]
    # The sequence is the durable owner even for the public apply() API: if an
    # exception prevents a return, its close/retire path still has this journal.
    journals=getattr(sequence,'_authored_actor_journals',None)
    if journals is None:
        journals=[];sequence._authored_actor_journals=journals
    if type(journals) is not list:raise RuntimeError('Invalid sequence actor ownership journal')
    journals.append(owners)
    for index,(edit,source,guid) in enumerate(targets):
        actor=BlueprintActor(sequence.scope)
        owners.append(actor)
        pose=placement_pose(edit,anchor,index,scene_yaw)
        with measure('timeline.cast.actor'):
            actor.prepare(edit['profile'],pose);actor.reveal()
        with measure('timeline.cast.binding'):
            bind_actor(sequence,source,guid,actor)
    return tuple(owners)


def validate_reanchor(actors,document,anchor,scene_yaw=0.):
    """Preflight all replacement destinations before moving any owner."""
    from .scene_transform import actor_placement
    edits=document['cast_edits']
    if len(actors)!=len(edits):raise RuntimeError('Replacement owner count changed')
    moves=[]
    for index,(actor,edit) in enumerate(zip(actors,edits)):
        placement=edit.get('placement',dict(offset=[300.,150.*index,0.],yaw=0.))
        location,yaw=actor_placement(anchor,placement['offset'],placement['yaw'],scene_yaw)
        if any(not math.isfinite(v) or abs(v)>1e7 for v in location):
            raise ValueError('Replacement destination exceeds placement bounds')
        moves.append((actor,location,yaw))
    return tuple(moves)


def reanchor(actors,document,anchor,scene_yaw=0.):
    """Move retained replacement owners with the same scene pivot as NPCs."""
    for actor,location,yaw in validate_reanchor(actors,document,anchor,scene_yaw):
        actor.move(location,yaw)
