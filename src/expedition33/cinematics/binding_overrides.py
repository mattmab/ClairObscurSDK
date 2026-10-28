"""Once-only actor overrides on SDK-owned, not-yet-evaluated sequence players.

Only the factory actor's override object changes. Authored sequence assets and
their templates stay untouched. Component/path and animation compatibility still
need playback validation; a dispatch receipt alone does not prove those effects.
"""
from .._reader import shared_operation
from ..catalog import capture_matching,capture_selected,CatalogObject
from ..invocation import InvocationError
from .._portable_binding import resolve,_hold
from .authored_references import sequence_occurrences


def _prepare_binding_metadata(scope):
    """Retain both sets of static selectors from one fresh discovery scan.

    Resolved bindings are still checked by the native query, and AddBinding's
    target and descriptors are still selected again immediately before dispatch.
    No hierarchy, actor or query result is cached here.
    """
    portable=getattr(scope,'_portable_binding_metadata',None)
    authored=getattr(scope,'_authored_binding_metadata',None)
    if portable is None or authored is None:
        catalog=capture_matching(scope.pid,names=('AddBinding','MovieSceneObjectBindingID','Guid',
            'MovieSceneSequenceExtensions','Default__MovieSceneSequenceExtensions','GetPortableBindingID'))
        if portable is None:
            portable=tuple(_hold(scope,catalog.find_path(path)) for path in (
                '/Script/SequencerScripting.Default__MovieSceneSequenceExtensions',
                '/Script/SequencerScripting.MovieSceneSequenceExtensions:GetPortableBindingID'))
            scope._portable_binding_metadata=portable
        if authored is None:
            authored=tuple(_hold(scope,catalog.find_path(path)) for path in (
                '/Script/LevelSequence.LevelSequenceActor:AddBinding',
                '/Script/MovieScene.MovieSceneObjectBindingID','/Script/CoreUObject.Guid'))
            scope._authored_binding_metadata=authored
    if any(lease.active is not True for lease in (*portable,*authored)):
        raise RuntimeError('Actor binding metadata lease is inactive')
    return authored


def _authored_actor(scope,source,guid):
    from .._pod_values import GUID,encode
    from ..values import read_values_with_references,StoredArray,StoredStruct
    requested=encode(GUID,guid)
    if not any(requested):raise ValueError('Nonempty authored actor GUID required')
    catalog=capture_selected(scope.pid,((source.index,source.serial,source.address),))
    values,catalog=read_values_with_references(catalog,source,fields=('MovieScene',))
    if values.errors or values.truncated:raise ValueError('Complete source MovieScene required')
    scenes=[v for k,v in values.values.items() if k[1]=='MovieScene']
    if len(scenes)!=1 or scenes[0] is None:raise ValueError('Source MovieScene is unavailable')
    scene=scenes[0]
    if scene.class_name!='MovieScene' or (scene.outer_index,scene.outer_serial)!=(source.index,source.serial):
        raise ValueError('Source MovieScene ownership changed')
    values,catalog=read_values_with_references(catalog,scene,fields=('Spawnables','Possessables'))
    if values.errors or values.truncated:raise ValueError('Complete source binding arrays required')
    fields={key[1]:v for key,v in values.values.items()}
    if set(fields)!={'Spawnables','Possessables'}:raise ValueError('Source binding arrays missing')
    matches=[]
    for kind,rows in fields.items():
        if not isinstance(rows,StoredArray) or rows.length!=len(rows.items):raise ValueError('Complete source binding array required')
        for row in rows.items:
            value=row.fields.get('Guid') if isinstance(row,StoredStruct) and 'Guid' not in row.errors else None
            if (not isinstance(value,StoredStruct) or value.errors or value.truncated or
                    catalog.path_name(catalog.resolve(value.type_object))!=GUID):raise ValueError('Complete source binding GUID required')
            if encode(GUID,dict(value.fields))==requested:matches.append((kind,row))
    if len(matches)!=1:raise ValueError('Authored actor GUID is missing or ambiguous')
    kind,row=matches[0];template=row.fields.get('ObjectTemplate')
    if kind!='Spawnables' or not isinstance(template,CatalogObject) or not any(catalog.classes[i].name=='Actor' for i in catalog.ancestors(template.class_index)):
        raise ValueError('Choose an authored spawnable actor binding')


def bind_actor(sequence,source,guid,actor):
    """Bind one owned cinematic Blueprint before the player's first evaluation.

    Construct the BlueprintActor under sequence.scope so cleanup can stop the
    consumer before destroying its inputs. Reused nested shots require explicit
    instance selection and are rejected by this initial unique-shot path.
    """
    from ..sequences import OwnedLevelSequence
    from .blueprint_actor import BlueprintActor
    if not isinstance(sequence,OwnedLevelSequence) or not isinstance(actor,BlueprintActor):
        raise TypeError('Owned sequence and Blueprint actor required')
    scope=sequence.scope;scope._check();actor.scope._check()
    if (sequence.state!='ready' or sequence.owner.state!='armed' or sequence.uncertain or sequence._evaluation_attempted or
            sequence.actor is None or sequence._asset is None):raise RuntimeError('Bind actors before the owned sequence first evaluates')
    if actor.state!='visible' or not actor.owner._timeline:raise RuntimeError('Revealed owned cinematic Blueprint required')
    if (actor.scope._session is not scope._session or actor.scope._parent is None or actor.scope._parent() is not scope):
        raise ValueError('Replacement actor must be constructed under the sequence scope')
    if actor.owner._timeline_binding_owners:raise RuntimeError('This Blueprint actor already has a binding consumer')
    capability=getattr(scope._session._transport,'sequence_binding_values_protocol',0)
    if type(capability) is not int or capability!=1:raise RuntimeError('Native binding ID values required')
    with shared_operation(scope.pid,_executable=scope._session._transport._executable):
        count=sequence_occurrences(scope,sequence._asset,source)
        if count!=1:raise ValueError('Choose a source occurring exactly once under the playback root')
        _authored_actor(scope,source,guid)
        metadata=_prepare_binding_metadata(scope)
        value=resolve(scope,sequence._asset,source,guid)
        key=(tuple(value['Guid'][name] for name in 'ABCD'),value['SequenceID'],value['ResolveParentIndex'])
        if key in sequence._actor_binding_attempts:raise RuntimeError('Binding override was already attempted; create a fresh preview')
        fixed=tuple(lease.object for lease in metadata)
        observed=capture_selected(scope.pid,(actor.identity,))
        replacement=observed.by_index[actor.identity[0]]
        catalog=capture_selected(scope.pid,tuple((obj.index,obj.serial,obj.address) for obj in (sequence.actor,replacement,*fixed)))
        # Descriptors and call authority are freshly rebuilt from this selected
        # closure; cached leases never substitute for schema validation.
        planner=scope.invocation_planner(catalog=catalog,selected_results=True)
        call=planner.prepare(sequence.actor,fixed[0],Binding=value,Actor=replacement,bAllowBindingsFromAsset=False)
        sequence._actor_binding_attempts.add(key)
        actor.owner._timeline_binding_owners.append(sequence.owner)
        scope._close_before_descendants(sequence.owner)
        try:
            # Prepared invocations return a scope-owned retained-result wrapper.
            # Release any output leases promptly; the replacement actor and
            # sequence retain their own independent ownership journals.
            with call.invoke() as result:
                outcome=result.outcome
        except BaseException as error:
            if isinstance(error,InvocationError) and error.outcome=='not_dispatched':
                actor.owner._timeline_binding_owners.remove(sequence.owner)
            else:sequence.uncertain=True
            raise
        return dict(binding=value,outcome=outcome,component_binding_verified=False)
