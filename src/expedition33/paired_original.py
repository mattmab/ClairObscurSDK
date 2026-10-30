"""Experimental unchanged paired Duolliste graph in original CleasTower only.

The game's Sequential instance and battle Blueprint own progression, cinematic,
P2 summon and campaign completion. This adapter never advances phases, moves
actors, patches source data, cancels actions or destroys cinematic actors.
"""
from . import pair_source as source
from . import _paired_phase_observation as phase
from .simon_original import _Provider as _OriginalProvider, _member, _soft_path
from ._original_action_observation import OriginalActionMonitor
from .catalog import capture_matching, capture_selected
from .cinematics.history import field, identity
from .values import read_values_with_references, StoredArray


def _history_gate(history, context):
    if (history.get('decoded') is not True or history.get('read_error') is not None or
            tuple(history['context_identities']['world']) != tuple(context['world'])):
        raise RuntimeError('Readable paired cinematic history in the current world required')
    # Already-played cinematic IDs warn in the original validator, not reject.
    history['history'].items
    slot = history.get('selected_slot')
    if type(slot) is not int or slot < 0:
        raise RuntimeError('Current disposable paired save slot required')
    return slot


class _Provider(_OriginalProvider):
    def graph(self, catalog, root):
        return source.observe_graph(catalog, root)

    def dependencies(self, scope, catalog, graph, sequence, context):
        from .original_encounter_roster import _verify_source
        from ._npc_encounter_preparation import _controller_battle_manager
        from ._original_trigger_fight import _stored_pose
        sequence = catalog.resolve(sequence)
        if sequence.class_name != 'LevelSequence' or catalog.path_name(sequence) != phase.SEQUENCE:
            raise RuntimeError('Exact retained paired phase LevelSequence required')
        trigger = graph.actions[0]
        _verify_source(scope, trigger, 'Boss_Duolliste_P1')
        observed, catalog = read_values_with_references(catalog, trigger, fields=('Battle Start Params',))
        parameters = field(observed, 'Battle Start Params', 'StructProperty')
        if _member(parameters, 'BattleMapBP_', 'ObjectProperty') is not None:
            raise RuntimeError('Original paired hard arena reference differs')
        arena_path = _soft_path(_member(parameters, 'BattleMapBPSoft_', 'SoftObjectProperty'), 'paired original arena')
        if arena_path != source.ARENA:
            raise RuntimeError('Original paired soft arena source differs')
        catalog = catalog.with_observations(capture_matching(scope.pid, classes=('BP_BattleMap_DuollistAlpha_C',)))
        catalog = catalog.with_observations(capture_selected(scope.pid,
            (tuple(context['controller'][1:]), tuple(context['world'][1:]))))
        arena = catalog.find_path(source.ARENA, 'BP_BattleMap_DuollistAlpha_C')
        from ._world_level_membership import observe_actor_membership
        # A source path/outer chain alone does not prove a streamed level is
        # currently admitted by the active World. Preserve the exact source
        # identity and independently prove reciprocal visible-level membership.
        observe_actor_membership(scope, arena, expected_context=context)
        observed, catalog = read_values_with_references(catalog, arena, fields=('RootComponent',))
        root = field(observed, 'RootComponent', 'ObjectProperty')
        if root is None or root.outer_index != arena.index or root.outer_serial != arena.serial:
            raise RuntimeError('Original paired arena root ownership differs')
        observed, catalog = read_values_with_references(catalog, root,
            fields=('RelativeLocation','RelativeRotation','RelativeScale3D','AttachParent'))
        if field(observed, 'AttachParent', 'ObjectProperty') is not None:
            raise RuntimeError('Original paired arena root is unexpectedly attached')
        values = {name:field(observed,name,'StructProperty')
                  for name in ('RelativeLocation','RelativeRotation','RelativeScale3D')}
        pose = _stored_pose(values)
        source.validate_original_context(catalog, context, catalog.by_index[context['world'][1]],
                                         arena, pose, arena_reference=arena_path)
        manager, catalog = _controller_battle_manager(catalog, catalog.by_index[context['controller'][1]])
        observed, catalog = read_values_with_references(catalog, manager,
            fields=('IsBattleInitialized','HasBattleStartedEndFlow','Enemies','PlayerCharacters','BattleMapBP'))
        if (field(observed,'IsBattleInitialized','BoolProperty') is not False or
                field(observed,'HasBattleStartedEndFlow','BoolProperty') is not False or
                field(observed,'BattleMapBP','ObjectProperty') is not None):
            raise RuntimeError('Original paired battle manager is busy')
        for name in ('Enemies','PlayerCharacters'):
            array = field(observed,name,'ArrayProperty')
            if not isinstance(array,StoredArray) or array.length != 0 or array.items:
                raise RuntimeError('Complete idle paired battle roster required')
        return catalog

    def monitor(self, scope, executor, cinematic, root, context):
        return OriginalActionMonitor(scope,executor=executor,cinematic_system=cinematic,
                                     root=root,root_path=source.ROOT,context=context)

    def phase(self, scope, context):
        return phase.observe(scope, expected_context=context)


def prepare(scope, *, disposable_test=False, _provider=None):
    """Prepare unchanged save-changing original graph after caller isolation.

    Passing disposable_test asserts the caller verified save/config copies and
    restoration paths. No travel occurs here. Repeat handling is original and
    remains visually unverified. History is never cleared or edited. All
    source/context dependencies fail closed.
    """
    scope._check()
    if disposable_test is not True:
        raise RuntimeError('Original paired encounter requires caller-verified disposable saves/config')
    provider = _provider or _Provider()
    owned = provider.child(scope)
    planner = monitor = None
    try:
        context = provider.context(owned)
        if context['world_path'] != source.WORLD:
            raise RuntimeError('Original paired encounter requires exact original CleasTower; no travel performed')
        slot = _history_gate(provider.history(owned), context)
        services = provider.services(owned, context)
        root_hold = provider.load(owned, source.ROOT)
        sequence_hold = provider.load(owned, phase.SEQUENCE)
        root, sequence = root_hold.return_value, sequence_hold.return_value
        if root is None or sequence is None:
            raise RuntimeError('An exact paired source/phase dependency did not load')
        catalog = provider.observations(owned, root, services, (sequence,))
        graph, catalog = provider.graph(catalog, root)
        catalog = provider.dependencies(owned, catalog, graph, sequence, context)
        monitor = provider.monitor(owned, services[1], services[2], root, context)
        if not monitor.observe().idle:
            raise RuntimeError('Original paired executor/cinematic system is busy')
        if provider.context(owned) != context or _history_gate(provider.history(owned), context) != slot:
            raise RuntimeError('Paired context or selected slot changed during preparation')
        planner, call = provider.plan(owned, catalog, services[1], services[3], root)
        return PreparedPair(provider,owned,context,slot,planner,call,monitor,
                            (root_hold,sequence_hold),catalog,root,sequence)
    except BaseException:
        if planner is not None:planner.close()
        if monitor is not None:monitor.close()
        owned.close()
        raise


class PreparedPair:
    def __init__(self,provider,scope,context,slot,planner,call,monitor,holds,catalog,root,sequence):
        self._provider,self._scope,self._context,self._slot = provider,scope,context,slot
        self._planner,self._call,self._monitor,self._holds = planner,call,monitor,holds
        self._catalog,self._root,self._sequence = catalog,root,sequence
        self.state = 'prepared'
        self.dispatch_attempted = self.dispatch_unknown = self.observed_active = False
        self.error = self.observation_error = self.phase_observation_error = None
        self.phase_observation = None
        self.phase_observation_current = False

    def start(self):
        self._scope._check()
        if self.state != 'prepared' or self.dispatch_attempted:
            raise RuntimeError('Original paired dispatch is one-shot and cannot be retried')
        if (self._provider.context(self._scope) != self._context or
                _history_gate(self._provider.history(self._scope),self._context) != self._slot or
                not self._monitor.observe().idle):
            raise RuntimeError('Paired context/history/readiness changed before dispatch')
        graph,catalog = self._provider.graph(self._catalog,self._root)
        self._catalog = self._provider.dependencies(self._scope,catalog,graph,self._sequence,self._context)
        if self._provider.context(self._scope) != self._context:
            raise RuntimeError('Paired context changed during final dependency validation')
        if (_history_gate(self._provider.history(self._scope),self._context) != self._slot or
                not self._monitor.observe().idle):
            raise RuntimeError('Paired history/readiness changed during final dependency validation')
        self.dispatch_attempted = True
        self.state = 'dispatch_pending'
        try:
            with self._call.invoke():pass
        except BaseException as error:
            self.dispatch_unknown = True
            self.state,self.error = 'unknown',str(error)
            raise
        self.state = 'dispatch_acknowledged'
        return self.status()

    def poll(self):
        if self.state in ('closed','world_changed'):return self.status()
        self._scope._check()
        self.phase_observation_current = False
        if not self.dispatch_attempted:return self.status()
        try:
            if self._provider.context(self._scope) != self._context:
                self.state = 'world_changed'
                self.observation_error = 'Original paired world/controller replaced; no stale reads attempted'
                return self.status()
            observed = self._monitor.observe()
        except BaseException as error:
            self.observation_error = str(error)
            if getattr(self._monitor,'world_changed',False):self.state = 'world_changed'
            elif not self.dispatch_unknown:self.state = 'observation_blocked'
            return self.status()
        self.observation_error = None
        if not observed.idle:
            self.observed_active = True
            if not self.dispatch_unknown:self.state = 'original_graph_active'
        elif self.observed_active and not self.dispatch_unknown:self.state = 'idle_after_activity'
        if observed.sequence_player is not None:
            try:
                self.phase_observation = self._provider.phase(self._scope,self._context)
                self.phase_observation_current = True
                self.phase_observation_error = None
            except BaseException as error:
                self.phase_observation_error = str(error)
        return self.status()

    def status(self):
        sample = self.phase_observation
        evidence = None if sample is None else dict(state=sample.state,asset=sample.asset_path,
            requested_id=sample.requested_id,sequence_started=sample.sequence_started,
            camera_target=sample.camera_target,camera_class=sample.camera_class)
        return dict(state=self.state,root=source.ROOT,experimental=True,repeat_supported=False,
            repeat_policy='original',repeat_verified=False,
            dispatch_attempted=self.dispatch_attempted,dispatch_unknown=self.dispatch_unknown,
            observed_active=self.observed_active,error=self.error,observation_error=self.observation_error,
            phase_observation=evidence,phase_observation_error=self.phase_observation_error,
            phase_observation_current=self.phase_observation_current,
            completion_proved=False,visibility_proved=False,includes_campaign_tail=True)

    def close(self):
        if self.state == 'closed':return
        # Only SDK planning copies/asset holds retire. Game-owned action and
        # sequence lifetimes continue through their original callbacks.
        self._planner.close()
        self._monitor.close()
        self._scope.close()
        self.state = 'closed'
