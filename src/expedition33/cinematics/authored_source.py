"""Copied authored timeline data for editor import; never mutates game assets.

Runtime identities are used only while reading the retained source. Persistent
editor data contains asset paths and authored binding GUIDs, not process slots.
Unsupported or truncated data remains explicit and cannot masquerade as an
editable complete track.
"""
import math
import time
from ..catalog import CatalogObject
from ..values import StoredArray,StoredStruct,StoredMap,StoredMapEntries,StoredSoftObjectPath,SOURCE_VALUE_BATCH_LIMIT

MAX_GRAPH_NODES=8192
DEFAULT_GRAPH_NODES=MAX_GRAPH_NODES


def copied(value,catalog,*,depth=0,budget=None):
    budget=[16384] if budget is None else budget
    budget[0]-=1
    if depth>24 or budget[0]<0:raise ValueError('Authored source copy exceeds bounds')
    def child(item):return copied(item,catalog,depth=depth+1,budget=budget)
    if value is None or type(value) in (str,bool,int):return value
    if type(value) is float:
        if not math.isfinite(value):raise ValueError('Nonfinite authored value')
        return value
    if isinstance(value,CatalogObject):
        return {'object_path':catalog.path_name(catalog.resolve(value)),'class':value.class_name}
    if isinstance(value,StoredSoftObjectPath):
        return {'soft_path':dict(package=value.package,asset=value.asset,subpath=value.subpath)}
    if isinstance(value,StoredArray):
        return {'array':[child(v) for v in value.items],'length':value.length,
                'complete':value.length==len(value.items)}
    if type(value) is tuple:return {'static_array':[child(v) for v in value]}
    if isinstance(value,StoredStruct):
        result={'struct':catalog.path_name(catalog.resolve(value.type_object)),
                'fields':{str(k):child(v) for k,v in value.fields.items()},
                'errors':{str(k):str(v) for k,v in value.errors.items()},
                'complete':not value.errors and not value.truncated}
        if value.native is not None:
            from ..values import StoredFrameRange
            if not isinstance(value.native,StoredFrameRange):raise ValueError('Unsupported native authored value')
            r=value.native
            result['frame_range']=dict(lower=dict(kind=r.lower_kind,value=r.lower),upper=dict(kind=r.upper_kind,value=r.upper))
        return result
    if isinstance(value,StoredMap):
        return {'map':[[child(k),child(v)] for k,v in value.items.items()]}
    if isinstance(value,StoredMapEntries):
        return {'map':[[child(k),child(v)] for k,v in value.entries]}
    raise ValueError('Unsupported authored value: '+type(value).__name__)


def _references(value):
    if isinstance(value,CatalogObject):yield value
    elif isinstance(value,StoredArray):
        for item in value.items:yield from _references(item)
    elif type(value) is tuple:
        for item in value:yield from _references(item)
    elif isinstance(value,StoredStruct):
        for item in value.fields.values():yield from _references(item)
    elif isinstance(value,(StoredMap,StoredMapEntries)):
        pairs=value.items.items() if isinstance(value,StoredMap) else value.entries
        for key,item in pairs:
            yield from _references(key)
            yield from _references(item)


def _inspect_graph(catalog,asset,read,*,max_nodes=DEFAULT_GRAPH_NODES):
    steps=_inspect_graph_steps(catalog,asset,read,max_nodes=max_nodes)
    while True:
        try:next(steps)
        except StopIteration as done:return done.value


def _inspect_graph_steps(catalog,asset,read,*,max_nodes=DEFAULT_GRAPH_NODES,read_many=None,metrics=None):
    """Follow stored sequence/track references without following gameplay actors.

    Each node is independently observed. This is not an atomic graph snapshot or
    an editable track codec: opaque native channels remain unsupported.
    """
    if type(max_nodes) is not int or not 1<=max_nodes<=MAX_GRAPH_NODES:raise ValueError('Invalid authored graph limit')
    if asset.class_name!='LevelSequence':raise ValueError('Expected a game LevelSequence')
    root=catalog.path_name(catalog.resolve(asset))
    queue=[asset];scheduled={root};sequence_paths={root};nodes={};pending=[]
    budget=[524288];prefetched={}
    def is_sequence(obj):
        return obj.class_name=='LevelSequence' or any(
            catalog.classes[index].name=='MovieSceneSequence' for index in catalog.ancestors(obj.class_index))
    def is_track_or_section(obj):
        return obj.class_name.startswith('MovieScene') or any(
            catalog.classes[index].name in ('MovieSceneTrack','MovieSceneSection')
            for index in catalog.ancestors(obj.class_index))
    while queue:
        obj=queue.pop(0);path=catalog.path_name(catalog.resolve(obj))
        if len(nodes)>=max_nodes:
            pending=[path]+[catalog.path_name(catalog.resolve(o)) for o in queue]
            break
        started=time.perf_counter() if metrics is not None else None
        if read_many is not None:
            if obj.index not in prefetched:
                batch=(obj,*queue[:min(SOURCE_VALUE_BATCH_LIMIT-1,max_nodes-len(nodes)-1)])
                prefetched,catalog=read_many(catalog,batch)
                if metrics is not None:metrics['read_batches']=metrics.get('read_batches',0)+1
            values=prefetched.pop(obj.index)
        else:
            values,catalog=read(catalog,obj)
            if metrics is not None:metrics['read_batches']=metrics.get('read_batches',0)+1
        if metrics is not None:
            metrics['read_ms']=metrics.get('read_ms',0.)+(time.perf_counter()-started)*1000
            started=time.perf_counter()
        fields={};errors={key[1]:str(error) for key,error in values.errors.items()}
        refs=[]
        for key,value in values.values.items():
            try:fields[key[1]]=copied(value,catalog,budget=budget)
            except ValueError as error:errors[key[1]]=str(error)
            refs.extend(_references(value))
        if metrics is not None:
            metrics['copy_ms']=metrics.get('copy_ms',0.)+(time.perf_counter()-started)*1000
            started=time.perf_counter()
        nodes[path]=dict(class_name=obj.class_name,fields=fields,errors=errors,
                         truncated=sorted(key[1] for key in values.truncated))
        # Add newly referenced nested sequences before checking their owned rows.
        for ref in refs:
            if is_sequence(ref):sequence_paths.add(catalog.path_name(catalog.resolve(ref)))
        for ref in refs:
            ref_path=catalog.path_name(catalog.resolve(ref))
            eligible=(is_sequence(ref) or
                      (is_track_or_section(ref) and
                       any(ref_path.startswith(source+('.' if ':' in source else ':')) for source in sequence_paths)))
            if eligible and ref_path not in scheduled:
                scheduled.add(ref_path);queue.append(ref)
        if metrics is not None:
            metrics['follow_ms']=metrics.get('follow_ms',0.)+(time.perf_counter()-started)*1000
        yield len(nodes)
    return dict(sequence=root,nodes=nodes,pending=pending,editable=False,
                observation='independent stored reads; native channels may be opaque')


def inspect_graph(scope,path,*,max_nodes=DEFAULT_GRAPH_NODES):
    """Inspect nested shots, track sections and declared cast; never writes assets."""
    from ..assets import load_asset
    from ..catalog import capture_selected
    from ..values import read_values_with_references
    from .._reader import shared_operation
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        asset=load_asset(scope,path).return_value
        if asset is None:raise ValueError('Expected a game LevelSequence')
        catalog=capture_selected(scope.pid,((asset.index,asset.serial,asset.address),))
        return _inspect_graph(catalog,asset,read_values_with_references,max_nodes=max_nodes)


def inspect_retained_graph(scope,asset,*,max_nodes=DEFAULT_GRAPH_NODES):
    """Inspect a retained private sequence without asset-path loading."""
    from ..catalog import capture_selected
    from ..values import read_values_with_references
    from .._reader import shared_operation
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        catalog=capture_selected(scope.pid,((asset.index,asset.serial,asset.address),))
        return _inspect_graph(catalog,asset,read_values_with_references,max_nodes=max_nodes)


def inspect_source(scope,path):
    """Inspect the retained root sequence's timing, cast and track declarations.

    This is source inspection, not playback or an editable scene conversion.
    Nested sequence assets and channel codecs are imported by later stages.
    The caller owns the scope and all retained source assets until it closes.
    """
    from ..assets import load_asset
    from ..catalog import capture
    from ..values import read_values_with_references
    from .._reader import shared_operation
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        asset=load_asset(scope,path).return_value
        if asset is None or asset.class_name!='LevelSequence':raise ValueError('Expected a game LevelSequence')
        catalog=capture()
        values,catalog=read_values_with_references(catalog,asset,fields=('MovieScene',))
        rows=[v for k,v in values.values.items() if k[1]=='MovieScene']
        if values.errors or len(rows)!=1 or not isinstance(rows[0],CatalogObject):
            raise ValueError('Complete authored MovieScene reference required')
        scene=rows[0]
        if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(asset.index,asset.serial):
            raise ValueError('Authored MovieScene is outside its source sequence')
        values,catalog=read_values_with_references(catalog,scene,fields=(
            'TickResolution','DisplayRate','PlaybackRange','Spawnables','Possessables','ObjectBindings','Tracks'))
        return dict(sequence=path,fields={k[1]:copied(v,catalog) for k,v in values.values.items()},
                    errors={k[1]:str(v) for k,v in values.errors.items()},
                    truncated=sorted(k[1] for k in values.truncated),editable=False)
