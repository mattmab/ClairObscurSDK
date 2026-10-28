"""Bounded sequence/track reference traversal without decoding curve contents."""
from ..catalog import capture_selected
from ..values import read_values_with_references,capture_selected_values,StoredArray,StoredStruct,StoredMap,StoredMapEntries
from .authored_source import _references


def _complete(value,depth=0):
    if depth>24:raise RuntimeError('Sequence reference depth exceeded')
    if isinstance(value,StoredArray):
        if value.length!=len(value.items):raise RuntimeError('Incomplete sequence reference array')
        children=value.items
    elif isinstance(value,StoredStruct):
        if value.errors or value.truncated:raise RuntimeError('Incomplete sequence reference struct')
        children=value.fields.values()
    elif isinstance(value,StoredMap):children=tuple(v for pair in value.items.items() for v in pair)
    elif isinstance(value,StoredMapEntries):children=tuple(v for pair in value.entries for v in pair)
    elif type(value) is tuple:children=value
    else:return
    for child in children:_complete(child,depth+1)


def _reachable_sections(catalog,root,candidates,read,*,read_many=None,on_reference=None,on_section_reference=None,follow_subsequences=True):
    """Return actual referenced candidate identities; all reads are projections."""
    wanted={obj.index for obj in candidates};candidate_tracks=set()
    def is_a(obj,name):
        return any(catalog.classes[i].name==name for i in catalog.ancestors(obj.class_index))
    for obj in candidates:
        tracks=[p for p in catalog.outer_chain(obj) if is_a(p,'MovieSceneTrack')]
        if len(tracks)!=1:raise RuntimeError('Edited section requires one owning track')
        candidate_tracks.add(tracks[0].index)
    queue=[root];seen=set();found=set();reads=0
    def checked(values,names):
        if values.errors or values.truncated:raise RuntimeError('Incomplete sequence reference fields')
        result={key[1]:value for key,value in values.values.items()}
        if len(values.values)!=len(names) or set(result)!=set(names):raise RuntimeError('Missing or ambiguous sequence reference field')
        for value in result.values():_complete(value)
        return result
    def fields_many(objects,names):
        nonlocal catalog,reads
        objects=tuple(objects)
        if not objects:return {}
        reads+=len(objects)
        if reads>4096:raise RuntimeError('Sequence reference read limit exceeded')
        if read_many is None:
            values={}
            for obj in objects:values[obj.index],catalog=read(catalog,obj,fields=names)
        else:values,catalog=read_many(catalog,objects,fields=names)
        if set(values)!={obj.index for obj in objects}:raise RuntimeError('Incomplete sequence reference batch')
        return {index:checked(value,names) for index,value in values.items()}
    def fields(obj,names):return fields_many((obj,),names)[obj.index]
    while queue:
        # Project each breadth level together. Every level is a fresh read;
        # no graph observation is reused across playback construction.
        frontier=[]
        for sequence in queue:
            if sequence.index in seen:continue
            if len(seen)>=128 or not is_a(sequence,'MovieSceneSequence'):raise RuntimeError('Invalid nested sequence graph')
            seen.add(sequence.index);frontier.append(sequence)
        queue=[]
        scene_values=fields_many(frontier,('MovieScene',));scenes=[];parents={}
        for sequence in frontier:
            scene=scene_values[sequence.index]['MovieScene']
            if (scene is None or scene.class_name!='MovieScene' or
                    (scene.outer_index,scene.outer_serial)!=(sequence.index,sequence.serial)):
                raise RuntimeError('Sequence MovieScene ownership changed')
            scenes.append(scene);parents[scene.index]=sequence
        scene_refs=fields_many(scenes,('Tracks','ObjectBindings','CameraCutTrack'))
        selected=[];track_parents={};subsections={}
        for scene in scenes:
            refs=scene_refs[scene.index]
            tracks={obj.index:obj for value in refs.values() for obj in _references(value) if is_a(obj,'MovieSceneTrack')}
            for track in tracks.values():
                if (track.outer_index,track.outer_serial)!=(scene.index,scene.serial):
                    raise RuntimeError('Sequence track ownership changed')
                if not is_a(track,'MovieSceneSubTrack') and track.index not in candidate_tracks:continue
                selected.append(track);track_parents[track.index]=parents[scene.index]
        track_values=fields_many(selected,('Sections',))
        for track in selected:
            subtrack=is_a(track,'MovieSceneSubTrack')
            sections=track_values[track.index]['Sections']
            if not isinstance(sections,StoredArray):raise RuntimeError('Expected complete track section array')
            for section in sections.items:
                if (section is None or not is_a(section,'MovieSceneSection') or
                        (section.outer_index,section.outer_serial)!=(track.index,track.serial)):
                    raise RuntimeError('Sequence section ownership changed')
                if section.index in wanted:found.add(section.index)
                if subtrack:
                    if not is_a(section,'MovieSceneSubSection'):raise RuntimeError('Subtrack contains another section family')
                    subsections[section.index]=(section,track_parents[track.index])
        for index,row in fields_many((pair[0] for pair in subsections.values()),('SubSequence',)).items():
            if row['SubSequence'] is not None:
                if on_reference is not None:on_reference(subsections[index][1],row['SubSequence'])
                if on_section_reference is not None:on_section_reference(subsections[index][1],subsections[index][0],row['SubSequence'])
                if follow_subsequences:queue.append(row['SubSequence'])
    return frozenset(found)


def _path_count(edges,root,source):
    """Count distinct shot occurrences, saturating at two; reject cycles."""
    active=set();memo={}
    def visit(node):
        if node in active:raise RuntimeError('Cyclic nested sequence hierarchy')
        if node in memo:return memo[node]
        active.add(node)
        children=tuple(edges.get(node,()))
        # Traverse all edges even after saturation so cycles stay explicit.
        counts=[visit(child) for child in children]
        count=1 if node==source else min(2,sum(counts))
        active.remove(node);memo[node]=count;return count
    return visit(root)


def sequence_occurrences(scope,root,source):
    """Count actual source occurrences under root, not merely object ownership."""
    scope._check()
    key=lambda obj:(obj.index,obj.serial,obj.address)
    catalog=capture_selected(scope.pid,(key(root),key(source)) if key(root)!=key(source) else (key(root),))
    edges={}
    def edge(parent,child):edges.setdefault(key(parent),[]).append(key(child))
    def read_many(catalog,objects,*,fields):
        fresh,values=capture_selected_values(scope.pid,tuple(key(o) for o in objects),fields=fields,references=True)
        return values,catalog.with_observations(fresh)
    _reachable_sections(catalog,root,(),read_values_with_references,read_many=read_many,on_reference=edge)
    return _path_count(edges,key(root),key(source))


def reachable_sequences(scope,root):
    """Read actual nested membership, retaining distinct sequence identities."""
    scope._check();key=lambda o:(o.index,o.serial,o.address)
    catalog=capture_selected(scope.pid,(key(root),));root=catalog.by_index[root.index]
    objects={key(root):root};edges={}
    def edge(parent,child):
        objects[key(child)]=child;edges.setdefault(key(parent),[]).append(key(child))
    def read_many(catalog,objects,*,fields):
        fresh,values=capture_selected_values(scope.pid,tuple(key(o) for o in objects),fields=fields,references=True)
        return values,catalog.with_observations(fresh)
    _reachable_sections(catalog,root,(),read_values_with_references,read_many=read_many,on_reference=edge)
    _path_count(edges,key(root),key(root)) # Validate the entire graph, including cycles.
    return tuple(objects.values())


def reachable_sections(scope,root,catalog,candidates):
    scope._check()
    fresh=capture_selected(scope.pid,((root.index,root.serial,root.address),))
    catalog=catalog.with_observations(fresh)
    def read_many(catalog,objects,*,fields):
        fresh,values=capture_selected_values(scope.pid,tuple((o.index,o.serial,o.address) for o in objects),
            fields=fields,references=True)
        return values,catalog.with_observations(fresh)
    return _reachable_sections(catalog,root,candidates,read_values_with_references,read_many=read_many)


def sequence_links(scope,root,*,recursive=True):
    """Observe actual parent/section/child edges for a retained sequence root.

    Results are current observations, not leases or authority to edit children.
    Callers must separately validate private ownership before every mutation.
    """
    if type(recursive) is not bool:raise ValueError('Boolean sequence traversal mode required')
    scope._check();key=lambda o:(o.index,o.serial,o.address)
    catalog=capture_selected(scope.pid,(key(root),));root=catalog.by_index[root.index]
    links=[];edges={}
    def edge(parent,section,child):
        links.append((parent,section,child));edges.setdefault(key(parent),[]).append(key(child))
    def read_many(catalog,objects,*,fields):
        fresh,values=capture_selected_values(scope.pid,tuple(key(o) for o in objects),fields=fields,references=True)
        return values,catalog.with_observations(fresh)
    _reachable_sections(catalog,root,(),read_values_with_references,read_many=read_many,
                        on_section_reference=edge,follow_subsequences=recursive)
    _path_count(edges,key(root),key(root))
    return tuple(links)
