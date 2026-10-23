"""Experimental original battle spawns inside one SDK-owned encounter.

Uses the existing typed Blueprint planner. It never edits encounter tables,
creates exploration recipes, or promotes discovered assets into the catalog.
"""
import re
from .catalog import capture_matching,capture_selected
from ._reader import ReadBatch
from .cinematics.original_game_action import controller_context
from . import _query

BASE='/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Enemy_Battle_Base.BP_jRPG_Enemy_Battle_Base_C'
SPAWN='/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:SpawnEnemyOnSpot'
GLOBAL_ID='EnemyGlobalID_12_57EC6FC84879C6C042EC7BB68F507FE2'


def _owned_global_id(params,name):
    # Other start-parameter fields may be unsupported by the existing reader.
    # Authority depends on this exact observed field, not decoding music/loot.
    return (not params.truncated and GLOBAL_ID not in params.errors and
            params.fields.get(GLOBAL_ID)==name and type(name) is str and bool(name))


def resolve_definition(catalog,recipe_id,definition_row=None):
    if type(recipe_id) is not str:raise ValueError('Expected a catalog recipe ID')
    selected=[e for e in catalog['entries'] if e['id']==recipe_id]
    if len(selected)!=1:raise ValueError('Unknown or ambiguous battle recipe')
    entry=selected[0]
    if entry.get('role')!='battle' or BASE not in entry.get('ancestry',()):
        raise ValueError('An actual enemy battle Blueprint is required')
    rows=entry.get('authored_relationships',{}).get('enemy_definition_rows',())
    if not rows or any(type(r) is not str or not re.fullmatch(r'[A-Za-z0-9_]{1,128}',r) for r in rows):
        raise ValueError('No supported stored enemy-definition relationship')
    if definition_row is None:
        if len(set(rows))!=1:raise ValueError('Choose an explicit enemy-definition row for this variant')
        definition_row=rows[0]
    if type(definition_row) is not str or definition_row not in rows:
        raise ValueError('Definition row does not belong to the selected Blueprint')
    paths={e['class_path'] for e in catalog['entries'] if definition_row in
           e.get('authored_relationships',{}).get('enemy_definition_rows',()) and e.get('role')=='battle'}
    if paths!={entry['class_path']}:raise ValueError('Stored definition maps to ambiguous battle classes')
    return dict(recipe_id=recipe_id,definition_row=definition_row,class_path=entry['class_path'],
                validation=entry.get('validation','discovered'),experimental=True)


def _observe(service):
    from .enemy_spawning import _fields
    from ._npc_encounter_preparation import _controller_battle_manager
    scope=service._scope;session=scope._session
    context=controller_context(session)
    owner_id=tuple(service._owner.actor_identity);arena_id=tuple(service._owner.arena_identity)
    c=capture_matching(scope.pid,names=('SpawnEnemyOnSpot',),classes=('AC_jRPG_BattleManager_C',))
    c=c.with_observations(capture_selected(scope.pid,(owner_id,arena_id,tuple(context['controller'][1:]))))
    owner=c.by_index[owner_id[0]]
    if (owner.index,owner.serial,owner.address)!=owner_id:raise RuntimeError('Owned enemy identity changed')
    flags,c=_fields(c,owner,('IsInBattle',))
    if flags['IsInBattle'] is not True:raise RuntimeError('Owned active battle unavailable')
    # Authored bosses can replace the manager while the default component
    # remains alive. The controller's exact reference is the current authority.
    manager,c=_controller_battle_manager(c,c.by_index[context['controller'][1]])
    values,c=_fields(c,manager,('IsBattleInitialized','Enemies','BattleMapBP','CurrentBattleStartParams',
                              'HasBattleStartedEndFlow','CurrentTurn_CanChooseAction'))
    arena=values['BattleMapBP'];params=values['CurrentBattleStartParams'];roster=values['Enemies']
    if (values['IsBattleInitialized'] is not True or values['HasBattleStartedEndFlow'] is not False or
        values['CurrentTurn_CanChooseAction'] is not True or arena is None or
        (arena.index,arena.serial,arena.address)!=arena_id or not _owned_global_id(params,owner.name) or
        roster.length!=len(roster.items) or not 1<=roster.length<=10 or any(o is None for o in roster.items)):
        raise RuntimeError('Owned encounter, action-selection phase or roster did not verify')
    identities=tuple((o.index,o.serial,o.address) for o in roster.items)
    if len(set(identities))!=len(identities):raise RuntimeError('Duplicate current combatant identities')
    if controller_context(session)!=context:raise RuntimeError('Travel during combat addition observation')
    return dict(catalog=c,context=context,manager=manager,identities=identities,actors=roster.items)


def _invoke(service,snapshot,row,slot,journal):
    from .enemy_spawning import _exact
    c=snapshot['catalog'];session=service._scope._session
    function=_exact(c,SPAWN)
    _,descriptors=_query(['--describe',str(service._scope.pid),f'{function.index}:{function.serial}:{function.address:x}'])
    kinds=('struct','enum','property_class','meta_class','signature_function',
           'inner_struct','inner_enum','inner_property_class','inner_meta_class')
    names={r[k+'_name'] for r in descriptors for k in kinds if k+'_name' in r}
    if names:c=c.with_observations(capture_matching(service._scope.pid,names=tuple(sorted(names))))
    with session.invocation_planner(catalog=c,selected_results=True) as planner:
        planned=planner.prepare_blueprint(snapshot['manager'],function,BattleSpotIndex=slot,
            CharacterHardcodedName=row,NotifyBattleStart=True)
        if controller_context(session)!=snapshot['context']:raise RuntimeError('Travel before combat addition')
        journal['planned']=True
        journal['attempted']=True
        result=planned.invoke()
        result.release()


def add_combatant(service,recipe_id,*,definition_row=None,experimental=False):
    service._scope._check()
    if service._closed:raise RuntimeError('Enemy spawner is closed')
    if experimental is not True:raise ValueError('Combat addition requires explicit experimental=True')
    definition=resolve_definition(service.catalog,recipe_id,definition_row)
    if service._owner.phase!='active' or service._owner.actor_identity is None or service._owner.arena_identity is None:
        raise RuntimeError('Combat addition requires an active SDK-owned encounter')
    journal=service._record.setdefault('combat_additions',[])
    if any(r.get('attempted') and not r.get('verified') for r in journal):
        raise RuntimeError('A previous combat addition is unresolved; retire it rather than retrying')
    entry=None
    try:
        with ReadBatch(service._scope.pid):
            before=_observe(service);slot=len(before['identities'])
            if slot>=10:raise ValueError('Experimental roster is limited to ten enemies')
            positions=service._record.get('extra_battle_positions',{})
            if slot>3 and (positions.get('total_count',0)<=slot or
                          positions.get('enemy_slot_mask',0)&(1<<slot)==0):
                raise RuntimeError('Next battle position was not prepared by this owner')
            entry=dict(definition,slot=slot,planned=False,attempted=False,acknowledged=False,verified=False)
            journal.append(entry)
            _invoke(service,before,definition['definition_row'],slot,entry);entry['acknowledged']=True
            after=_observe(service)
            if (after['context']!=before['context'] or after['identities'][:slot]!=before['identities'] or
                len(after['identities'])!=slot+1):raise RuntimeError('Original spawn did not preserve and extend the roster')
            from .enemy_spawning import _fields,_exact
            actor=after['actors'][slot];c=after['catalog']
            # The roster observation already contains each object's actual
            # class/outer closure. Verify that exact class instead of scanning
            # unrelated live objects again after the spawn has committed.
            expected=_exact(c,definition['class_path'])
            props,c=_fields(c,actor,('BattleSpotIndex',))
            if actor.class_index!=expected.index or props['BattleSpotIndex']!=slot:
                raise RuntimeError('Spawned class or original battle slot differs from stored definition')
            entry.update(verified=True,actor_identity=after['identities'][slot])
    except BaseException as error:
        if entry is not None:
            entry['error']=str(error)
            if entry['attempted']:service._owner.phase='unknown'
        raise
    return dict(entry)
