"""Original starting rosters through the existing owned parameter adapter.

Candidate-only entry from a prepared, held world anchor. This does not claim
that the anchor is the requested enemy's original exploration representation.
The native source profile, owned-copy policy, arena and entry lifetime remain
authoritative. No late combat additions or encounter-table writes are used.
"""
from copy import deepcopy
from ._reader import ReadBatch
from .catalog import capture_selected
from .values import read_values_with_references,StoredStruct
from .original_trigger_sources import exercise_trigger_parameter_copy

ENCOUNTERS='/Game/jRPGTemplate/Datatables/DT_jRPG_Encounters.DT_jRPG_Encounters'
_ROUTES={
    'a65ad026a55174bc':dict(
        source='/Game/Levels/CleasTower/GameActions/DA_GA_SQT_SimonAlpha.DA_GA_SQT_SimonAlpha:BP_GameAction_TriggerBattle_C_1',
        encounter='Boss_SimonALPHA*1',definition='Boss_Simon_ALPHA',slot=0),
}
# Exact cached source routes; all new identities remain preflight-only.
_ROUTES.update({'f019ec6032602e07': {'source': '/Game/Levels/ForgottenBattlefield/GameActions/DA_GA_SQT_TheDuallist.DA_GA_SQT_TheDuallist:BP_GameAction_TriggerBattle_C_1',
                      'encounter': 'FB_DuallisteLR',
                      'definition': 'FB_DuallisteLR',
                      'slot': 0,
                      'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/BP_EnemyBattle_Duelliste_LR_MainPathBoss.BP_EnemyBattle_Duelliste_LR_MainPathBoss_C',
                      'full_initial_roster': [{'recipe_id': 'f019ec6032602e07',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/BP_EnemyBattle_Duelliste_LR_MainPathBoss.BP_EnemyBattle_Duelliste_LR_MainPathBoss_C',
                                               'definition': 'FB_DuallisteLR',
                                               'slot': 0,
                                               'narrative': False}],
                      'preflight_only_reason': 'The original trigger anchor needs a private save '
                                               'identity and qualified construction/retirement; '
                                               'full route and phase/finisher gameplay remain unverified.'},
 'd6ec611a700522e6': {'source': '/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha.DA_GA_SQT_DuallisteAlpha:BP_GameAction_TriggerBattle_C_1',
                      'encounter': 'Boss_Duolliste_P1',
                      'definition': 'Duolliste_A',
                      'slot': 0,
                      'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_A.BP_Battle_Duolliste_A_C',
                      'full_initial_roster': [{'recipe_id': 'd6ec611a700522e6',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_A.BP_Battle_Duolliste_A_C',
                                               'definition': 'Duolliste_A',
                                               'slot': 0,
                                               'narrative': False},
                                              {'recipe_id': '2ce599dacbb35ccb',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_B.BP_Battle_Duolliste_B_C',
                                               'definition': 'Duolliste_B',
                                               'slot': 1,
                                               'narrative': False}],
                      'preflight_only_reason': 'The original meshless dialogue anchor is identified; '
                                               'isolated NPC construction and the complete A/B '
                                               'to phase-two route remain unverified.'},
 '2ce599dacbb35ccb': {'source': '/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha.DA_GA_SQT_DuallisteAlpha:BP_GameAction_TriggerBattle_C_1',
                      'encounter': 'Boss_Duolliste_P1',
                      'definition': 'Duolliste_B',
                      'slot': 1,
                      'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_B.BP_Battle_Duolliste_B_C',
                      'full_initial_roster': [{'recipe_id': 'd6ec611a700522e6',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_A.BP_Battle_Duolliste_A_C',
                                               'definition': 'Duolliste_A',
                                               'slot': 0,
                                               'narrative': False},
                                              {'recipe_id': '2ce599dacbb35ccb',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Duelliste/Duolliste/BP_Battle_Duolliste_B.BP_Battle_Duolliste_B_C',
                                               'definition': 'Duolliste_B',
                                               'slot': 1,
                                               'narrative': False}],
                      'preflight_only_reason': 'The original meshless dialogue anchor is identified; '
                                               'isolated NPC construction and the complete A/B '
                                               'to phase-two route remain unverified.'},
 '2ce5e0adacadbef7': {'source': '/Game/Levels/ForgottenBattlefield/GameActions/DA_GA_SQT_ArrivingInTheBattlefield.DA_GA_SQT_ArrivingInTheBattlefield:BP_GameAction_TriggerBattle_C_0',
                      'encounter': 'FB_Chalier_GradientCounterTutorial*1',
                      'definition': 'FB_Chalier_GradientCounterTutorial',
                      'slot': 0,
                      'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Chalier/BP_EnemyBattle_Chalier_GradientCounterTutorial.BP_EnemyBattle_Chalier_GradientCounterTutorial_C',
                      'full_initial_roster': [{'recipe_id': '2ce5e0adacadbef7',
                                               'class_path': '/Game/Characters/Enemies/Forgotten_BattleField/Chalier/BP_EnemyBattle_Chalier_GradientCounterTutorial.BP_EnemyBattle_Chalier_GradientCounterTutorial_C',
                                               'definition': 'FB_Chalier_GradientCounterTutorial',
                                               'slot': 0,
                                               'narrative': False}],
                      'preflight_only_reason': 'Original tutorial dismissal writes completion and '
                                               'requests autosave; isolated tutorial state and '
                                               'input cleanup are not implemented.'},
 'd7da3e9d4941e833': {'source': '/Game/Levels/GestralVillage/GameActions/DA_GA_SQT_ScielJoinsGroup_P2_Tutorial.DA_GA_SQT_ScielJoinsGroup_P2_Tutorial:BP_GameAction_Conditional_C_1.BP_GameAction_AskQuestion_C_0.BP_GameAction_TriggerBattle_C_0',
                      'encounter': 'QUEST_DominiqueGiantFeet_ScielTuto*1',
                      'definition': 'GV_GestralScielTuto',
                      'slot': 0,
                      'class_path': '/Game/Characters/Enemies/Gestrals/Gestral_Arena/YellowForestArena/BP_EnemyBattle_Gestral_DominiqueGiantFeet_ScielTuto.BP_EnemyBattle_Gestral_DominiqueGiantFeet_ScielTuto_C',
                      'full_initial_roster': [{'recipe_id': 'd7da3e9d4941e833',
                                               'class_path': '/Game/Characters/Enemies/Gestrals/Gestral_Arena/YellowForestArena/BP_EnemyBattle_Gestral_DominiqueGiantFeet_ScielTuto.BP_EnemyBattle_Gestral_DominiqueGiantFeet_ScielTuto_C',
                                               'definition': 'GV_GestralScielTuto',
                                               'slot': 0,
                                               'narrative': True}],
                      'preflight_only_reason': 'Isolated policy clears the required party '
                                               'override; tutorial state and UI blocker have no '
                                               'isolated owner.'}})

# Exact Monolith source; only the dedicated original-trigger service dispatches it.
_ROUTES.update({'e02190410f616184': {'source': '/Game/Levels/Monolith/Monolith_Interior_Climb/GameActions/DA_GA_SQT_BossMirrorRenoir.DA_GA_SQT_BossMirrorRenoir:BP_GameAction_TriggerBattle_C_2', 'encounter': 'MM_MirrorRenoir', 'definition': 'MM_MirrorRenoir', 'slot': 0, 'class_path': '/Game/Characters/Enemies/MonocoMountain/MirrorRenoir/BP_EnemyBattle_MM_MirrorRenoir_Monolith.BP_EnemyBattle_MM_MirrorRenoir_Monolith_C', 'full_initial_roster': [{'recipe_id': 'e02190410f616184', 'class_path': '/Game/Characters/Enemies/MonocoMountain/MirrorRenoir/BP_EnemyBattle_MM_MirrorRenoir_Monolith.BP_EnemyBattle_MM_MirrorRenoir_Monolith_C', 'definition': 'MM_MirrorRenoir', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact original-trigger direct-fight service and its original arena; the generic held-world-anchor entry is not admitted for this route.'}})

_ROUTES.update({'d4e224bbeb87e684': {'source': '/Game/Levels/EsquieRealCousin/GameActions/DA_GA_SQT_OsquioBoss.DA_GA_SQT_OsquioBoss:BP_GameAction_TriggerBattle_C_1', 'encounter': 'VD_Osquio*1', 'definition': 'VD_Osquio', 'slot': 0, 'class_path': '/Game/Characters/Enemies/Verso_Draft/Osquio/BP_EnemyBattle_Osquio.BP_EnemyBattle_Osquio_C', 'full_initial_roster': [{'recipe_id': 'd4e224bbeb87e684', 'class_path': '/Game/Characters/Enemies/Verso_Draft/Osquio/BP_EnemyBattle_Osquio.BP_EnemyBattle_Osquio_C', 'definition': 'VD_Osquio', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'eb4bb3b3f2a33358': {'source': '/Game/Levels/MonocoStation/GameActions/DA_GA_SQT_MeetingMonoco.DA_GA_SQT_MeetingMonoco:BP_GameAction_TriggerBattle_C_1', 'encounter': 'MS_Monoco', 'definition': 'MS_Monoco', 'slot': 0, 'class_path': '/Game/Characters/Enemies/MonocoStation/BP_EnemyBattle_MS_Monoco.BP_EnemyBattle_MS_Monoco_C', 'full_initial_roster': [{'recipe_id': 'eb4bb3b3f2a33358', 'class_path': '/Game/Characters/Enemies/MonocoStation/BP_EnemyBattle_MS_Monoco.BP_EnemyBattle_MS_Monoco_C', 'definition': 'MS_Monoco', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'84bdfeafeecedf47': {'source': '/Game/Levels/OrangeForest/GameActions/DA_GA_SQT_BossScavenger.DA_GA_SQT_BossScavenger:BP_GameAction_TriggerBattle_C_0', 'encounter': 'YF_Scavenger', 'definition': 'YF_Boss_Scavenger', 'slot': 0, 'class_path': '/Game/Characters/Enemies/YellowForest/Boss_Scavenger/BP_EnemyBattle_Scavenger.BP_EnemyBattle_Scavenger_C', 'full_initial_roster': [{'recipe_id': '84bdfeafeecedf47', 'class_path': '/Game/Characters/Enemies/YellowForest/Boss_Scavenger/BP_EnemyBattle_Scavenger.BP_EnemyBattle_Scavenger_C', 'definition': 'YF_Boss_Scavenger', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'8dcca6e9359e0054': {'source': '/Game/Levels/Monolith/Monolith_Interior_PaintressIntro/GameActions/DA_GA_SQT_PaintressIntro.DA_GA_SQT_PaintressIntro:BP_GameAction_TriggerBattle_C_0', 'encounter': 'ML_PaintressIntro', 'definition': 'ML_PaintressIntro', 'slot': 0, 'class_path': '/Game/Characters/Enemies/Monolith/PaintressIntro/BP_EnemyBattle_PaintressIntro.BP_EnemyBattle_PaintressIntro_C', 'full_initial_roster': [{'recipe_id': '8dcca6e9359e0054', 'class_path': '/Game/Characters/Enemies/Monolith/PaintressIntro/BP_EnemyBattle_PaintressIntro.BP_EnemyBattle_PaintressIntro_C', 'definition': 'ML_PaintressIntro', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'e7e263f066d33733': {'source': '/Game/Levels/SmallLevels/SimonArea/GameActions/DA_GA_SQT_BossSimon.DA_GA_SQT_BossSimon:BP_GameAction_TriggerBattle_C_1', 'encounter': 'Boss_Simon*1', 'definition': 'Boss_Simon', 'slot': 0, 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Simon/BP_EnemyBattle_Simon.BP_EnemyBattle_Simon_C', 'full_initial_roster': [{'recipe_id': 'e7e263f066d33733', 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Simon/BP_EnemyBattle_Simon.BP_EnemyBattle_Simon_C', 'definition': 'Boss_Simon', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'ab11b529310fbd73': {'source': '/Game/Levels/SmallLevels/SimonArea/GameActions/DA_GA_SQT_BossSimon.DA_GA_SQT_BossSimon:BP_GameAction_TriggerBattle_C_0', 'encounter': 'Boss_SimonPhase2*1', 'definition': 'Boss_Simon_Phase2', 'slot': 0, 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Simon/BP_EnemyBattle_Simon_Phase2.BP_EnemyBattle_Simon_Phase2_C', 'full_initial_roster': [{'recipe_id': 'ab11b529310fbd73', 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Simon/BP_EnemyBattle_Simon_Phase2.BP_EnemyBattle_Simon_Phase2_C', 'definition': 'Boss_Simon_Phase2', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ROUTES.update({'9dbac56b68f4cd24': {'source': '/Game/Levels/Monolith/Monolith_Exterior_Peak/GameActions/DA_GA_SQT_BossPaintress.DA_GA_SQT_BossPaintress:BP_GameAction_TriggerBattle_C_0', 'encounter': 'L_Boss_Paintress_P1', 'definition': 'MO_Boss_Paintress', 'slot': 0, 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Aline/BP_EnemyBattle_Paintress_Curatress.BP_EnemyBattle_Paintress_Curatress_C', 'full_initial_roster': [{'recipe_id': '9dbac56b68f4cd24', 'class_path': '/Game/Characters/Enemies/HumanEnnemies/Aline/BP_EnemyBattle_Paintress_Curatress.BP_EnemyBattle_Paintress_Curatress_C', 'definition': 'MO_Boss_Paintress', 'slot': 0, 'narrative': False}], 'preflight_only_reason': 'Use the exact controlled original-trigger direct-fight service; generic held-world-anchor dispatch is not admitted.'}})

_ENCOUNTER_FIELD='EncounterRow_25_76E166214BC95AA2A6A68DAD97A47C62'

def resolve_source(catalog,recipe_id):
    route=_ROUTES.get(recipe_id)
    if route is None:raise ValueError('No admitted original starting-roster source for this enemy')
    entries=[row for row in catalog['entries'] if row.get('id')==recipe_id]
    if len(entries)!=1:raise ValueError('Missing or ambiguous original enemy identity')
    relations=entries[0].get('authored_relationships',{})
    matches=[row for row in relations.get('authored_encounters',()) if
        row.get('row')==route['encounter'] and row.get('enemy_row')==route['definition'] and row.get('slot')==route['slot']]
    if len(matches)!=1 or route['definition'] not in relations.get('enemy_definition_rows',()):
        raise ValueError('Original starting-roster relationship does not match the catalog evidence')
    # Prove every initial member, including the paired Duolliste counterpart.
    # A familiar class/mesh name cannot replace an exact definition+slot join.
    for expected in route.get('full_initial_roster', ()):
        members=[row for row in catalog['entries'] if row.get('id')==expected['recipe_id']]
        if len(members)!=1 or members[0].get('class_path')!=expected['class_path']:
            raise ValueError('Exact initial-roster class identity is missing or changed')
        relationships=members[0].get('authored_relationships', {})
        exact=[row for row in relationships.get('authored_encounters', ()) if
            row.get('row')==route['encounter'] and row.get('enemy_row')==expected['definition'] and
            row.get('slot')==expected['slot'] and row.get('narrative')==expected['narrative']]
        if len(exact)!=1 or expected['definition'] not in relationships.get('enemy_definition_rows', ()):
            raise ValueError('Full initial-roster relationship is missing or changed')
    if 'full_initial_roster' in route:
        # Inclusion is insufficient: an unexpected third member must also fail.
        # Use all cached battle-class relationships for this exact encounter.
        observed=[]
        for member in catalog['entries']:
            if member.get('role')!='battle':
                continue
            for relationship in member.get('authored_relationships', {}).get('authored_encounters', ()):
                if relationship.get('row')==route['encounter']:
                    observed.append(dict(recipe_id=member.get('id'), class_path=member.get('class_path'),
                        definition=relationship.get('enemy_row'), slot=relationship.get('slot'),
                        narrative=relationship.get('narrative')))
        expected=route['full_initial_roster']
        if len(observed)!=len(expected) or any(member not in expected for member in observed):
            raise ValueError('Complete initial-roster relationships differ from the exact route')
    return deepcopy(dict(route,recipe_id=recipe_id,asset_path=route['source'].split(':',1)[0]))

def _verify_source(scope,source,expected):
    with ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable):
        c=capture_selected(scope.pid,((source.index,source.serial,source.address),))
        values,c=read_values_with_references(c,c.by_index[source.index],fields=('Battle Start Params',))
        params=[v for k,v in values.values.items() if k[1]=='Battle Start Params']
        if values.errors or len(params)!=1 or not isinstance(params[0],StoredStruct):
            raise RuntimeError('Original battle parameters could not be inspected')
        handle=params[0].fields.get(_ENCOUNTER_FIELD)
        if not isinstance(handle,StoredStruct) or handle.errors or handle.truncated:
            raise RuntimeError('Original encounter handle is incomplete')
        table=handle.fields.get('DataTable')
        if table is None or c.path_name(table)!=ENCOUNTERS or handle.fields.get('RowName')!=expected:
            raise RuntimeError('Original trigger does not contain the expected starting roster')

def enter_original(service,recipe_id,*,experimental=False,dispatch=False):
    service._scope._check()
    if service._closed:raise RuntimeError('Enemy spawner is closed')
    if experimental is not True or type(dispatch) is not bool:
        raise ValueError('Original starting-roster entry requires explicit experimental=True and bool dispatch')
    transport=service._scope._session._transport
    if getattr(transport,'owned_authored_entry_protocol',0)!=1:
        raise RuntimeError('Original starting-roster entry requires the updated SDK lifetime guards')
    route=resolve_source(service.catalog,recipe_id)
    if dispatch and route.get('preflight_only_reason'):
        raise RuntimeError('Original-source dispatch remains blocked: '+route['preflight_only_reason'])
    if (service._owner.phase!='initialized' or service._record.get('stage')!='prepared' or
        service._record.get('policy')!='isolated' or service._owner.arena_identity is None):
        raise RuntimeError('Prepare an isolated held world anchor and bind its arena first')
    if service._record.get('authored_battle',{}).get('attempted'):
        raise RuntimeError('Original encounter entry was already attempted; no replay')
    journal=dict(route,attempted=dispatch,acknowledged=False,initial_roster_verified=False,
                 exploration_assembly_verified=False,late_additions_used=False)
    if dispatch:service._record['authored_battle']=journal
    try:
        result=exercise_trigger_parameter_copy(service._scope,route['asset_path'],route['source'],
            perform_copy=True,policy_mode=1,enemy_owner=service._owner,entry_preflight=True,
            bind_arena=True,dispatch=dispatch,arena_policy=1,
            _source_observer=lambda source:_verify_source(service._scope,source,route['encounter']))
        journal.update(acknowledged=True,entry=result)
        if dispatch:service._record['stage']='authored_battle_starting'
    except BaseException as error:
        journal['error']=str(error)
        raise
    return dict(journal)
