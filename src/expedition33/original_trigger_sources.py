"""Inspect original retained battle-trigger parameters without executing actions."""
import re
import struct
from .assets import load_asset
from ._scope import SessionScope
from ._reader import ReadBatch
from .catalog import capture_matching,capture_selected
from .reflection import describe
from .values import read_values_with_references,StoredStruct,StoredArray,StoredMap,StoredMapEntries

TRIGGER_CLASS='/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle.BP_GameAction_TriggerBattle_C'
BATTLE_STRUCT='/Game/Gameplay/Battle/FBattleStartParams.FBattleStartParams'


def _copy(value,catalog):
    if hasattr(value,'class_index'):return catalog.path_name(value)
    if isinstance(value,StoredStruct):
        return dict(type=catalog.path_name(value.type_object),fields={k:_copy(v,catalog) for k,v in value.fields.items()},
            errors={k:str(v) for k,v in value.errors.items()},truncated=value.truncated)
    if isinstance(value,StoredArray):return dict(length=value.length,items=[_copy(v,catalog) for v in value.items])
    if isinstance(value,(StoredMap,StoredMapEntries)):
        pairs=value.items.items() if isinstance(value,StoredMap) else value.entries
        return dict(entries=[[_copy(k,catalog),_copy(v,catalog)] for k,v in pairs])
    if isinstance(value,(tuple,list)):return [_copy(v,catalog) for v in value]
    if value is None or type(value) in (str,int,float,bool):return value
    raise TypeError('Unsupported copied observation type: '+type(value).__name__)


def _validate_paths(asset_path,source_path):
    if (type(asset_path) is not str or not re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.(?i:\1)',asset_path)):
        raise ValueError('Expected an exact original top-level asset path')
    if (type(source_path) is not str or len(source_path)>4096 or
        not source_path.casefold().startswith(asset_path.casefold()+':') or
        not re.fullmatch(r'[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*',source_path[len(asset_path)+1:])):
        raise ValueError('Expected a nested source path belonging to the selected asset')


def _owned_source(catalog,root,source_path):
    matches=[obj for obj in catalog.objects if catalog.path_name(obj).casefold()==source_path.casefold()]
    if len(matches)!=1:raise RuntimeError('Original trigger source is missing or ambiguous')
    source=matches[0];cursor=source;seen=set()
    while cursor.index!=root.index:
        if cursor.index in seen or len(seen)>=128:raise RuntimeError('Invalid original source ownership chain')
        seen.add(cursor.index);cursor=catalog.by_index.get(cursor.outer_index)
        if cursor is None:raise RuntimeError('Trigger is not owned by the retained asset')
    if (cursor.serial,cursor.address)!=(root.serial,root.address):raise RuntimeError('Original asset identity changed')
    if TRIGGER_CLASS not in {catalog.path_name(catalog.by_index[i]) for i in catalog.ancestors(source.class_index)}:
        raise RuntimeError('Source does not derive from the original battle-trigger class')
    return source


def inspect_trigger_parameters(scope,asset_path,source_path):
    """Load/retain the original asset, read its exact trigger, then release it.

    Asset loading is the only engine mutation. No action invocation, struct
    assignment, actor spawn, campaign write or general codec extension occurs.
    """
    scope._check();_validate_paths(asset_path,source_path)
    child=SessionScope(scope)
    try:
        retained=load_asset(child,asset_path);root=retained.return_value
        if root is None:raise RuntimeError('Original asset did not load')
        with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
            catalog=capture_matching(scope.pid,classes=('BP_GameAction_TriggerBattle_C',),names=('FBattleStartParams',))
            catalog=catalog.with_observations(capture_selected(scope.pid,((root.index,root.serial,root.address),)))
            observed=catalog.by_index[root.index]
            if (observed.serial,observed.address)!=(root.serial,root.address) or catalog.path_name(observed).casefold()!=asset_path.casefold():
                raise RuntimeError('Loaded asset differs from the exact retained root')
            source=_owned_source(catalog,observed,source_path)
            descriptor=describe(catalog,(catalog.by_index[source.class_index],))[source.class_index]
            fields=[f for f in descriptor.properties if f['type']=='StructProperty' and f.get('struct_name')=='FBattleStartParams']
            if len(fields)!=1:raise RuntimeError('Expected one original battle-start parameter field')
            field=fields[0]['name']
            values,catalog=read_values_with_references(catalog,source,fields=(field,))
            parameters=[v for k,v in values.values.items() if k[1]==field]
            if len(parameters)!=1 or not isinstance(parameters[0],StoredStruct) or catalog.path_name(parameters[0].type_object)!=BATTLE_STRUCT:
                raise RuntimeError('Original battle-start parameter type did not verify')
            return dict(asset_path=catalog.path_name(observed),source_path=catalog.path_name(source),field=field,
                source_identity=(source.index,source.serial,source.address),parameter_type=BATTLE_STRUCT,
                parameters=_copy(parameters[0],catalog),field_errors={k[1]:str(v) for k,v in values.errors.items()},
                asset_loaded=True,actions_executed=0,actors_spawned=0,encounter_verified=False)
    finally:
        # Leave the read operation before releasing retained engine resources.
        # Cleanup must never borrow a reader that failed during observation.
        child.close()


def exercise_trigger_parameter_copy(scope,asset_path,source_path,*,perform_copy=False,policy_mode=None,enemy_owner=None,entry_preflight=False,bind_arena=False,dispatch=False,arena_policy=0,_source_observer=None):
    """Candidate-only original source match and optional owned copy/cleanup test.

    Policy/arena changes affect only the owned copy. Battle dispatch requires
    explicit isolated arena-entry flags and a separate native capability. The
    original trigger/action chain is never executed or promoted into a catalog.
    """
    scope._check();_validate_paths(asset_path,source_path)
    if _source_observer is not None and not callable(_source_observer):raise ValueError('Invalid private source observer')
    if type(arena_policy) is not int or arena_policy not in (0,1) or (not bind_arena and arena_policy):raise ValueError('Explicit arena policy required')
    if type(perform_copy) is not bool:raise ValueError('Explicit bool copy flag required')
    if type(entry_preflight) is not bool or (entry_preflight and policy_mode is None):
        raise ValueError('Entry preflight requires an explicit policy-copy test')
    if type(bind_arena) is not bool or type(dispatch) is not bool or (bind_arena and not entry_preflight) or (
        dispatch and (not bind_arena or policy_mode!=1)):
        raise ValueError('Arena entry requires explicit preflight; dispatch requires isolated arena entry')
    if policy_mode is not None:
        if type(policy_mode) is not int or policy_mode not in (0,1) or not perform_copy:
            raise ValueError('Policy test requires a copy and exact mode')
        if (enemy_owner is None or enemy_owner._scope is not scope or enemy_owner._closed or
            enemy_owner.phase!='initialized' or enemy_owner.actor_identity is None):
            raise RuntimeError('Policy test requires this scope\'s staged owned enemy')
        anchor_identity=tuple(enemy_owner.actor_identity)
    elif enemy_owner is not None:raise ValueError('Unexpected policy actor owner')
    from ._battle_parameter_owner import ParameterResearchOwner
    child=SessionScope(scope)
    try:
        retained=load_asset(child,asset_path);root=retained.return_value
        if root is None:raise RuntimeError('Original asset did not load')
        with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
            classes=('BP_GameAction_TriggerBattle_C','AC_jRPG_BattleManager_C') if entry_preflight else ('BP_GameAction_TriggerBattle_C',)
            names=('FBattleStartParams','StartBattleNEW') if entry_preflight else ('FBattleStartParams',)
            catalog=capture_matching(scope.pid,classes=classes,names=names)
            catalog=catalog.with_observations(capture_selected(scope.pid,((root.index,root.serial,root.address),)))
            observed=catalog.by_index[root.index]
            if (observed.serial,observed.address)!=(root.serial,root.address) or catalog.path_name(observed).casefold()!=asset_path.casefold():
                raise RuntimeError('Loaded original root identity changed')
            source=_owned_source(catalog,observed,source_path)
            structures=[o for o in catalog.objects if catalog.path_name(o)==BATTLE_STRUCT]
            if len(structures)!=1:raise RuntimeError('Original battle struct is missing or ambiguous')
            identities=(structures[0],source,observed)
            if policy_mode is not None:
                catalog=catalog.with_observations(capture_selected(scope.pid,(anchor_identity,)))
                anchor=catalog.by_index[anchor_identity[0]]
                if (anchor.index,anchor.serial,anchor.address)!=anchor_identity or tuple(enemy_owner.actor_identity)!=anchor_identity:
                    raise RuntimeError('Staged actor identity changed')
            if entry_preflight:
                from .cinematics.original_game_action import controller_context
                context=controller_context(scope._session)
                from ._npc_encounter_preparation import _controller_battle_manager
                catalog=catalog.with_observations(capture_selected(scope.pid,(tuple(context['controller'][1:]),)))
                manager,catalog=_controller_battle_manager(catalog,catalog.by_index[context['controller'][1]])
                path='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:StartBattleNEW'
                functions=[o for o in catalog.objects if catalog.path_name(o)==path]
                if len(functions)!=1:raise RuntimeError('Exact current battle-entry context unavailable')
                entry_identities=(manager,functions[0])
                if controller_context(scope._session)!=context:raise RuntimeError('Travel during entry preflight preparation')
        if _source_observer is not None:_source_observer(source)
        owner=ParameterResearchOwner(child)
        owner.match(identities)
        policy_observation=None
        if policy_mode is not None:
            if entry_preflight:
                if bind_arena:
                    response=owner.entry_arena_cleanup((*identities,anchor,*entry_identities),mode=policy_mode,anchor_owner=enemy_owner._owner,dispatch=dispatch,arena_policy=arena_policy)
                else:
                    response=owner.entry_preflight_cleanup((*identities,anchor,*entry_identities),mode=policy_mode,anchor_owner=enemy_owner._owner)
            else:
                response=owner.policy_cleanup((*identities,anchor),mode=policy_mode,anchor_owner=enemy_owner._owner)
            mode,before,after,verified=struct.unpack_from('<4I',response,4108)
            policy_observation=dict(mode=mode,party_members_before=before,party_members_after=after,
                verified=verified==1,instance_name_from_owned_actor=True)
        elif perform_copy:owner.copy_cleanup(identities)
        return dict(asset_path=asset_path,source_path=source_path,native_source_match=True,
            copy_cleanup_verified=perform_copy,source_parameter_bytes_unchanged=True if perform_copy else None,
            policy=policy_observation,
            entry_preflight_verified=entry_preflight,
            arena_binding_verified=bind_arena,battle_dispatched=dispatch,engine_owned_parameter_copy_verified=dispatch,
            arena_policy=('explicit_current_map' if arena_policy else 'only_if_authored_empty') if bind_arena else None,
            actions_executed=0,actors_spawned=None if dispatch else 0,encounter_verified=False,
            limitation=('Engine entry returned with verified input-copy handoff; encounter outcome needs observation.' if dispatch else
                'Disposable owned copy test only; no battle invocation or original asset changes.'))
    finally:
        child.close()
