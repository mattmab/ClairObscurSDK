"""Engine-authored private sequence copies retained by the caller's scope.

DuplicateSequence is the shipping Movie Render Pipeline implementation, not a
Python reconstruction of MovieScene fields. No source mutation is performed.
"""
from ..assets import load_asset
from ..catalog import capture_matching, capture_selected
from .._reader import shared_operation
from ..values import read_values_with_references
from .authored_source import copied
from . import authored_timeline
from fractions import Fraction

LIBRARY='/Script/MovieRenderPipelineCore.MoviePipelineBlueprintLibrary'


def curve_edits_available(transport):
    cap=getattr(transport,'authored_curve_patch_protocol',0)
    return type(cap) is int and cap==1


def require_key_edit_support(document,transport):
    if document.get('key_edits') and not curve_edits_available(transport):
        raise ValueError('Native curve-key playback capability required')


def duplicate(scope,path,outer,*,document=None,additional_sections=()):
    """Duplicate a retained LevelSequence hierarchy into an owned outer.

    The caller must keep the outer alive through use and release. A returned
    copy is only construction evidence; playback and edit application require
    their own validation. Never replay a failed/uncertain invocation.
    """
    scope._check()
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        source=load_asset(scope,path).return_value
        if source is None or source.class_name!='LevelSequence':raise ValueError('Expected a source LevelSequence')
        catalog=capture_matching(scope.pid,names=('MoviePipelineBlueprintLibrary',
            'Default__MoviePipelineBlueprintLibrary','DuplicateSequence'))
        catalog=catalog.with_observations(capture_selected(scope.pid,
            tuple((o.index,o.serial,o.address) for o in (source,outer))))
        default=catalog.find_path('/Script/MovieRenderPipelineCore.Default__MoviePipelineBlueprintLibrary')
        function=catalog.find_path(LIBRARY+':DuplicateSequence')
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        # Keep the result in the scope: closing a transient result here would
        # discard the only explicit root before the edited player is created.
        retained=planner.prepare(default,function,Outer=outer,InSequence=source).invoke(refresh_from_result=True)
        copied=retained.return_value
        if (copied is None or copied.class_name!='LevelSequence' or copied.index==source.index or
                (copied.outer_index,copied.outer_serial)!=(outer.index,outer.serial)):
            raise RuntimeError('Engine did not return a private LevelSequence under the supplied outer')
        catalog=planner._catalog
        roots=[]
        for obj in (source,copied):
            values,catalog=read_values_with_references(catalog,obj,fields=('MovieScene',))
            rows=[v for key,v in values.values.items() if key[1]=='MovieScene']
            if values.errors or len(rows)!=1 or rows[0] is None:raise RuntimeError('Complete MovieScene root required')
            scene=rows[0]
            if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(obj.index,obj.serial):
                raise RuntimeError('MovieScene is not owned by its sequence')
            roots.append(scene)
        if roots[0].index==roots[1].index:raise RuntimeError('Duplicated sequence still shares the source MovieScene')
        states=getattr(scope,'_authored_copy_states',None)
        if type(states) is not dict:states=scope._authored_copy_states={}
        states[(copied.index,copied.serial,copied.address)]=dict(state='fresh',source=path,
            outer=(outer.index,outer.serial,outer.address))
        if document is not None:
            from .authored_private_hierarchy import prepare
            prepare(scope,copied,outer,document,additional_sections=additional_sections)
        return copied


def seal_copy(scope,asset):
    """End the construction-only editing window before a player is created."""
    current=scope
    for _ in range(64):
        states=vars(current).get('_authored_copy_states',{})
        record=states.get((asset.index,asset.serial,asset.address)) if type(states) is dict else None
        if record is not None:
            records=[record]
            for identity in record.get('members',()):
                member=states.get(identity)
                if member is None:raise RuntimeError('Private child sequence journal is missing')
                records.append(member)
            if any(row['state'] not in ('fresh','ready') for row in records):
                raise RuntimeError('Private sequence editing is no longer available')
            for row in records:row['state']='sealed'
            return
        parent=vars(current).get('_parent');current=parent() if parent is not None else None
        if current is None:return
    raise RuntimeError('Private sequence ownership nesting exceeds the edit bound')


def apply_key_edits(scope,root,outer,document):
    """Validate every requested channel, then patch private storage before use.

    Shipping Sequencer Scripting returns no channel wrappers. The separate native
    capability validates exact channel layouts and keeps times, values, tangents
    and source observations through its write/readback receipt.
    """
    document=authored_timeline.validate(document)
    edits=document['key_edits']
    if not edits:return {}
    cap=getattr(scope._session._transport,'authored_curve_patch_protocol',0)
    if type(cap) is not int or cap!=1:raise RuntimeError('Native authored curve editing capability required')
    record=getattr(scope,'_authored_copy_states',{}).get((root.index,root.serial,root.address))
    if (record is None or record['state']!='fresh' or record['source']!=document['source']['sequence'] or
            record['outer']!=(outer.index,outer.serial,outer.address)):
        raise RuntimeError('A fresh private sequence copy is required for key editing')
    from .. import _authored_curve_patch as native
    paths=tuple(sorted({e['section'] for e in edits}));names=tuple({path.rsplit('.',1)[-1] for path in paths})
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        catalog=capture_matching(scope.pid,names=names)
        catalog=catalog.with_observations(capture_selected(scope.pid,
            tuple((o.index,o.serial,o.address) for o in (root,outer))))
        def owned(obj):return any((p.index,p.serial)==(outer.index,outer.serial) for p in catalog.outer_chain(obj))
        def read(obj,fields):
            nonlocal catalog
            values,catalog=read_values_with_references(catalog,obj,fields=fields)
            if values.errors or values.truncated:raise RuntimeError('Complete copied curve fields required')
            return {key[1]:copied(value,catalog) for key,value in values.values.items()}
        wanted={signature(document['source']['nodes'][path]):path for path in paths}
        if len(wanted)!=len(paths):raise ValueError('Ambiguous source section signatures')
        candidates={}
        for obj in tuple(catalog.objects):
            if obj.name not in names or not owned(obj):continue
            key=signature(dict(fields=read(obj,('Signature',))))
            if key in wanted:
                path=wanted[key]
                if obj.class_name!=document['source']['nodes'][path]['class_name']:raise RuntimeError('Private copied section class changed')
                candidates.setdefault(path,[]).append(obj)
        targets=_select_reachable_sections(scope,root,catalog,candidates)
        if set(targets)!=set(paths):raise RuntimeError('Copied sequence is missing an edited channel section')
        groups={}
        for edit in edits:groups.setdefault((edit['section'],tuple(edit['path'])),[]).append(edit)
        plan=[]
        for (section,path),changes in groups.items():
            if len(changes)>64:raise ValueError('At most 64 edits per native channel batch')
            original=catalog.find_path(section);target=targets[section]
            if owned(original):raise RuntimeError('Original section aliases the private copy')
            source_signature=signature(document['source']['nodes'][section])
            if signature(dict(fields=read(original,('Signature',))))!=source_signature:raise RuntimeError('Source section changed since import')
            expected={'fields':document['source']['nodes'][section]['fields']}
            source_now={'fields':read(original,(path[0],))};target_now={'fields':read(target,(path[0],))}
            for part in path:
                expected=expected['fields'][part] if type(part) is str else expected['static_array'][part]
                source_now=source_now['fields'][part] if type(part) is str else source_now['static_array'][part]
                target_now=target_now['fields'][part] if type(part) is str else target_now['static_array'][part]
            if source_now!=expected or target_now!=expected:raise RuntimeError('Source or copied channel differs from the imported curve')
            sequences=[obj for obj in catalog.outer_chain(target) if obj.class_name=='LevelSequence']
            if len(sequences)!=1 or not owned(sequences[0]):raise RuntimeError('Channel must belong to one private sequence')
            kind,keys=authored_timeline.channel(document,section,list(path))
            rows=[dict(index=e['index'],before_time=keys[e['index']]['at'],after_time=e['at'],
                       before=keys[e['index']]['value'],after=e['value']) for e in sorted(changes,key=lambda e:e['index'])]
            plan.append((section,path,(original,target,sequences[0],outer),source_signature,kind,len(keys),rows))
        record['state']='editing'
        try:
            for section,path,objects,guid,kind,count,rows in plan:
                native.patch(scope,objects,guid,kind,list(path),count,rows)
        except BaseException:
            record['state']='rejected';raise
        record['state']='ready'
        return {(section,path):len(rows) for section,path,_,_,_,_,rows in plan}


def signature(node):
    value=node.get('fields',{}).get('Signature',{})
    if (value.get('struct')!='/Script/CoreUObject.Guid' or not value.get('complete') or
            value.get('errors') or set(value.get('fields',{}))!=set('ABCD')):
        raise ValueError('Complete authored object signature required')
    fields=value['fields']
    if any(type(fields[k]) is not int or not -(1<<31)<=fields[k]<(1<<31) for k in 'ABCD'):
        raise ValueError('Invalid authored object signature')
    result=tuple(fields[k] for k in 'ABCD')
    if not any(result):raise ValueError('Empty authored object signature')
    return result


def apply_section_edits(scope,root,outer,document):
    """Apply exact native tick ranges to private copied sections before playback.

    Sequencer Scripting SetRange takes DISPLAY frames. Convert exactly when
    possible. For off-grid ticks, temporarily change only the private sequence's
    display rate to its tick resolution, then restore it after the edit.
    """
    document=authored_timeline.validate(document)
    edits=document['section_edits']
    if not edits:return {}
    states=vars(scope).get('_authored_copy_states',{})
    record=states.get((root.index,root.serial,root.address)) if type(states) is dict else None
    if record is not None and record['state'] not in ('fresh','ready'):
        raise RuntimeError('Private sequence editing is no longer available')
    scope._check()
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        names=tuple({path.rsplit('.',1)[-1] for path in edits})
        catalog=capture_matching(scope.pid,names=names+('MovieSceneSectionExtensions',
            'Default__MovieSceneSectionExtensions','SetRange','MovieSceneSequenceExtensions',
            'Default__MovieSceneSequenceExtensions','SetDisplayRate'))
        catalog=catalog.with_observations(capture_selected(scope.pid,
            tuple((o.index,o.serial,o.address) for o in (root,outer))))
        def owned(obj):return any((p.index,p.serial)==(outer.index,outer.serial) for p in catalog.outer_chain(obj))
        if not owned(root) or root.class_name!='LevelSequence':raise RuntimeError('Private sequence root required')
        def read(obj,fields):
            nonlocal catalog
            values,catalog=read_values_with_references(catalog,obj,fields=fields)
            if values.errors or values.truncated:raise RuntimeError('Complete copied timeline fields required')
            return {k[1]:v for k,v in values.values.items()}
        wanted={signature(document['source']['nodes'][path]):path for path in edits}
        if len(wanted)!=len(edits):raise ValueError('Ambiguous source section signatures')
        candidates={}
        for obj in tuple(catalog.objects):
            if obj.name not in names or not owned(obj):continue
            fields=read(obj,('Signature',))
            key=signature({'fields':{'Signature':copied(fields.get('Signature'),catalog)}})
            if key not in wanted:continue
            path=wanted[key]
            if obj.class_name!=document['source']['nodes'][path]['class_name']:
                raise RuntimeError('Private copied section class changed')
            candidates.setdefault(path,[]).append(obj)
        targets=_select_reachable_sections(scope,root,catalog,candidates)
        if set(targets)!=set(edits):raise RuntimeError('Copied timeline is missing an edited section')
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        def invoke(owner,name,**arguments):
            planner.refresh_from(catalog)
            default=catalog.find_path('/Script/SequencerScripting.Default__'+owner)
            function=catalog.find_path('/Script/SequencerScripting.'+owner+':'+name)
            with planner.prepare(default,function,**arguments).invoke():pass
        result={}
        for path,section in targets.items():
            original=catalog.find_path(path)
            if owned(original):raise RuntimeError('Original source aliases the private copy')
            expected=document['source']['nodes'][path]['fields']['SectionRange']
            if signature({'fields':{'Signature':copied(read(original,('Signature',))['Signature'],catalog)}})!=signature(document['source']['nodes'][path]):
                raise RuntimeError('Source section signature changed since import')
            before=copied(read(original,('SectionRange',))['SectionRange'],catalog)
            private_before=copied(read(section,('SectionRange',))['SectionRange'],catalog)
            if before!=expected or private_before!=expected:raise RuntimeError('Source or copied section range changed since import')
            sequences=[o for o in catalog.outer_chain(section) if o.class_name=='LevelSequence']
            if len(sequences)!=1 or not owned(sequences[0]):raise RuntimeError('Section must belong to one private sequence')
            sequence=sequences[0];scene=read(sequence,('MovieScene',))['MovieScene']
            timing=read(scene,('TickResolution','DisplayRate'))
            rates={name:dict(value.fields) for name,value in timing.items()}
            if set(rates)!={'TickResolution','DisplayRate'} or any(set(rate)!={'Numerator','Denominator'} or any(type(v) is not int or v<=0 for v in rate.values()) for rate in rates.values()):
                raise RuntimeError('Positive exact private sequence rates required')
            changed_rate=False
            try:start,end=display_frames(edits[path],rates['TickResolution'],rates['DisplayRate'])
            except ValueError:
                cap=getattr(scope._session._transport,'sequencer_frame_values_protocol',0)
                if type(cap) is not int or cap!=1:raise
                start,end=edits[path]['start'],edits[path]['end']
                invoke('MovieSceneSequenceExtensions','SetDisplayRate',Sequence=sequence,DisplayRate=rates['TickResolution'])
                changed_rate=True
            invoke('MovieSceneSectionExtensions','SetRange',Section=section,StartFrame=start,EndFrame=end)
            if changed_rate:
                invoke('MovieSceneSequenceExtensions','SetDisplayRate',Sequence=sequence,DisplayRate=rates['DisplayRate'])
            after=copied(read(section,('SectionRange',))['SectionRange'],catalog)
            bounds=after.get('frame_range',{})
            if bounds!={'lower':{'kind':'inclusive','value':edits[path]['start']},'upper':{'kind':'exclusive','value':edits[path]['end']}}:
                raise RuntimeError('Engine section range differs from requested native ticks')
            if copied(read(original,('SectionRange',))['SectionRange'],catalog)!=before:
                raise RuntimeError('Original source section changed during private edit')
            if dict(read(scene,('DisplayRate',))['DisplayRate'].fields)!=rates['DisplayRate']:
                raise RuntimeError('Private sequence display rate was not restored')
            result[path]=bounds
        return result


def _select_reachable_sections(scope,root,catalog,candidates):
    """Disambiguate duplicate copy products through actual sequence references.

    DuplicateSequence can leave extra copies under the supplied outer. Equal
    signatures and ownership alone do not identify the section used by playback.
    """
    if any(len(rows)>1 for rows in candidates.values()):
        from .authored_references import reachable_sections
        reachable=reachable_sections(scope,root,catalog,tuple(obj for rows in candidates.values() for obj in rows))
        candidates={path:[obj for obj in rows if obj.index in reachable]
                    for path,rows in candidates.items()}
    if any(len(rows)!=1 for rows in candidates.values()):
        raise RuntimeError('Ambiguous or unreachable private copied section signature')
    return {path:rows[0] for path,rows in candidates.items()}


def display_frames(edit,tick,display):
    scale=Fraction(display['Numerator']*tick['Denominator'],display['Denominator']*tick['Numerator'])
    values=tuple(edit[key]*scale for key in ('start','end'))
    if any(v.denominator!=1 for v in values):raise ValueError('Section edit is between display frames; exact native tick setter required')
    return tuple(authored_timeline.frame(v.numerator) for v in values)
