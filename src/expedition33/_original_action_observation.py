"""Bounded, observation-only evidence for original encounter action playback.

An empty executor is not a victory/completion callback. These snapshots never
advance a stage, stop a game-owned sequence, or grant actor destruction authority.
"""
from dataclasses import dataclass

from ._reader import ReadBatch
from .catalog import capture_selected
from .cinematics.history import identity, field
from .cinematics.original_game_action import controller_context
from .values import read_values_with_references, StoredArray

ROOTS = frozenset((
    '/Game/Levels/SmallLevels/SimonArea/GameActions/DA_GA_SQT_BossSimon.DA_GA_SQT_BossSimon',
    '/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha.DA_GA_SQT_DuallisteAlpha',
))
EXECUTOR = '/Game/Gameplay/GameActionsSystem/BP_GameActionExecutorComponent.BP_GameActionExecutorComponent_C'
CINEMATIC = '/Game/Gameplay/CinematicSystem/BP_CinematicSystem.BP_CinematicSystem_C'
@dataclass(frozen=True)
class ActionInstanceObservation:
    identity: tuple
    path: str
    class_path: str
    sequential_action: str | None = None
    next_index: int | None = None
    autosave: bool | None = None
    player_controller: tuple | None = None
    action_path: str | None = None
    parent: tuple | None = None
    action_identity: tuple | None = None


@dataclass(frozen=True)
class OriginalActionObservation:
    context: tuple
    root: str
    instances: tuple
    sequence_player: tuple | None
    sequence_path: str | None
    sequence_status: object
    pending_asset_request: tuple | None

    @property
    def idle(self):
        return not self.instances and self.sequence_player is None and self.pending_asset_request is None


def _fields(catalog, obj, names):
    observed, catalog = read_values_with_references(catalog, obj, fields=tuple(names))
    result = {}
    for name, kinds in names.items():
        kinds = (kinds,) if isinstance(kinds, str) else kinds
        matches = [key for key in observed.types if key[1] == name]
        if len(matches) != 1 or observed.types[matches[0]] not in kinds:
            raise RuntimeError('Unexpected original action field type: ' + name)
        result[name] = field(observed, name, observed.types[matches[0]])
    return result, catalog


def _in_world(catalog, obj, world):
    return any(identity(outer) == world for outer in catalog.outer_chain(obj))


class _ActionMonitor:
    """One scope/context's copied observations, never a playback owner.

    Supply already observed executor/cinematic/root identities after preparation.
    The root path must be explicitly supplied and remains an attribution label:
    executor instance rows alone do not prove which action created them. No API
    here reports success, victory or cinematic visibility.
    """
    def __init__(self, scope, *, executor, cinematic_system, root, root_path, context):
        scope._check()
        self._scope = scope
        self._identities = tuple(identity(obj) for obj in (executor, cinematic_system, root))
        if any(row[0] != scope.pid for row in self._identities):
            raise ValueError('Original action observations belong to another process')
        self._context = (tuple(context['controller']), tuple(context['world']), context['world_path'])
        self.root_path = root_path
        self._closed = False
        self.world_changed = False

    def close(self):
        # Local copies only; no attempt to stop or release game-owned actions.
        self._closed = True

    def observe(self):
        self._scope._check()
        if self._closed or self.world_changed:
            raise RuntimeError('Original action monitor is closed or world was replaced')
        executable = self._scope._session._transport._executable
        with ReadBatch(self._scope.pid, share=True, _executable=executable):
            context = controller_context(self._scope._session, project=True)
            current = (tuple(context['controller']), tuple(context['world']), context['world_path'])
            if current != self._context:
                self.world_changed = True
                raise RuntimeError('Original action world/controller replaced; no stale reads attempted')
            catalog = capture_selected(self._scope.pid, tuple(row[1:] for row in self._identities))
            executor, cinematic, root = (catalog.by_index[row[1]] for row in self._identities)
            if catalog.path_name(root) != self.root_path:
                raise RuntimeError('Original action root identity/path differs')
            if executor.class_name != 'BP_GameActionExecutorComponent_C' or cinematic.class_name != 'BP_CinematicSystem_C':
                raise RuntimeError('Original action service classes differ')
            if (catalog.path_name(catalog.by_index[executor.class_index]) != EXECUTOR or
                    catalog.path_name(catalog.by_index[cinematic.class_index]) != CINEMATIC):
                raise RuntimeError('Original action service class packages differ')
            if executor.outer_index != cinematic.outer_index or executor.outer_serial != cinematic.outer_serial:
                raise RuntimeError('Original action services have different owners')
            if not all(_in_world(catalog, obj, current[1]) for obj in (executor, cinematic)):
                raise RuntimeError('Original action services belong to another world')
            values, catalog = _fields(catalog, executor, {'GameActionInstancesInExecution': 'ArrayProperty'})
            active = values['GameActionInstancesInExecution']
            if not isinstance(active, StoredArray) or active.length != len(active.items) or active.length > 64:
                raise RuntimeError('Complete bounded executor instance array required')
            if any(obj is None for obj in active.items) or len({identity(obj) for obj in active.items}) != active.length:
                raise RuntimeError('Null or duplicate executor instance identity')
            instances, seen = [], set()
            pending = [(obj, None, 0) for obj in active.items]
            while pending:
                obj, parent, depth = pending.pop(0)
                if identity(obj) in seen or depth > 8 or len(seen) >= 64:
                    raise RuntimeError('Action instance chain is cyclic or exceeds observation bound')
                seen.add(identity(obj))
                values, catalog = _fields(catalog, obj, {'GameAction': 'ObjectProperty'})
                action = values['GameAction']
                action_path = catalog.path_name(action) if action is not None else None
                sequential = None
                next_index = autosave = player_controller = None
                if obj.class_name == 'BP_GameActionInstance_Sequential_C':
                    values, catalog = _fields(catalog, obj, {'GameActionSequential': 'ObjectProperty',
                        'NextIndex': 'IntProperty', 'ShouldTriggerAutoSave': 'BoolProperty',
                        'PlayerController': 'ObjectProperty', 'ChildGameActionInstance': 'ObjectProperty'})
                    sequential = catalog.path_name(values['GameActionSequential']) if values['GameActionSequential'] is not None else None
                    next_index, autosave = values['NextIndex'], values['ShouldTriggerAutoSave']
                    player_controller = identity(values['PlayerController']) if values['PlayerController'] is not None else None
                    if type(next_index) is not int or next_index < 0 or type(autosave) is not bool:
                        raise RuntimeError('Invalid sequential observation state')
                    if player_controller != current[0]:
                        raise RuntimeError('Sequential action controller differs from current controller')
                    child = values['ChildGameActionInstance']
                    if child is not None:
                        if child.outer_index != obj.index or child.outer_serial != obj.serial:
                            raise RuntimeError('Original child action instance outer differs from parent')
                        pending.append((child, identity(obj), depth + 1))
                instances.append(ActionInstanceObservation(identity(obj), catalog.path_name(obj),
                    catalog.path_name(catalog.by_index[obj.class_index]), sequential, next_index, autosave,
                    player_controller, action_path, parent,
                    identity(action) if action is not None else None))
            values, catalog = _fields(catalog, cinematic, {'LevelSequencePlayer': 'ObjectProperty',
                                                         'LoadCinematicAssetRequest': 'ObjectProperty'})
            player, request = values['LevelSequencePlayer'], values['LoadCinematicAssetRequest']
            sequence_path = status = None
            if player is not None:
                values, catalog = _fields(catalog, player, {'Sequence': 'ObjectProperty', 'Status': ('ByteProperty', 'EnumProperty')})
                sequence_path = catalog.path_name(values['Sequence']) if values['Sequence'] is not None else None
                status = values['Status']
            again = controller_context(self._scope._session, project=True)
            if (tuple(again['controller']), tuple(again['world']), again['world_path']) != current:
                self.world_changed = True
                raise RuntimeError('Original action context changed during observation; discard snapshot')
        return OriginalActionObservation(current, self.root_path, tuple(instances),
            identity(player) if player is not None else None, sequence_path, status,
            identity(request) if request is not None else None)


class OriginalActionMonitor(_ActionMonitor):
    def __init__(self, scope, *, executor, cinematic_system, root, root_path, context):
        if root_path not in ROOTS:
            raise ValueError('Exact original encounter root required')
        super().__init__(scope, executor=executor, cinematic_system=cinematic_system,
                         root=root, root_path=root_path, context=context)


class CinematicActionMonitor(_ActionMonitor):
    """The encounter observer with independently checked cinematic admission."""
    def __init__(self, scope, *, prepared, profile):
        from .cinematics.original_game_action import profiles
        admitted = profiles().get(profile.get('id'))
        if admitted is None or admitted != profile:
            raise ValueError('Exact reviewed original cinematic profile required')
        super().__init__(scope, executor=prepared.executor, cinematic_system=prepared.component,
                         root=prepared.asset, root_path=profile['action_path'], context=prepared.context)
