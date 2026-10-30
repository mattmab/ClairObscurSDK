"""Construction-only relinking of retained private cinematic subsections."""
from .._reader import shared_operation
from ..catalog import capture_matching,capture_selected
from ..values import read_values_with_references
from .authored_source import copied
from .authored_copy import signature
from .authored_references import sequence_links


def relink(scope,parent,section,child,replacement,outer,source_parent,source_section):
    """Dispatch once, then verify the private link and unchanged source link.

    A failed or uncertain dispatch poisons construction rather than replaying
    it. The caller retains every sequence and the supplied outer through use.
    """
    scope._check();key=lambda obj:(obj.index,obj.serial,obj.address)
    states=vars(scope).get('_authored_copy_states',{})
    record=states.get(key(parent));replacement_record=states.get(key(replacement))
    for item in (record,replacement_record):
        if item is None or item['state'] not in ('fresh','ready') or item['outer']!=key(outer):
            raise RuntimeError('Fresh retained private sequences required for relinking')
    if key(parent)==key(replacement):raise RuntimeError('A sequence cannot contain itself')
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        catalog=capture_matching(scope.pid,names=('SetSequence',))
        objects=(parent,section,child,replacement,outer,source_parent,source_section)
        catalog=catalog.with_observations(capture_selected(scope.pid,tuple(dict.fromkeys(key(o) for o in objects))))
        parent,section,child,replacement,outer,source_parent,source_section=(catalog.resolve(o) for o in objects)
        def owned(obj,owner):return any(key(p)==key(owner) for p in catalog.outer_chain(obj))
        if (not owned(parent,outer) or not owned(replacement,outer) or
                not owned(section,parent) or not owned(source_section,source_parent) or
                owned(source_parent,outer) or owned(source_section,outer) or owned(child,outer)):
            raise RuntimeError('Private and original subsection ownership must be distinct')
        if catalog.path_name(source_parent)!=record['source'] or catalog.path_name(child)!=replacement_record['source']:
            raise RuntimeError('Private sequence source journal does not match the original')
        if parent.class_name!='LevelSequence' or replacement.class_name!='LevelSequence':
            raise RuntimeError('Retained LevelSequence copies required')
        if section.class_name!=source_section.class_name:
            raise RuntimeError('Private subsection class differs from its source')
        def linked(root,selected):
            matches=[c for p,s,c in sequence_links(scope,root,recursive=False) if key(p)==key(root) and key(s)==key(selected)]
            if len(matches)!=1:return None
            return key(matches[0])
        if linked(parent,section)!=key(child) or linked(source_parent,source_section)!=key(child):
            raise RuntimeError('Original or private subsection references changed')
        # A replacement containing its new parent would make a recursive graph.
        if any(key(c)==key(parent) for p,s,c in sequence_links(scope,replacement)):
            raise RuntimeError('Relinking would create a cyclic sequence hierarchy')
        def fields(obj):
            nonlocal catalog
            values,catalog=read_values_with_references(catalog,obj,fields=('Signature','SubSequence'))
            rows={k[1]:v for k,v in values.values.items()}
            if values.errors or values.truncated or len(values.values)!=2 or set(rows)!={'Signature','SubSequence'}:
                raise RuntimeError('Complete subsection signature and reference required')
            return signature({'fields':{'Signature':copied(rows['Signature'],catalog)}}),key(rows['SubSequence'])
        before=fields(source_section)
        if fields(section)!=before or before[1]!=key(child):
            raise RuntimeError('Copied subsection no longer matches its original')
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        function=catalog.find_path('/Script/MovieScene.MovieSceneSubSection:SetSequence')
        record['state']='relinking'
        try:
            with planner.prepare(section,function,Sequence=replacement).invoke():pass
            if fields(section)[1]!=key(replacement):raise RuntimeError('Private subsection relink was not applied')
            if fields(source_section)!=before:raise RuntimeError('Original subsection changed during private relink')
        except BaseException:
            record['state']='rejected';raise
        record['state']='fresh'
