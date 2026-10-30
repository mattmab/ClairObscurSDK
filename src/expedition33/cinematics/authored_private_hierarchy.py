"""Selective private sequence duplication with explicit retained copy journals."""
from collections import Counter


def edited_sequence_paths(document,*,additional_sections=()):
    """Resolve imported edited sections to their exact owning sequence paths.

    This plans copies only; current engine identities and actual reachability
    must still be checked before construction. Asset-name prefix similarity is
    insufficient: an owned object starts after the sequence's outer separator.
    """
    source=document['source'];nodes=source['nodes']
    paths=set(document.get('section_edits',{}));paths.update(additional_sections)
    paths.update(edit['section'] for edit in document.get('key_edits',()))
    if not paths:return frozenset()
    if source.get('pending'):raise ValueError('Complete source hierarchy required for private edits')
    sequences={path for path,node in nodes.items() if node['class_name']=='LevelSequence'}
    if source['sequence'] not in sequences:raise ValueError('Source root LevelSequence is missing')
    result=set()
    for path in sorted(paths):
        node=nodes.get(path)
        if node is None or node.get('errors') or node.get('truncated'):
            raise ValueError('Complete imported edited section required')
        owners=[parent for parent in sequences
                if path.startswith(parent+('.' if ':' in parent else ':'))]
        if len(owners)!=1:raise ValueError('Edited section requires one imported LevelSequence owner')
        result.add(owners[0])
    return frozenset(result)


def required_paths(root,targets,edges):
    """Plan all ancestors before creating or relinking any engine object."""
    targets=frozenset(targets);active=set();seen=set();needed=set()
    def visit(node,depth=0):
        if node in active:raise ValueError('Cyclic private sequence hierarchy')
        if node in seen:return node in needed
        if depth>=32 or len(seen)+len(active)>=128:raise ValueError('Private sequence hierarchy limit')
        active.add(node)
        child_needs=[visit(child,depth+1) for child in edges.get(node,())]
        active.remove(node);seen.add(node)
        if node in targets or any(child_needs):needed.add(node)
        return node in needed
    visit(root)
    if not targets<=seen:raise ValueError('Edited sequence is not reachable from the private root')
    return frozenset(needed)


def copy_required(root,targets,initial_links,*,key,links,clone,relink):
    """Copy shared assets once, but relink every required private occurrence.

    ``links`` reobserves a newly copied parent's direct sections. ``relink``
    must prove private ownership and source immutability itself. A failed call
    is never retried here. Owners must journal every clone before linking it.
    """
    edges={}
    for parent,section,child in initial_links:edges.setdefault(key(parent),[]).append(key(child))
    needed=required_paths(key(root),targets,edges)
    copies={};processed=set()
    def visit(parent,source_identity):
        if key(parent) in processed:return
        processed.add(key(parent))
        observed=tuple(links(parent))
        if Counter(key(child) for section,child in observed)!=Counter(edges.get(source_identity,())):
            raise RuntimeError('Private sequence references changed during construction')
        sections=[key(section) for section,child in observed]
        if len(set(sections))!=len(sections):
            raise RuntimeError('Duplicate private subsection reference')
        for section,child in observed:
            identity=key(child)
            if identity not in needed:continue
            if identity not in copies:
                copies[identity]=clone(child)
                visit(copies[identity],identity)
            relink(parent,section,child,copies[identity])
    visit(root,key(root))
    return tuple(copies.values())


def match_children(original,current,*,section_key):
    """Pair direct edges by section class, relative path and signature."""
    def indexed(rows):
        result={}
        for section,child in rows:
            identity=section_key(section)
            if identity in result:raise RuntimeError('Ambiguous subsection correspondence')
            result[identity]=(section,child)
        return result
    before=indexed(original);after=indexed(current)
    if before.keys()!=after.keys():raise RuntimeError('Copied subsection structure differs from its source')
    return tuple((*before[k],*after[k]) for k in before)


def reconcile_tree(source,root,needed,*,key,links,section_key,is_private,adopt,clone,relink):
    """Accept engine-deep copies and duplicate only still-shared edited branches.

    Complete correspondence is checked before new mutations. Fresh direct
    observations are repeated during construction; dispatch failures propagate
    once with all adopted children still journaled by the caller.
    """
    mapped={};active=set();seen=set()
    def pairs(a,b):return match_children(links(a),links(b),section_key=section_key)
    def validate(a,b,depth=0):
        identity=(key(a),key(b))
        if identity in active:raise RuntimeError('Cyclic copied hierarchy')
        if identity in seen:return
        if depth>=32 or len(seen)+len(active)>=128:raise RuntimeError('Copied hierarchy correspondence limit')
        if key(a)!=key(b):
            if not is_private(b):raise RuntimeError('Foreign copied sequence reference')
            if key(b) in mapped and mapped[key(b)]!=key(a):raise RuntimeError('Conflicting copied sequence provenance')
            mapped[key(b)]=key(a)
        active.add(identity)
        for original_section,child,current_section,current_child in pairs(a,b):
            validate(child,current_child,depth+1)
        active.remove(identity);seen.add(identity)
    validate(source,root)
    built=set()
    def build(a,b):
        identity=(key(a),key(b))
        if identity in built:return
        built.add(identity)
        if key(a)!=key(b):adopt(a,b)
        for original_section,child,current_section,current_child in pairs(a,b):
            if key(child) not in needed:
                # Deep engine copies still need provenance and a seal journal.
                if key(child)!=key(current_child):build(child,current_child)
                continue
            if key(child)==key(current_child):
                copied=clone(child)
                validate(child,copied)
                build(child,copied)
                relink(a,b,original_section,current_section,child,copied)
            else:build(child,current_child)
    build(source,root)


def prepare(scope,root,outer,document,*,additional_sections=()):
    """Privatize edited branches, including children copied by Unreal itself."""
    from ..assets import load_asset
    from ..catalog import capture_selected
    from ..values import read_values_with_references,capture_selected_values
    from .._portable_binding import _hold
    from .authored_source import copied
    from .authored_copy import duplicate,signature
    from .authored_references import sequence_links
    from .authored_relink import relink
    paths=edited_sequence_paths(document,additional_sections=additional_sections)
    if not paths:return ()
    key=lambda o:(o.index,o.serial,o.address)
    states=vars(scope).get('_authored_copy_states',{});record=states.get(key(root))
    if record is None or record['state']!='fresh' or record['source']!=document['source']['sequence']:
        raise RuntimeError('Fresh private root required for hierarchy construction')
    record['members']=[];adopted={}
    try:
        source=load_asset(scope,record['source']).return_value
        if source is None:raise RuntimeError('Original root unavailable')
        initial=sequence_links(scope,source)
        objects={key(o):o for row in initial for o in row};objects[key(source)]=source
        catalog=capture_selected(scope.pid,tuple(objects))
        path_objects={catalog.path_name(o):o for o in objects.values()}
        if not paths<=path_objects.keys():raise RuntimeError('Edited source is absent from the original hierarchy')
        edges={}
        for parent,section,child in initial:edges.setdefault(key(parent),[]).append(key(child))
        needed=required_paths(key(source),{key(path_objects[p]) for p in paths},edges)
        section_keys={}
        def links(parent):
            rows=[(s,c) for p,s,c in sequence_links(scope,parent,recursive=False) if key(p)==key(parent)]
            # Refresh all direct subsection signatures together. This remains
            # a fresh observation on every traversal, not a persistent cache.
            sections={key(section):section for section,child in rows}
            objects=tuple(sections.values())
            for offset in range(0,len(objects),128):
                batch=objects[offset:offset+128]
                fresh,values=capture_selected_values(scope.pid,tuple(key(o) for o in batch),fields=('Signature',),references=True)
                if set(values)!={o.index for o in batch}:raise RuntimeError('Incomplete subsection signature batch')
                for section in batch:
                    value=values[section.index]
                    if value.errors or value.truncated or len(value.values)!=1:raise RuntimeError('Complete subsection signature required')
                    parents=[o for o in fresh.outer_chain(section) if o.class_name in ('LevelSequence','CameraAnimationSequence')]
                    if len(parents)!=1:raise RuntimeError('One subsection sequence owner required')
                    path=fresh.path_name(section);prefix=fresh.path_name(parents[0])
                    if not path.startswith(prefix+'.') and not path.startswith(prefix+':'):raise RuntimeError('Owned subsection path required')
                    section_keys[key(section)]=(section.class_name,path[len(prefix):].lstrip('.:'),signature({'fields':{'Signature':copied(next(iter(value.values.values())),fresh)}}))
            return rows
        def private(obj):
            fresh=capture_selected(scope.pid,(key(obj),key(outer)))
            return any(key(p)==key(outer) for p in fresh.outer_chain(obj))
        def section_key(section):return section_keys[key(section)]
        def adopt(original,asset):
            if original.class_name!='LevelSequence' or asset.class_name!='LevelSequence' or not private(asset):
                raise RuntimeError('Distinct owned LevelSequence child required')
            fresh=capture_selected(scope.pid,(key(original),key(asset),key(outer)))
            if any(key(p)==key(outer) for p in fresh.outer_chain(original)):raise RuntimeError('Original sequence is private')
            scenes=[]
            for obj in (original,asset):
                values,fresh=read_values_with_references(fresh,obj,fields=('MovieScene',))
                rows=list(values.values.values())
                if values.errors or values.truncated or len(rows)!=1 or rows[0] is None:raise RuntimeError('Complete copied MovieScene required')
                scene=rows[0]
                if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(obj.index,obj.serial):raise RuntimeError('Copied MovieScene ownership changed')
                scenes.append(scene)
            if key(scenes[0])==key(scenes[1]):raise RuntimeError('Copied child shares original MovieScene')
            origin=fresh.path_name(original);existing=states.get(key(asset));adopted[key(asset)]=asset
            if existing is not None and (existing['source']!=origin or existing['outer']!=key(outer) or existing['state'] not in ('fresh','ready')):
                raise RuntimeError('Conflicting private child journal')
            if existing is None:
                _hold(scope,asset)
                states[key(asset)]=dict(state='fresh',source=origin,outer=key(outer))
            if key(asset)!=key(root) and key(asset) not in record['members']:record['members'].append(key(asset))
        def clone(child):
            fresh=capture_selected(scope.pid,(key(child),))
            return duplicate(scope,fresh.path_name(child),outer)
        def link(original,parent,source_section,section,child,replacement):
            relink(scope,parent,section,child,replacement,outer,original,source_section)
        reconcile_tree(source,root,needed,key=key,links=links,section_key=section_key,
                       is_private=private,adopt=adopt,clone=clone,relink=link)
        return tuple(adopted[k] for k in record['members'])
    except BaseException:
        record['state']='rejected';raise
