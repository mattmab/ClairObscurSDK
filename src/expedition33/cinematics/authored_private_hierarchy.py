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


def prepare(scope,root,outer,document,*,additional_sections=()):
    """Privatize edited nested branches before any channel mutation or player."""
    from ..assets import load_asset
    from ..catalog import capture_selected
    from ..values import read_values_with_references
    from .authored_source import copied
    from .authored_copy import duplicate,signature
    from .authored_references import sequence_links
    from .authored_relink import relink
    paths=edited_sequence_paths(document,additional_sections=additional_sections)
    if not paths:return ()
    key=lambda o:(o.index,o.serial,o.address)
    states=vars(scope).get('_authored_copy_states',{})
    record=states.get(key(root))
    if record is None or record['state']!='fresh' or record['source']!=document['source']['sequence']:
        raise RuntimeError('Fresh private root required for hierarchy construction')
    record['members']=[]
    try:
        initial=sequence_links(scope,root)
        objects={key(o):o for row in initial for o in (row[0],row[2])};objects[key(root)]=root
        catalog=capture_selected(scope.pid,tuple(objects))
        path_objects={catalog.path_name(o):o for o in objects.values()}
        path_objects[record['source']]=root
        if not paths<=path_objects.keys():raise RuntimeError('Edited source is absent from the playback hierarchy')
        targets={key(path_objects[path]) for path in paths}
        def links(parent):return [(s,c) for p,s,c in sequence_links(scope,parent,recursive=False) if key(p)==key(parent)]
        def clone(child):
            asset=duplicate(scope,catalog.path_name(child),outer)
            record['members'].append(key(asset))
            return asset
        def section_signature(section):
            fresh=capture_selected(scope.pid,(key(section),))
            values,fresh=read_values_with_references(fresh,section,fields=('Signature',))
            if values.errors or values.truncated or len(values.values)!=1:
                raise RuntimeError('Complete subsection signature required')
            return signature({'fields':{'Signature':copied(next(iter(values.values.values())),fresh)}})
        def link(parent,section,child,replacement):
            source=load_asset(scope,states[key(parent)]['source']).return_value
            if source is None:raise RuntimeError('Original parent sequence is unavailable')
            expected=section_signature(section)
            candidates=[s for p,s,c in sequence_links(scope,source,recursive=False)
                        if key(p)==key(source) and key(c)==key(child) and s.class_name==section.class_name
                        and section_signature(s)==expected]
            if len(candidates)!=1:raise RuntimeError('Original subsection signature is absent or ambiguous')
            relink(scope,parent,section,child,replacement,outer,source,candidates[0])
        return copy_required(root,targets,initial,key=key,links=links,clone=clone,relink=link)
    except BaseException:
        record['state']='rejected';raise
