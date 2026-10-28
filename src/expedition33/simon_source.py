"""Exact original Simon graph observations, without dispatch or campaign edits.

This source check is a preflight ingredient, never native invocation authority.
The original Sequential instance must own stage advancement and callbacks. The
complete graph includes persistent progression/reward actions after the outro.
"""
from dataclasses import dataclass

from .values import StoredArray, StoredStruct, StoredValues, read_values_with_references

WORLD = '/Game/Levels/SmallLevels/SimonArea/SmallLevel_SimonArea.SmallLevel_SimonArea'
PACKAGE = '/Game/Levels/SmallLevels/SimonArea/GameActions/DA_GA_SQT_BossSimon'
ROOT = PACKAGE + '.DA_GA_SQT_BossSimon'
ROOT_CLASS = '/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential.BP_GameAction_Sequential_C'
WRAPPER_CLASS = '/Script/SandFall.GameAction_Wrapper'
EXIT = WORLD + ':PersistentLevel.BP_Cine_ExitPoint_C_UAID_C87F5409F1EC9BF501_1760572885'
_CLASS_PACKAGES = {
    'BP_GameAction_Sequential_C': '/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential',
    'BP_GameAction_CinematicWithLightingScenario_C': '/Game/Gameplay/GameActionsSystem/Cinematic/BP_GameAction_CinematicWithLightingScenario',
    'BP_GameAction_TriggerBattle_C': '/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle',
    'BP_GameAction_WritePersistentFlag_C': '/Game/Gameplay/GameActionsSystem/PersistentFlag/BP_GameAction_WritePersistentFlag',
    'BP_GameAction_AddItemToInventory_C': '/Game/Gameplay/GameActionsSystem/Item/BP_GameAction_AddItemToInventory',
    'BP_GameAction_PlaySound_C': '/Game/Gameplay/GameActionsSystem/Audio/PlaySound/BP_GameAction_PlaySound',
}


def _asset(package):
    return package + '.' + package.rsplit('/', 1)[-1]


@dataclass(frozen=True)
class SimonStage:
    name: str
    path: str
    wrapper_field: str
    class_name: str
    sequence: str | None = None
    cinematic_id: str | None = None

    @property
    def class_path(self):
        return _CLASS_PACKAGES[self.class_name] + '.' + self.class_name


STAGES = (
    SimonStage('intro', _asset('/Game/Cinematics/Simon/SimonIntro/DA_GA_CIN_SimonIntro'),
               'GameActionReference', 'BP_GameAction_CinematicWithLightingScenario_C',
               _asset('/Game/Cinematics/Simon/SimonIntro/MCS_SimonIntro'), 'SimonIntro'),
    SimonStage('battle1', ROOT + ':BP_GameAction_TriggerBattle_C_1',
               'GameActionInline', 'BP_GameAction_TriggerBattle_C'),
    SimonStage('transition', _asset('/Game/Cinematics/Simon/SimonIntro/DA_GA_CIN_SimonPhaseTransition'),
               'GameActionReference', 'BP_GameAction_CinematicWithLightingScenario_C',
               _asset('/Game/Characters/Enemies/HumanEnnemies/Simon/Sequences/SEQ_Simon_Skill_10_PhaseSwitch'),
               'SimonPhaseTransition'),
    SimonStage('battle2', ROOT + ':BP_GameAction_TriggerBattle_C_0',
               'GameActionInline', 'BP_GameAction_TriggerBattle_C'),
    SimonStage('outro', _asset('/Game/Cinematics/Simon/SimonOutro/DA_GA_CIN_SimonOutro'),
               'GameActionReference', 'BP_GameAction_CinematicWithLightingScenario_C',
               _asset('/Game/Cinematics/Simon/SimonOutro/MCS_SimonOutro'), 'SimonOutro'),
)
_TAIL = (
    ('BP_GameAction_WritePersistentFlag_C_0', 'BP_GameAction_WritePersistentFlag_C'),
    ('BP_GameAction_AddItemToInventory_C_1', 'BP_GameAction_AddItemToInventory_C'),
    ('BP_GameAction_PlaySound_C_0', 'BP_GameAction_PlaySound_C'),
    ('BP_GameAction_AddItemToInventory_C_2', 'BP_GameAction_AddItemToInventory_C'),
    ('BP_GameAction_AddItemToInventory_C_0', 'BP_GameAction_AddItemToInventory_C'),
)
_EXPECTED = STAGES + tuple(SimonStage('campaign_tail', ROOT + ':' + name,
                                    'GameActionInline', cls) for name, cls in _TAIL)


@dataclass(frozen=True)
class SimonSourceGraph:
    root: object
    actions: tuple
    includes_campaign_tail: bool = True


def validate_graph(catalog, root, observed):
    """Validate the complete copied authored array, including its campaign tail.

    No partial prefix, alternate battle source, truncated wrapper or replacement
    identity is accepted. The result neither loads a world nor authorizes playing
    this save-changing graph. The caller must separately prove current-world,
    cinematic dependency, native admission and disposable-save requirements.
    """
    root = catalog.resolve(root)
    if (catalog.path_name(root) != ROOT or root.object_flags & 0x40000030 or
            catalog.path_name(catalog.by_index[root.class_index]) != ROOT_CLASS):
        raise ValueError('Exact original Simon Sequential source required')
    if not isinstance(observed, StoredValues) or observed.target != root:
        raise ValueError('Simon source values belong to another identity')
    key = (root.class_index, 'GameActionsToExecute')
    if (observed.types.get(key) != 'ArrayProperty' or key in observed.errors or
            key in observed.truncated):
        raise ValueError('Complete original Simon action array required')
    array = observed.values.get(key)
    if not isinstance(array, StoredArray) or array.length != 10 or len(array.items) != 10:
        raise ValueError('All ten original Simon actions required')
    actions = []
    for wrapper, stage in zip(array.items, _EXPECTED):
        if (not isinstance(wrapper, StoredStruct) or wrapper.errors or wrapper.truncated or
                catalog.path_name(catalog.resolve(wrapper.type_object)) != WRAPPER_CLASS or
                set(wrapper.fields) != {'GameActionReference', 'GameActionInline'} or
                dict(wrapper.types) != {'GameActionReference': 'ObjectProperty',
                                        'GameActionInline': 'ObjectProperty'}):
            raise ValueError('Complete exact original GameAction_Wrapper required')
        inactive = 'GameActionInline' if stage.wrapper_field == 'GameActionReference' else 'GameActionReference'
        if wrapper.fields[inactive] is not None or wrapper.fields[stage.wrapper_field] is None:
            raise ValueError('Original Simon wrapper selection differs')
        action = catalog.resolve(wrapper.fields[stage.wrapper_field])
        if (action.object_flags & 0x40000030 or catalog.path_name(action) != stage.path or
                action.class_name != stage.class_name or
                catalog.path_name(catalog.by_index[action.class_index]) != stage.class_path):
            raise ValueError('Original Simon action order or source differs')
        actions.append(action)
    return SimonSourceGraph(root, tuple(actions))


def observe_graph(catalog, root):
    """Bounded read of the original source and missing referenced identities.

    Returns (graph, extended_catalog). This invokes no game function and performs
    no registry-wide scan. The caller retains any source assets independently.
    """
    observed, current = read_values_with_references(catalog, root,
                                                  fields=('GameActionsToExecute',))
    return validate_graph(current, root, observed), current
