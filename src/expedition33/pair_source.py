"""Exact original paired Duolliste graph preflight; no dispatch or save edits.

The original battle Blueprint owns the phase cinematic and P2 summon. The outer
Sequential graph also writes persistent campaign state and is only appropriate
for a separately verified disposable-save or explicitly authorized campaign run.
"""
from dataclasses import dataclass, replace

from . import _paired_phase_frame as frame
from .values import StoredArray, StoredStruct, StoredValues, read_values_with_references

WORLD = frame.WORLD
ARENA = frame.ARENA
ARENA_CLASS = frame.CLASS
PACKAGE = '/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha'
ROOT = PACKAGE + '.DA_GA_SQT_DuallisteAlpha'
ROOT_CLASS = '/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential.BP_GameAction_Sequential_C'
WRAPPER_CLASS = '/Script/SandFall.GameAction_Wrapper'
FLAG = '/Game/Gameplay/ProgressionFlags/SideLevels/NID_BeatDuallisteAlpha.NID_BeatDuallisteAlpha'
_CLASS_PACKAGES = {
    'BP_GameAction_Sequential_C': '/Game/Gameplay/GameActionsSystem/SequentialGameAction/BP_GameAction_Sequential',
    'BP_GameAction_TriggerBattle_C': '/Game/Gameplay/GameActionsSystem/TriggerBattle/BP_GameAction_TriggerBattle',
    'BP_GameAction_WritePersistentFlag_C': '/Game/Gameplay/GameActionsSystem/PersistentFlag/BP_GameAction_WritePersistentFlag',
}


@dataclass(frozen=True)
class PairAction:
    name: str
    path: str
    class_name: str
    wrapper_field: str = 'GameActionInline'

    @property
    def class_path(self):
        return _CLASS_PACKAGES[self.class_name] + '.' + self.class_name


STAGES = (
    PairAction('battle', ROOT + ':BP_GameAction_TriggerBattle_C_1', 'BP_GameAction_TriggerBattle_C'),
    PairAction('campaign_tail', ROOT + ':BP_GameAction_WritePersistentFlag_C_0', 'BP_GameAction_WritePersistentFlag_C'),
)


@dataclass(frozen=True)
class PairSourceGraph:
    root: object
    actions: tuple
    persistent_flag: object = None
    includes_campaign_tail: bool = True


def _field(observed, owner, name, kind):
    if not isinstance(observed, StoredValues) or observed.target != owner:
        raise ValueError('Paired source values belong to another identity')
    key = (owner.class_index, name)
    if observed.types.get(key) != kind or key not in observed.values or key in observed.errors or key in observed.truncated:
        raise ValueError('Complete paired source field required: ' + name)
    return observed.values[key]


def validate_graph(catalog, root, observed):
    """Require both original inline actions in their complete authored order."""
    root = catalog.resolve(root)
    if (catalog.path_name(root) != ROOT or root.object_flags & 0x40000030 or
            catalog.path_name(catalog.by_index[root.class_index]) != ROOT_CLASS):
        raise ValueError('Exact original paired Sequential source required')
    array = _field(observed, root, 'GameActionsToExecute', 'ArrayProperty')
    if not isinstance(array, StoredArray) or array.length != 2 or len(array.items) != 2:
        raise ValueError('Both original paired actions, including campaign tail, required')
    actions = []
    for wrapper, stage in zip(array.items, STAGES):
        if (not isinstance(wrapper, StoredStruct) or wrapper.errors or wrapper.truncated or
                catalog.path_name(catalog.resolve(wrapper.type_object)) != WRAPPER_CLASS or
                set(wrapper.fields) != {'GameActionReference','GameActionInline'} or
                dict(wrapper.types) != {'GameActionReference':'ObjectProperty','GameActionInline':'ObjectProperty'}):
            raise ValueError('Complete exact original GameAction_Wrapper required')
        if wrapper.fields['GameActionReference'] is not None or wrapper.fields['GameActionInline'] is None:
            raise ValueError('Original paired inline wrapper selection differs')
        action = catalog.resolve(wrapper.fields['GameActionInline'])
        if (action.object_flags & 0x40000030 or action.outer_index != root.index or action.outer_serial != root.serial or
                catalog.path_name(action) != stage.path or action.class_name != stage.class_name or
                catalog.path_name(catalog.by_index[action.class_index]) != stage.class_path):
            raise ValueError('Original paired action order or source differs')
        actions.append(action)
    return PairSourceGraph(root, tuple(actions))


def validate_tail(catalog, graph, observed):
    """Require the exact original persistent flag and inherited true value."""
    action = catalog.resolve(graph.actions[1])
    flag = _field(observed, action, 'NamedID', 'ObjectProperty')
    value = _field(observed, action, 'Value', 'BoolProperty')
    if flag is None or value is not True:
        raise ValueError('Original paired persistent completion flag/value differs')
    flag = catalog.resolve(flag)
    if flag.object_flags & 0x40000030 or catalog.path_name(flag) != FLAG:
        raise ValueError('Exact original paired completion NamedID required')
    return replace(graph, persistent_flag=flag)


def observe_graph(catalog, root):
    """Read only the exact graph and its persistent tail; never invoke it."""
    observed, catalog = read_values_with_references(catalog, root, fields=('GameActionsToExecute',))
    graph = validate_graph(catalog, root, observed)
    observed, catalog = read_values_with_references(catalog, graph.actions[1], fields=('NamedID','Value'))
    return validate_tail(catalog, graph, observed), catalog


def validate_original_context(catalog, context, world, arena, pose, *, arena_reference):
    """Check exact active-world/source arena observations and authored frame.

    The caller must freshly obtain context and pose, validate the source soft
    arena reference, and check context again before dispatch. These copied
    observations neither pin actors nor authorize a native call.
    """
    world, arena = catalog.resolve(world), catalog.resolve(arena)
    if (context.get('world') != (world.pid,world.index,world.serial,world.address) or
            context.get('world_path') != WORLD or catalog.path_name(world) != WORLD or
            world.class_name != 'World' or world.object_flags & 0x40000030):
        raise ValueError('Exact current CleasTower world identity required')
    if (arena_reference != ARENA or catalog.path_name(arena) != ARENA or
            catalog.path_name(catalog.by_index[arena.class_index]) != ARENA_CLASS or
            arena.object_flags & 0x40000030 or not any(
                (obj.index,obj.serial,obj.address) == (world.index,world.serial,world.address)
                for obj in catalog.outer_chain(arena))):
        raise ValueError('Exact original paired source arena reference/identity required')
    frame.require_original_frame(context['world_path'], pose)
    return world, arena
