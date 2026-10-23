"""Evidence-backed authored-instance routes, separate from class availability."""
import json
from functools import lru_cache
from pathlib import Path
SPRONG_RECIPE='d85b762b2231d734'
SPRONG_CLASS='/Game/Characters/Enemies/SpringMeadows/Sprong/BP_EnemyWorld_Sprong.BP_EnemyWorld_Sprong_C'
SPRONG_ARENA='/Game/Levels/Battle_Maps/BattleMap_SpecialEnemies/BP_BattleMap_Sprong.BP_BattleMap_Sprong_C'
SAPLING_RECIPE='4b18373320792d9a'
SAPLING_CLASS='/Game/Characters/Enemies/YellowForest/Sapling/BP_jRPG_EnemyWorld_Sapling.BP_jRPG_EnemyWorld_Sapling_C'


@lru_cache(maxsize=1)
def _standard_candidates():
    return json.loads(Path(__file__).with_name('_authored_standard_routes.json').read_text(encoding='utf8'))['routes']


def authored_spawn_profile(recipe,*,include_unverified=False):
    """Return route evidence without promoting or modifying catalog records."""
    candidate=next((r for r in _standard_candidates() if r['recipe_id']==recipe.get('id')),None)
    if candidate is not None:
        if recipe.get('class_path')!=candidate['class_path']:raise ValueError('Authored route recipe/class identity differs')
        if not include_unverified and recipe.get('verification',{}).get('authored_preparation')!='verified':return None
        verification=recipe.get('verification',{})
        live_combat=verification.get('encounter')=='live_exact_single_enemy_targeting_attacks_and_damage_verified'
        validation=('approach_encounter_user_confirmed' if verification.get('encounter')=='user_confirmed_working_fight'
            else 'approach_encounter_live_combat_verified' if live_combat
            else 'original_preparation_and_selection_verified' if verification.get('authored_preparation')=='verified'
            else 'candidate_asset_relationships_only')
        limitation=(
            'Live walk-up, targeting, damage and enemy attack verified; normal abandonment and cleanup verified. Victory and original-map presentation remain unverified'
            if live_combat and verification.get('own_enemy_turn')=='live_ui_attack_observed_return_to_player_control'
            and verification.get('owned_cleanup')=='live_verified_after_abandonment_and_world_reload'
            else candidate.get('limitation','Individual combat and victory are not claimed; shared standard-enemy behavior has representative confirmation'))
        return dict(route=candidate['route'],encounter_row=candidate['encounter_row'],
            arena_class='/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C',arena_label='standard arena',policy='isolated',
            validation=validation,
            source='Exact original mesh/animation/material variant; actual definition and singleton authored encounter',
            limitation=limitation)
    if recipe.get('id')==SAPLING_RECIPE:
        if recipe.get('class_path')!=SAPLING_CLASS:raise ValueError('Authored route recipe/class identity differs')
        return dict(route=2,encounter_row='YF_Sapling*1',arena_class='/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C',
            policy='isolated',validation='approach_encounter_completed_through_victory',arena_label='standard arena',
            source='Exact original world/battle mesh and animation defaults; actual YF_Sapling row/class reference',
            limitation='Victory and cold CDO retention verified; original placed-map parameter overrides and campaign actions are not copied')
    if recipe.get('id')!=SPRONG_RECIPE:return None
    if recipe.get('class_path')!=SPRONG_CLASS:raise ValueError('Authored route recipe/class identity differs')
    return dict(route=1,encounter_row='WM_Sprong',arena_class=SPRONG_ARENA,
        policy='isolated',validation='approach_encounter_completed_through_victory',arena_label='original Sprong arena',
        limitation='Original arena only; mixed-group framing and campaign actions remain unverified')


def prepare_route(recipe,policy,arena_identity,observation,capability,*,activate=True,experimental_battle_positions=None):
    profile=authored_spawn_profile(recipe)
    if profile is None:raise ValueError('No verified authored-instance route for this recipe')
    if policy!=profile['policy']:raise ValueError('Verified authored route requires isolated mode')
    if type(capability) is not int or capability not in (2,3,4,5,6,7):raise RuntimeError('Authored instance encounter research unavailable')
    if capability<(2 if profile['route']==1 else 3 if profile['route']==2 else 4 if profile['route']<7 else 5 if profile['route']==7 else 6 if profile['route']<12 else 7):raise RuntimeError('Authored route requires the current native candidate')
    if type(activate) is not bool:raise ValueError('Enemy activation flag must be bool')
    if experimental_battle_positions is not None:raise ValueError('Verified authored route does not include expanded positions')
    if (type(arena_identity) not in (tuple,list) or len(arena_identity)!=3 or
        any(type(v) is not int for v in arena_identity)):
        raise ValueError('Select an observed '+profile['arena_label']+' first')
    matches=[a for a in observation['arenas'] if tuple(a['identity'])==tuple(arena_identity)]
    if len(matches)!=1 or matches[0]['class_path']!=profile['arena_class']:
        raise ValueError('Verified authored route requires the current '+profile['arena_label'])
    return dict(policy=policy,arena_identity=tuple(arena_identity),grounded=True,
        activate=activate,authored_instance_route=profile['route'])
