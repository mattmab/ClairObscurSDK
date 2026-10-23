"""Bounded main-Duelliste sequence observation and positively attributed cleanup.

Baseline/delta alone never authorizes destruction. Existing game-created actors
remain diagnostic unless an owned battle character's reciprocal Epic helper
link was observed. No Stop, interruption, forced GC, factory or native owner.
"""
import time

SOURCE = '/Game/Levels/ForgottenBattlefield/GameActions/DA_GA_SQT_TheDuallist.DA_GA_SQT_TheDuallist:BP_GameAction_TriggerBattle_C_1'
FINISHER = '/Game/Cinematics/ForgottenBattlefield/Finisher/CS_Finisher_Duallist.CS_Finisher_Duallist'
EPIC = '/Game/Gameplay/EpicBattleSequence/BP_EpicBattleSequenceActor.BP_EpicBattleSequenceActor_C'
DESTROY = '/Script/Engine.Actor:K2_DestroyActor'


def _identity(obj):
    return obj.index, obj.serial, obj.address


def _key(identity):
    # A pre-retention serial may be zero. Preserve the baseline conservatively
    # across serial stabilization; index/address reuse can only exclude a row.
    return identity[0], identity[2]


def _read(scope, *, inventory=False):
    from ._reader import ReadBatch
    from .catalog import capture_matching, capture_selected
    from .enemy_spawning import _fields, _exact
    from ._npc_encounter_preparation import _controller_battle_manager
    from .cinematics.original_game_action import controller_context
    with ReadBatch(scope.pid, share=True, _executable=scope._session._transport._executable):
        context = controller_context(scope._session)
        c = capture_selected(scope.pid, (tuple(context['controller'][1:]), tuple(context['world'][1:])))
        if inventory:
            c = c.with_observations(capture_matching(scope.pid,
                classes=('LevelSequenceActor', 'BP_EpicBattleSequenceActor_C'), names=('K2_DestroyActor',)))
        world_id = tuple(context['world'][1:])
        manager, c = _controller_battle_manager(c, c.by_index[context['controller'][1]])
        battle, c = _fields(c, manager, ('IsBattleInitialized', 'HasBattleStartedEndFlow',
            'CurrentBattleStartParams', 'BattleMapBP', 'Enemies', 'PlayerCharacters'))
        characters = []
        character_objects = []
        for field in ('Enemies', 'PlayerCharacters'):
            value = battle[field]
            if value.length != len(value.items) or any(o is None for o in value.items):
                raise RuntimeError('Complete current battle character arrays required')
            characters.extend(_identity(o) for o in value.items)
            character_objects.extend(value.items)
        if len(characters) > 32:
            raise RuntimeError('Bounded combat character observation exceeded')
        selected = {}
        if not inventory:
            # Normal combat polling follows owned roster references. Never scan
            # global classes/names just to discover a sequence every frame.
            for character in character_objects:
                values, c = _fields(c, character, ('CurrentComboSequence',))
                helper = values['CurrentComboSequence']
                if helper is None:
                    continue
                if c.path_name(c.by_index[helper.class_index]) != EPIC:
                    continue
                selected[helper.index] = helper
                values, c = _fields(c, helper, ('LevelSequenceActor',))
                if values['LevelSequenceActor'] is not None:
                    actor = values['LevelSequenceActor']
                    selected[actor.index] = actor
        rows = [o for o in (c.objects if inventory else selected.values())
                if o.class_name in ('LevelSequenceActor', 'BP_EpicBattleSequenceActor_C')
                and any(_identity(a) == world_id for a in c.outer_chain(o))]
        if len(rows) > 64:
            raise RuntimeError('Bounded current-world sequence inventory exceeded')
        params = battle['CurrentBattleStartParams']
        private = [str(v) for k, v in params.fields.items() if k.startswith('EnemyGlobalID_')]
        arena = battle['BattleMapBP']
        result = dict(context=context, manager=_identity(manager), started=battle['IsBattleInitialized'], ending=battle['HasBattleStartedEndFlow'],
            arena=_identity(arena) if arena else None, characters=characters,
            private_id=private[0] if len(private) == 1 else None, sequences={}, epics=[])
        for obj in rows:
            identity = _identity(obj)
            garbage = bool(obj.object_flags & 0x40000000 or getattr(obj, 'item_flags', 0) & 0x200000)
            if obj.class_name == 'BP_EpicBattleSequenceActor_C':
                if garbage:
                    continue
                if c.path_name(c.by_index[obj.class_index]) != EPIC:
                    raise RuntimeError('Unexpected Epic helper class')
                values, c = _fields(c, obj, ('SourceCharacter', 'LevelSequenceActor'))
                source, actor = values['SourceCharacter'], values['LevelSequenceActor']
                reciprocal = False
                if source is not None and _identity(source) in characters:
                    own, c = _fields(c, source, ('CurrentComboSequence',))
                    reciprocal = own['CurrentComboSequence'] is not None and _identity(own['CurrentComboSequence']) == identity
                result['epics'].append(dict(identity=identity, source=_identity(source) if source else None,
                    actor=_identity(actor) if actor else None, reciprocal=reciprocal))
                continue
            row = dict(identity=identity, actor=obj, garbage=garbage)
            result['sequences'][_key(identity)] = row
            if garbage:
                continue
            if c.path_name(c.by_index[obj.class_index]) != '/Script/LevelSequence.LevelSequenceActor':
                raise RuntimeError('Unexpected sequence actor class')
            values, c = _fields(c, obj, ('SequencePlayer', 'LevelSequenceAsset'))
            player, asset = values['SequencePlayer'], values['LevelSequenceAsset']
            row.update(asset_path=c.path_name(asset) if asset else None,
                       player_identity=_identity(player) if player else None)
            if row['asset_path'] != FINISHER:
                continue
            if player is None or asset is None:
                raise RuntimeError('Exact finisher actor/player pair required')
            values, c = _fields(c, player, ('Status', 'Sequence', 'PlaybackSettings'))
            settings = values['PlaybackSettings'].fields
            row.update(player=player, status=values['Status'],
                player_outer_matches=player.outer_index == obj.index,
                player_asset_matches=values['Sequence'] is not None and _identity(values['Sequence']) == _identity(asset),
                locks_clear=all(settings.get(k) is False for k in
                    ('bDisableMovementInput', 'bDisableLookAtInput', 'bHidePlayer', 'bHideHud')))
        result['catalog'] = c
        result['destroy'] = _exact(c, DESTROY) if inventory else None
    with ReadBatch(scope.pid, share=True, _executable=scope._session._transport._executable):
        if controller_context(scope._session) != context:
            raise RuntimeError('Context changed during sequence inventory')
    return result


class OriginalFightSequenceCleanup:
    """One route's persistent diagnostics/retained identities; same parent scope.

    Call baseline() before op130, entry_attempted() immediately before op130,
    observe_active(snapshot) during ordinary fight polls; observe() is a single
    inventory at an active-to-idle boundary. Close before route source holds.
    Unattributed deltas are reported but never become an automatic destroy list.
    """
    def __init__(self, scope, *, source):
        if source != SOURCE:
            raise ValueError('Only the exact original main Duelliste source is qualified')
        self._scope = scope
        self.context = None
        self.baseline_keys = None
        self.baseline_records = []
        self.private_id = None
        self.arena = None
        self.entries = {}
        self.diagnostics = []
        self.uncertain = False
        self.closed = False
        self._idle_since = None

    @staticmethod
    def _idle(snapshot):
        return (snapshot['started'] is False and snapshot['ending'] is False
                and snapshot['arena'] is None and not snapshot['characters'])

    def _fresh(self, *, inventory=False):
        self._scope._check()
        if self.closed or self.uncertain:
            raise RuntimeError('Closed or uncertain sequence cleanup cannot mutate or replay')
        snapshot = _read(self._scope, inventory=inventory)
        if self.context is not None and snapshot['context'] != self.context:
            raise RuntimeError('Original fight context changed; preserve sequence holds')
        return snapshot

    def baseline(self):
        if self.baseline_keys is not None:
            raise RuntimeError('Sequence baseline cannot be replaced')
        snapshot = self._fresh(inventory=True)
        if not self._idle(snapshot):
            raise RuntimeError('Idle battle required before sequence baseline')
        self.context = snapshot['context']
        self.baseline_keys = set(snapshot['sequences'])
        self.baseline_records = [dict(identity=row['identity'], asset_path=row.get('asset_path'))
                                 for row in snapshot['sequences'].values()]
        return self.status()

    def entry_attempted(self, *, private_id, arena_identity):
        self._scope._check()
        if self.closed or self.uncertain:
            raise RuntimeError('Closed or uncertain sequence component cannot accept entry')
        if self.baseline_keys is None or self.private_id is not None:
            raise RuntimeError('One pre-entry baseline required')
        if not isinstance(private_id, str) or private_id in ('', 'None') or len(arena_identity) != 3:
            raise ValueError('Exact private trigger identity and arena required')
        self.private_id, self.arena = private_id, tuple(arena_identity)

    def observe(self):
        """Bounded inventory at the active-to-idle boundary, not each poll."""
        return self._observe(self._fresh(inventory=True))

    def observe_active(self, expected):
        """Selected-only reciprocal attribution from the service's owned battle."""
        snapshot = self._fresh()
        for field in ('context', 'manager', 'started', 'ending', 'private_id', 'arena'):
            if snapshot[field] != expected[field]:
                raise RuntimeError('Selected battle observation changed before sequence attribution')
        if sorted(snapshot['characters']) != sorted(tuple(value) for value in expected['characters']):
            raise RuntimeError('Complete selected combat roster changed before sequence attribution')
        return self._observe(snapshot)

    def _observe(self, snapshot):
        if self.baseline_keys is None or self.private_id is None:
            raise RuntimeError('Entry intent required before observing owned sequences')
        owned_active = (snapshot['started'] is True and snapshot['private_id'] == self.private_id
                        and snapshot['arena'] == self.arena)
        self.diagnostics = []
        for key, row in snapshot['sequences'].items():
            if key in self.baseline_keys or row['garbage'] or row.get('asset_path') != FINISHER:
                continue
            if key in self.entries:
                continue
            proofs = [p for p in snapshot['epics'] if p['actor'] == row['identity'] and p['reciprocal']
                      and p['source'] in snapshot['characters']]
            if (not owned_active or len(proofs) != 1 or not row.get('player_outer_matches')
                    or not row.get('player_asset_matches')):
                self.diagnostics.append(dict(identity=row['identity'], reason='No observed owned Epic-helper relationship'))
                continue
            entry = dict(identity=row['identity'], player_identity=row['player_identity'], proof=proofs[0],
                         leases=[], destroy_attempted=False, destroy_acknowledged=False, retired=False)
            self.entries[key] = entry  # Persistent before the first acquire.
            for obj in (row['actor'], row['player']):
                self.uncertain = True
                lease = self._scope.retain(obj)
                entry['leases'].append(lease)
                if _key(_identity(lease.object)) != _key(_identity(obj)):
                    raise RuntimeError('Retained sequence identity changed')
                self.uncertain = False
            entry['identity'] = _identity(entry['leases'][0].object)
            entry['player_identity'] = _identity(entry['leases'][1].object)
        return self.status()

    def poll(self, snapshot):
        return self.observe_active(snapshot)

    def close_after_world_change(self):
        """Release observation holds only; never destroy old/new world actors.

        The original game owns these sequence actors. On a replaced world its
        teardown owns their destruction; retaining SDK observation leases must
        not pin that world or require its vanished controller to report idle.
        """
        if self.closed:return True
        if self.uncertain:return False
        pending=False
        for entry in self.entries.values():
            for lease in entry['leases']:
                if getattr(lease,'_state',None)=='released':continue
                if lease.release_pending:pending=True;continue
                self.uncertain=True
                released=lease.release()
                self.uncertain=False
                if released is not True:pending=True
            entry['observation_holds_released']=all(getattr(v,'_state',None)=='released' for v in entry['leases'])
        if pending:return False
        self.closed=True
        return True

    def close(self):
        if self.closed:
            return True
        if not self.entries:
            # Optional baseline/observation failures grant no ownership. Never
            # make unrelated sequence reads a prerequisite to close this route.
            self.closed = True
            return True
        snapshot = self._fresh()
        if not self._idle(snapshot) or snapshot['epics']:
            self._idle_since = None
            return False
        now = time.monotonic()
        if self.entries and self._idle_since is None:
            self._idle_since = now
            return False
        if self.entries and now - self._idle_since < .5:
            return False  # Let the original QueueDestroyActor's 0.5 s path run.
        # Explicit retirement needs fresh candidate/player state and a complete
        # no-Epic check. This is outside ordinary polling and only for attributed
        # pairs; no-owned-entry close above performs no inventory or reads.
        snapshot = self._fresh(inventory=True)
        if not self._idle(snapshot) or snapshot['epics']:
            self._idle_since = None
            return False
        pending = False
        for key, entry in self.entries.items():
            row = snapshot['sequences'].get(key)
            if row is not None and not row['garbage']:
                if (row['identity'] != entry['identity'] or row.get('player_identity') != entry['player_identity']
                        or row.get('asset_path') != FINISHER or not row.get('player_outer_matches')
                        or not row.get('player_asset_matches') or not row.get('locks_clear')
                        or type(row.get('status')) is not int or row['status'] != 0):
                    raise RuntimeError('Attributed sequence is not the exact stopped unlocked pair; preserve it')
                if not entry['destroy_attempted']:
                    planner = self._scope.invocation_planner(catalog=snapshot['catalog'], selected_results=True)
                    try:
                        call = planner.prepare(row['actor'], snapshot['destroy'])
                        entry['destroy_attempted'] = True
                        self.uncertain = True
                        result = call.invoke()
                        if result.outcome != 'dispatch_returned':
                            raise RuntimeError('Sequence destruction outcome unknown; never replay')
                        entry['destroy_acknowledged'] = True  # Before result release or later reads.
                        # The call acknowledgement survives a result-release
                        # failure, but that failure must still quarantine holds.
                        if result.release() is not True:
                            raise RuntimeError('Sequence destruction result release deferred; preserve state')
                        self.uncertain = False
                    finally:
                        planner.close()
                pending = True  # Require a later complete inventory for retirement.
                continue
            entry['retired'] = True
            for lease in entry['leases']:
                if getattr(lease, '_state', None) == 'released':
                    continue
                if lease.release_pending:
                    pending = True
                    continue  # Session owns a queued release; do not replay it.
                self.uncertain = True
                released = lease.release()
                self.uncertain = False
                if released is not True:
                    pending = True
        if pending:
            return False
        self.closed = True
        return True

    def status(self):
        return dict(baseline_count=len(self.baseline_keys or ()), attributed_count=len(self.entries),
            baseline=list(self.baseline_records),
            diagnostics=list(self.diagnostics), uncertain=self.uncertain, closed=self.closed,
            entries=[{k: v for k, v in row.items() if k != 'leases'} for row in self.entries.values()])
