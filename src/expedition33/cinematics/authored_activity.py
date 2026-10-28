"""Verified private spawn-section suppression before player construction."""
from ..catalog import capture_matching,capture_selected
from ..values import read_values_with_references
from .._reader import shared_operation
from .authored_source import copied
from .authored_copy import signature,_select_reachable_sections


def disable_sections(scope,root,outer,document,paths):
    paths=tuple(paths)
    if not paths:return
    if len(paths)!=len(set(paths)) or len(paths)>16:raise ValueError('Bounded distinct private sections required')
    key=lambda o:(o.index,o.serial,o.address)
    record=vars(scope).get('_authored_copy_states',{}).get(key(root))
    if (record is None or record['state'] not in ('fresh','ready') or record['outer']!=key(outer)
            or record['source']!=document['source']['sequence']):
        raise RuntimeError('Editable private root required for section suppression')
    scope._check()
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        names=tuple({p.rsplit('.',1)[-1] for p in paths})
        catalog=capture_matching(scope.pid,names=names+('SetIsActive',))
        catalog=catalog.with_observations(capture_selected(scope.pid,(key(root),key(outer))))
        def owned(o):return any(key(p)==key(outer) for p in catalog.outer_chain(o))
        if root.class_name!='LevelSequence' or not owned(root):raise RuntimeError('Owned private root required')
        def read(o):
            nonlocal catalog
            values,catalog=read_values_with_references(catalog,o,fields=('Signature','bIsActive'))
            rows={k[1]:v for k,v in values.values.items()}
            if values.errors or values.truncated or len(values.values)!=2 or set(rows)!={'Signature','bIsActive'} or type(rows['bIsActive']) is not bool:
                raise RuntimeError('Complete section signature and activity required')
            return signature({'fields':{'Signature':copied(rows['Signature'],catalog)}}),rows['bIsActive']
        expected={signature(document['source']['nodes'][p]):p for p in paths}
        if len(expected)!=len(paths):raise ValueError('Ambiguous imported section signatures')
        candidates={}
        for obj in tuple(catalog.objects):
            if obj.name not in names or not owned(obj):continue
            sig,active=read(obj)
            if sig in expected:candidates.setdefault(expected[sig],[]).append(obj)
        from .authored_references import reachable_sections
        reachable=reachable_sections(scope,root,catalog,tuple(o for rows in candidates.values() for o in rows))
        candidates={path:[o for o in rows if o.index in reachable] for path,rows in candidates.items()}
        targets=_select_reachable_sections(scope,root,catalog,candidates)
        if set(targets)!=set(paths):raise RuntimeError('Private movie spawn section is missing')
        plan=[]
        for path,target in targets.items():
            original=catalog.find_path(path);node=document['source']['nodes'][path]
            if owned(original) or target.class_name!='MovieSceneSpawnSection' or original.class_name!=target.class_name:
                raise RuntimeError('Distinct original and private movie spawn sections required')
            before=(signature(node),node['fields'].get('bIsActive'))
            if before[1] is not True or read(original)!=before or read(target)!=before:
                raise RuntimeError('Original or private movie activity changed since import')
            plan.append((original,target,before))
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        function=catalog.find_path('/Script/MovieScene.MovieSceneSection:SetIsActive')
        record['state']='editing'
        try:
            for original,target,before in plan:
                with planner.prepare(target,function,bInIsActive=False).invoke():pass
                if read(target)[1] is not False:raise RuntimeError('Private movie section did not deactivate')
                if read(original)!=before:raise RuntimeError('Original movie section changed during suppression')
        except BaseException:
            record['state']='rejected';raise
        record['state']='ready'
