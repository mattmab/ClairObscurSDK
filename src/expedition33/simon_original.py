"""Experimental original Simon, in its original world only.

The original Sequential game action owns all stage progression, battle callbacks,
cinematic actors and persistent rewards. This module never advances stages,
stops cinematics, clears history or modifies source parameters. Repeat handling
remains the original game policy; visible repeated runs are not yet qualified.
"""
from contextlib import nullcontext

from . import simon_source as source
from ._scope import SessionScope
from ._original_action_observation import OriginalActionMonitor, EXECUTOR, CINEMATIC
from .catalog import capture_matching, capture_selected
from .assets import load_asset
from .cinematics.history import field, identity, read_current_history
from .cinematics.original_game_action import controller_context
from .values import StoredArray, StoredStruct, read_values_with_references

TRANSITION_STRUCT = '/Game/Gameplay/GameFlow/Transition/S_GameFlowTransitionRequest.S_GameFlowTransitionRequest'
TRANSITION_ENUM = '/Game/Gameplay/GameFlow/Transition/S_GameFlowTransitionType.S_GameFlowTransitionType'
TRANSITION_FIELD = 'TransitionType_2_AAD1248A4F7B147B0EF7D8A55451E307'


class UnsupportedSimonDependency(RuntimeError):
    """An exact original presentation dependency cannot be proved by the reader."""


def _one(rows, label):
    rows = tuple(rows)
    if len(rows) != 1:
        raise RuntimeError('Expected one current Simon ' + label)
    return rows[0]


def _member(structure, prefix, kind):
    if not isinstance(structure, StoredStruct):
        raise UnsupportedSimonDependency('Unreadable Simon struct for ' + prefix)
    names = [name for name in structure.types if name.startswith(prefix)]
    if len(names) != 1:
        raise UnsupportedSimonDependency('Missing or ambiguous Simon dependency: ' + prefix)
    name = names[0]
    if structure.truncated or structure.types[name] != kind or name in structure.errors or name not in structure.fields:
        detail = structure.errors.get(name, 'unsupported, changed or incomplete field')
        raise UnsupportedSimonDependency(f'Simon dependency {name} ({kind}): {detail}')
    return structure.fields[name]


def _soft_path(value, label):
    # The reader must provide a validated copied soft path. Never infer a source
    # binding merely because loading the expected asset happened to succeed.
    from .values import StoredSoftObjectPath
    if not isinstance(value,StoredSoftObjectPath) or value.path is None or not value.path.startswith('/Game/'):
        raise UnsupportedSimonDependency('Validated copied soft object path required: ' + label)
    return value.path


def _history_gate(history, context):
    if history.get('decoded') is not True or history.get('read_error') is not None:
        raise RuntimeError('Readable current Simon cinematic history required')
    if tuple(history['context_identities']['world']) != tuple(context['world']):
        raise RuntimeError('Simon history belongs to another world')
    # Original ValidateCinematicParameters logs already-played IDs as a warning;
    # it leaves IsValid true. Preserve that policy without editing history.
    history['history'].items
    slot = history.get('selected_slot')
    if type(slot) is not int or slot < 0:
        raise RuntimeError('Current disposable Simon save slot required')
    return slot


def _validate_transition(catalog, transition):
    from .reflection import describe_selected
    from .enums import describe_enums, enum_sentinel
    if (not isinstance(transition,StoredStruct) or
            catalog.path_name(catalog.resolve(transition.type_object)) != TRANSITION_STRUCT):
        raise UnsupportedSimonDependency('Exact original Simon transition struct required')
    # The exact cooked field is ByteProperty backed by a user-defined enum,
    # rather than EnumProperty. Validate that observed enum identity as well.
    number = _member(transition,TRANSITION_FIELD,'ByteProperty')
    if type(number) is not int or number != 2:
        raise RuntimeError('Original Simon post-transition value differs')
    obj = transition.type_object
    selected = describe_selected(catalog.pid,((obj.index,obj.serial,obj.address),))
    descriptor = selected.descriptors[obj.index]
    metadata = _one((row for row in descriptor.properties if row['name'] == TRANSITION_FIELD), 'transition field')
    if metadata.get('type') != 'ByteProperty' or 'enum_index' not in metadata:
        raise UnsupportedSimonDependency('Original Simon transition enum metadata required')
    enum = selected.catalog.by_index[metadata['enum_index']]
    if selected.catalog.path_name(enum) != TRANSITION_ENUM:
        raise RuntimeError('Original Simon transition enum identity differs')
    definition = describe_enums(selected.catalog,(enum,))[enum.index]
    if not any(member.value == number and not enum_sentinel(member.name) for member in definition.members):
        raise RuntimeError('Original Simon transition value is not a current enum member')


def _battle_dependencies(scope,catalog,graph,context):
    """Observe both unchanged battle sources and their loaded original arena.

    A loaded Simon map alone does not prove that the distant arena is streamed.
    No arena is spawned, moved, rebound or loaded by this preflight.
    """
    from .enemy_spawning import load_catalog
    from ._original_trigger_fight import _recipes, _stored_pose, _pose, _same_pose
    from .original_encounter_roster import _verify_source
    from ._npc_encounter_preparation import _controller_battle_manager
    recipes = {row['id']:row for row in _recipes(load_catalog())}
    required = (('simon-normal',1),('simon-phase2',3))
    arenas = []
    for recipe_id,position in required:
        recipe = recipes[recipe_id]
        trigger = catalog.resolve(graph.actions[position])
        profile = recipe['arena']
        if (catalog.path_name(trigger) != recipe['battle_source'] or
                profile['source_world'] != source.WORLD or context['world_path'] != source.WORLD):
            raise RuntimeError('Original Simon battle source/world differs')
        _verify_source(scope,trigger,recipe['encounter'])
        observed,catalog = read_values_with_references(catalog,trigger,fields=('Battle Start Params',))
        parameters = field(observed,'Battle Start Params','StructProperty')
        hard = _member(parameters,'BattleMapBP_','ObjectProperty')
        arena_path = _soft_path(_member(parameters,'BattleMapBPSoft_','SoftObjectProperty'),recipe_id+' original arena')
        if arena_path != profile['source_actor']:
            raise RuntimeError('Original Simon soft arena source differs: '+recipe_id)
        # Target one exact authored actor name, then verify path/class/world.
        catalog = catalog.with_observations(capture_matching(scope.pid,
            names=(profile['source_actor'].rsplit('.',1)[-1],)))
        catalog = catalog.with_observations(capture_selected(scope.pid,
            (tuple(context['controller'][1:]),tuple(context['world'][1:]))))
        world = catalog.by_index[context['world'][1]]
        if (identity(world) != tuple(context['world']) or world.class_name != 'World' or
                world.object_flags & 0x40000030 or catalog.path_name(world) != source.WORLD):
            raise RuntimeError('Current original Simon world identity differs')
        arena = catalog.find_path(profile['source_actor'],'BP_BattleMap_C')
        if (arena.object_flags & 0x40000030 or
                catalog.path_name(catalog.by_index[arena.class_index]) != profile['class_path'] or
                not any(identity(outer) == tuple(context['world']) for outer in catalog.outer_chain(arena))):
            raise RuntimeError('Original Simon arena is absent, stale or outside the current world')
        if hard is not None and identity(catalog.resolve(hard)) != identity(arena):
            raise RuntimeError('Original Simon hard arena reference differs: '+recipe_id)
        observed,catalog = read_values_with_references(catalog,arena,fields=('RootComponent',))
        root = field(observed,'RootComponent','ObjectProperty')
        frame = profile['frames']['DefaultSceneRoot']
        if (root is None or root.object_flags & 0x40000030 or
                (root.outer_index,root.outer_serial) != (arena.index,arena.serial) or
                catalog.path_name(root) != frame['source_path'] or
                catalog.path_name(catalog.by_index[root.class_index]) != frame['class_path']):
            raise RuntimeError('Original Simon arena root ownership/class differs')
        observed,catalog = read_values_with_references(catalog,root,
            fields=('RelativeLocation','RelativeRotation','RelativeScale3D','AttachParent'))
        if field(observed,'AttachParent','ObjectProperty') is not None or frame['parent_field'] is not None:
            raise RuntimeError('Original Simon arena root is unexpectedly attached')
        values = {name:field(observed,name,'StructProperty')
                  for name in ('RelativeLocation','RelativeRotation','RelativeScale3D')}
        pose = _stored_pose(values,limit=1e7)
        expected = _pose(frame['location'],frame['rotation'],frame['scale'],limit=1e7)
        if not _same_pose(pose,expected):
            raise RuntimeError('Original Simon arena frame differs: '+recipe_id)
        arenas.append(identity(arena))
    if arenas[0] != arenas[1]:
        raise RuntimeError('Original Simon stages do not use their same authored arena')
    manager,catalog = _controller_battle_manager(catalog,catalog.by_index[context['controller'][1]])
    observed,catalog = read_values_with_references(catalog,manager,
        fields=('IsBattleInitialized','HasBattleStartedEndFlow','Enemies','PlayerCharacters','BattleMapBP'))
    if (field(observed,'IsBattleInitialized','BoolProperty') is not False or
            field(observed,'HasBattleStartedEndFlow','BoolProperty') is not False or
            field(observed,'BattleMapBP','ObjectProperty') is not None):
        raise RuntimeError('Original Simon battle manager is busy')
    for name in ('Enemies','PlayerCharacters'):
        array = field(observed,name,'ArrayProperty')
        if not isinstance(array,StoredArray) or array.length != 0 or array.items:
            raise RuntimeError('Complete idle original Simon battle roster required')
    return catalog


class _Provider:
    def read_batch(self,scope):
        from ._reader import ReadBatch
        return ReadBatch(scope.pid,share=True,_executable=scope._session._transport._executable)

    def child(self, scope):
        return SessionScope(scope)

    def context(self, scope):
        with self.read_batch(scope):
            return controller_context(scope._session, project=True)

    def history(self, scope):
        with self.read_batch(scope):
            return read_current_history(scope)

    def load(self, scope, path):
        return load_asset(scope, path)

    def services(self, scope, context):
        with self.read_batch(scope):
            return self._services(scope,context)

    def _services(self, scope, context):
        catalog = capture_matching(scope.pid, names=('ExecuteGameAction',),
            classes=('BP_GameActionExecutorComponent_C', 'BP_CinematicSystem_C'))
        def current(obj, cls):
            return (obj.class_name == cls and not obj.object_flags & 0x40000030 and
                    any(identity(outer) == tuple(context['world']) for outer in catalog.outer_chain(obj)))
        executor = _one((obj for obj in catalog.objects if current(obj, 'BP_GameActionExecutorComponent_C')), 'executor')
        cinematic = _one((obj for obj in catalog.objects if current(obj, 'BP_CinematicSystem_C')), 'cinematic system')
        if (catalog.path_name(catalog.by_index[executor.class_index]) != EXECUTOR or
                catalog.path_name(catalog.by_index[cinematic.class_index]) != CINEMATIC or
                (executor.outer_index, executor.outer_serial) != (cinematic.outer_index, cinematic.outer_serial)):
            raise RuntimeError('Simon executor/cinematic service class or owner differs')
        function = _one((obj for obj in catalog.objects if obj.name == 'ExecuteGameAction' and
                        obj.class_name == 'Function' and obj.outer_index == executor.class_index), 'executor function')
        observed,catalog = read_values_with_references(catalog,executor,fields=('GameActionInstancesInExecution',))
        active = field(observed,'GameActionInstancesInExecution','ArrayProperty')
        if not isinstance(active,StoredArray) or active.length != 0 or active.items:
            raise RuntimeError('Simon original executor is busy or incompletely observed')
        observed,catalog = read_values_with_references(catalog,cinematic,
            fields=('LevelSequencePlayer','LoadCinematicAssetRequest'))
        if (field(observed,'LevelSequencePlayer','ObjectProperty') is not None or
                field(observed,'LoadCinematicAssetRequest','ObjectProperty') is not None):
            raise RuntimeError('Simon original cinematic system is busy')
        return catalog, executor, cinematic, function

    def observations(self, scope, root, services, sequences):
        required = (root, *services[1:], *sequences)
        catalog = capture_selected(scope.pid, tuple((obj.index,obj.serial,obj.address) for obj in required))
        catalog = catalog.with_observations(capture_matching(scope.pid, names=('GameAction','GameActionInstance')))
        return catalog

    def graph(self, catalog, root):
        return source.observe_graph(catalog, root)

    def dependencies(self, scope, catalog, graph, sequences, context):
        catalog = _battle_dependencies(scope,catalog,graph,context)
        by_stage = iter(sequences)
        for stage, action in zip(source.STAGES, graph.actions):
            if stage.sequence is None:
                continue
            sequence = next(by_stage)
            sequence = catalog.resolve(sequence)
            if sequence.class_name != 'LevelSequence' or catalog.path_name(sequence) != stage.sequence:
                raise RuntimeError('Exact retained original Simon sequence required')
            observed, catalog = read_values_with_references(catalog, action, fields=('CinematicParameters',))
            parameters = field(observed, 'CinematicParameters', 'StructProperty')
            original_path = _soft_path(_member(parameters, 'Cinematic_LevelSequence_SequenceToPlay_', 'SoftObjectProperty'), stage.name)
            if original_path != stage.sequence or _member(parameters, 'Cinematic_LevelSequence_ID_', 'NameProperty') != stage.cinematic_id:
                raise RuntimeError('Simon original sequence/ID source differs')
            repeat = _member(parameters, 'AllowRepeat_', 'BoolProperty')
            if repeat is not False:
                raise RuntimeError('Simon original AllowRepeat policy differs')
            if stage.name in ('intro','transition'):
                if _member(parameters, 'RestoreExplorationSoundOnEnd_', 'BoolProperty') is not False:
                    raise RuntimeError('Simon original sound restoration differs')
                pre = _member(parameters, 'PreCinematicParameters_', 'StructProperty')
                if _member(pre, 'UseCameraBlendBeforeCine_', 'BoolProperty') is not True:
                    raise RuntimeError('Simon original pre-camera blend differs')
                post = _member(parameters, 'PostCinematicParameters_', 'StructProperty')
                transition = _member(post, 'GameFlowTransitionRequest_', 'StructProperty')
                _validate_transition(catalog,transition)
            else:
                post = _member(parameters, 'PostCinematicParameters_', 'StructProperty')
                exit_path = _soft_path(_member(post, 'BPCineExitPoint_', 'SoftObjectProperty'), 'outro exit')
                if exit_path != source.EXIT:
                    raise RuntimeError('Simon original outro exit differs')
        exits = capture_matching(catalog.pid, classes=('BP_Cine_ExitPoint_C',))
        catalog = catalog.with_observations(exits)
        exit_point = catalog.find_path(source.EXIT, 'BP_Cine_ExitPoint_C')
        if not any(identity(outer) == tuple(context['world']) for outer in catalog.outer_chain(exit_point)):
            raise RuntimeError('Simon outro exit is outside the current original world')
        return catalog

    def monitor(self, scope, executor, cinematic, root, context):
        return OriginalActionMonitor(scope, executor=executor, cinematic_system=cinematic,
                                     root=root, root_path=source.ROOT, context=context)

    def plan(self, scope, catalog, executor, function, root):
        planner = scope.invocation_planner(catalog=catalog, selected_results=True)
        try:
            return planner, planner.prepare_blueprint(executor,function,GameAction=root)
        except BaseException:
            planner.close()
            raise


def prepare(scope, *, disposable_test=False, _provider=None):
    """Prepare the full unchanged original graph in a verified disposable setup.

    The caller must verify save/config isolation before passing disposable_test.
    No save/travel operation is performed here. Unsupported soft-path or enum
    reads reject before dispatch, even when expected assets loaded successfully.
    """
    scope._check()
    if disposable_test is not True:
        raise RuntimeError('Original Simon requires a caller-verified disposable save/config setup')
    provider = _provider or _Provider()
    owned = provider.child(scope)
    planner = monitor = None
    try:
        context = provider.context(owned)
        if context['world_path'] != source.WORLD:
            raise RuntimeError('Original Simon requires its exact original world; no travel performed')
        slot = _history_gate(provider.history(owned), context)
        services = provider.services(owned, context)
        root_hold = provider.load(owned, source.ROOT)
        root = root_hold.return_value
        if root is None:
            raise RuntimeError('Original Simon source did not load')
        sequence_holds = [provider.load(owned,stage.sequence) for stage in source.STAGES if stage.sequence]
        sequences = tuple(hold.return_value for hold in sequence_holds)
        if any(obj is None for obj in sequences):
            raise RuntimeError('An original Simon cinematic sequence did not load')
        # Read-only batches end before native asset loading or dispatch. Use the
        # same candidate reader as the session, not a stale default executable.
        with provider.read_batch(owned) if hasattr(provider,'read_batch') else nullcontext():
            catalog = provider.observations(owned,root,services,sequences)
            graph,catalog = provider.graph(catalog,root)
            catalog = provider.dependencies(owned,catalog,graph,sequences,context)
        monitor = provider.monitor(owned,services[1],services[2],root,context)
        if not monitor.observe().idle:
            raise RuntimeError('Original Simon executor/cinematic system is busy')
        if provider.context(owned) != context or _history_gate(provider.history(owned),context) != slot:
            raise RuntimeError('Simon context or selected slot changed during preparation')
        with provider.read_batch(owned) if hasattr(provider,'read_batch') else nullcontext():
            planner,call = provider.plan(owned,catalog,services[1],services[3],root)
        return PreparedSimon(provider,owned,context,slot,planner,call,monitor,
                             (root_hold,*sequence_holds),catalog,root,sequences)
    except BaseException:
        if planner is not None: planner.close()
        if monitor is not None: monitor.close()
        owned.close()
        raise


class PreparedSimon:
    def __init__(self,provider,scope,context,slot,planner,call,monitor,holds,catalog,root,sequences):
        self._provider,self._scope,self._context,self._slot = provider,scope,context,slot
        self._planner,self._call,self._monitor,self._holds = planner,call,monitor,holds
        self._catalog,self._root,self._sequences = catalog,root,sequences
        self.state = 'prepared'
        self.dispatch_attempted = False
        self.observed_active = False
        self.error = None
        self.observation_error = None

    def start(self):
        self._scope._check()
        if self.state != 'prepared' or self.dispatch_attempted:
            raise RuntimeError('Original Simon dispatch is one-shot and cannot be retried')
        if (self._provider.context(self._scope) != self._context or
                _history_gate(self._provider.history(self._scope),self._context) != self._slot or
                not self._monitor.observe().idle):
            raise RuntimeError('Simon context/history/readiness changed before dispatch')
        with self._provider.read_batch(self._scope) if hasattr(self._provider,'read_batch') else nullcontext():
            graph,catalog = self._provider.graph(self._catalog,self._root)
            self._catalog = self._provider.dependencies(self._scope,catalog,graph,self._sequences,self._context)
        if self._provider.context(self._scope) != self._context:
            raise RuntimeError('Simon context changed during final dependency validation')
        if (_history_gate(self._provider.history(self._scope),self._context) != self._slot or
                not self._monitor.observe().idle):
            raise RuntimeError('Simon history/readiness changed during final dependency validation')
        self.dispatch_attempted = True
        self.state = 'dispatch_pending'
        try:
            with self._call.invoke():
                pass
        except BaseException as error:
            self.state,self.error = 'unknown',str(error)
            raise
        self.state = 'dispatch_acknowledged'
        return self.status()

    def poll(self):
        if self.state == 'closed':
            return self.status()
        self._scope._check()
        if not self.dispatch_attempted: return self.status()
        try:
            observation = self._monitor.observe()
        except BaseException as error:
            self.observation_error = str(error)
            if self.state != 'unknown': self.state = 'observation_blocked'
            return self.status()
        self.observation_error = None
        if not observation.idle:
            self.observed_active = True
            if self.state != 'unknown': self.state = 'original_graph_active'
        elif self.observed_active and self.state != 'unknown':
            self.state = 'idle_after_activity'
        return self.status()

    def status(self):
        return dict(state=self.state,dispatch_attempted=self.dispatch_attempted,
                    observed_active=self.observed_active,error=self.error,
                    observation_error=self.observation_error,
                    root=source.ROOT,experimental=True,repeat_supported=False,
                    repeat_policy='original',repeat_verified=False,
                    completion_proved=False,visibility_proved=False,includes_campaign_tail=True)

    def close(self):
        if self.state == 'closed': return
        # Release only our planning observations/asset leases. Original engine
        # actions and their actors remain engine-owned and are never cancelled.
        self._planner.close()
        self._monitor.close()
        self._scope.close()
        self.state = 'closed'
