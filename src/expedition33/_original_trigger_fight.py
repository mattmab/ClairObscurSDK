"""Exact original direct fights through the existing owned trigger/arena route.

This is a direct battle action. It does not spawn an exploration character or
invoke the outer campaign action chain. Original combat phases and finisher
remain game-owned; only the copied battle parameters receive isolated policy.
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import threading
import time
from ._menu_latency import MenuLatency, measure_method

_PROFILE = Path(__file__).with_name('_original_trigger_recipes.json')
_PROFILE_SHA = '17e400e08d3e18f6046b9320d5413fbc7557750a328b3e78095951d9d2230c3b'
_GEOMETRY = ('AttachParent', 'AttachSocketName', 'RelativeLocation', 'RelativeRotation', 'RelativeScale3D')
_ENTRY = '/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:StartBattleNEW'
_CAPABILITIES = dict(enemy_spawn_protocol=3, enemy_retirement_protocol=1,
    enemy_grounded_spawn_protocol=2, enemy_visual_staging_research_protocol=1,
    enemy_trigger_anchor_research_protocol=1, enemy_trigger_parameter_research_protocol=1,
    enemy_trigger_entry_research_protocol=1, enemy_arena_binding_protocol=1, enemy_arena_protocol=1,
    owned_battle_arena_staging_protocol=1, owned_component_pose_protocol=1,
    owned_battle_arena_grounding_protocol=1, owned_battle_arena_approach_protocol=1,
    owned_battle_arena_approach_diagnostics_protocol=1, battle_parameter_frame_research_protocol=1,
    battle_parameter_policy_research_protocol=1, battle_entry_preflight_research_protocol=1,
    battle_entry_arena_research_protocol=2, battle_entry_dispatch_research_protocol=1,
    asset_load_protocol=1, picto_class_load_protocol=1, blueprint_invocation_protocol=1,
    lease_protocol=1, retained_protocol=1, stable_identity_protocol=1)


def _private_battle_id(params):
    # The general reader deliberately leaves soft references and other unrelated
    # members unsupported. Ownership needs only this exact decoded name field.
    names = [(k, v) for k, v in params.fields.items() if k.startswith('EnemyGlobalID_')]
    if (params.truncated or len(names) != 1 or
            any(k.startswith('EnemyGlobalID_') for k in params.errors) or
            type(names[0][1]) is not str or not names[0][1] or '\0' in names[0][1]):
        raise RuntimeError('Complete current battle identity required')
    return names[0][1]


def _identity(obj):
    return obj.index, obj.serial, obj.address


def _pose(location, rotation, scale, *, limit=100000.):
    xyz = tuple(location[k] for k in 'XYZ')
    pitch, yaw, roll = (rotation[k] for k in ('Pitch', 'Yaw', 'Roll'))
    sizes = tuple(scale[k] for k in 'XYZ')
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (*xyz, pitch, yaw, roll, *sizes)) or
            any(abs(v) > limit for v in xyz) or any(abs(v - 1.) > 1e-6 for v in sizes)):
        raise ValueError('Finite, unit-scale original component frame required')
    # Unreal: qZ(yaw) * qY(-pitch) * qX(-roll), retaining all three axes.
    def mul(a, b):
        x, y, z, w = a; u, v, t, s = b
        return (w*u+x*s+y*t-z*v, w*v-x*t+y*s+z*u, w*t+x*v-y*u+z*s, w*s-x*u-y*v-z*t)
    p, y, r = (math.radians(v)/2 for v in (pitch, yaw, roll))
    q = mul(mul((0., 0., math.sin(y), math.cos(y)), (0., -math.sin(p), 0., math.cos(p))),
            (-math.sin(r), 0., 0., math.cos(r)))
    return (*q, *xyz, 0., 1., 1., 1., 0.)


def _stored_pose(values, *, limit=100000.):
    def complete(name):
        value = values[name]
        if value.errors or value.truncated:
            raise RuntimeError('Incomplete original component frame: ' + name)
        return value.fields
    return _pose(complete('RelativeLocation'), complete('RelativeRotation'), complete('RelativeScale3D'), limit=limit)


def _same_pose(a, b):
    return (abs(abs(sum(x*y for x, y in zip(a[:4], b[:4]))) - 1.) < 1e-6 and
            all(abs(a[i]-b[i]) < .001 for i in range(4, 7)))


def _recipes(catalog):
    from .original_encounter_roster import resolve_source
    raw = _PROFILE.read_bytes()
    if len(raw) > 384*1024 or hashlib.sha256(raw).hexdigest() != _PROFILE_SHA:
        raise ValueError('Original trigger recipe package differs from its qualified source profile')
    data = json.loads(raw)
    if type(data.get('schema')) is not int or data['schema'] != 1 or len(data.get('recipes', ())) != 12:
        raise ValueError('Unsupported original trigger recipe package')
    allowed = {'duelliste-main': 'f019ec6032602e07', 'mirror-monolith': 'e02190410f616184', 'duolliste-pair': 'd6ec611a700522e6', 'chalier-tutorial': '2ce5e0adacadbef7', 'sciel-tutorial': 'd7da3e9d4941e833', 'osquio': 'd4e224bbeb87e684', 'monoco': 'eb4bb3b3f2a33358', 'scavenger': '84bdfeafeecedf47', 'paintress-intro': '8dcca6e9359e0054', 'simon-normal': 'e7e263f066d33733', 'simon-phase2': 'ab11b529310fbd73', 'paintress-main': '9dbac56b68f4cd24'}
    if {row.get('id'): row.get('recipe_id') for row in data['recipes']} != allowed:
        raise ValueError('Only the exact configured controlled original direct-fight profiles are admitted')
    result = []
    for row in data['recipes']:
        route = resolve_source(catalog, row['recipe_id'])
        if (row['battle_source'] != route['source'] or row['battle_class'] != route['class_path'] or
                row['encounter'] != route['encounter'] or row['full_initial_roster'] != route['full_initial_roster'] or
                len(row['full_initial_roster']) != (2 if row['id'] == 'duolliste-pair' else 1)):
            raise ValueError('Original trigger source and complete initial roster differ')
        arena = row['arena']; frames = arena['frames']; children = arena['children']
        if len(frames) != 20 or len(children) != 14 or len([x for x in children.values() if 'slot_index' in x]) != 7:
            raise ValueError('Complete original arena profile required')
        for name, frame in frames.items():
            # The unattached source root stores its original map coordinates;
            # construction replaces that root with the bounded staging pose.
            _pose(frame['location'], frame['rotation'], frame['scale'],
                  limit=1e7 if name=='DefaultSceneRoot' else 100000.)
            if name == 'DefaultSceneRoot':
                if frame['parent_field'] is not None: raise ValueError('Original root must be unattached')
            elif frame['parent_field'] not in frames:
                raise ValueError('Original frame parent is missing')
        placement = dict(forward_approach=row['id'] in ('duelliste-main', 'mirror-monolith'),
                         diagnostics=row['id'] in ('duelliste-main', 'mirror-monolith'), require_clear_approach=True)
        if any(name not in frames for name in children) or row['placement'] != placement:
            raise ValueError('Required original placement policy differs')
        result.append(deepcopy(row))
    return result


def direct_fight_recipes(catalog):
    """Exact direct-fight choices, separately keyed by the battle catalog ID."""
    return {row['recipe_id']: dict(id=row['id'], recipe=row['recipe_id'], recipe_id=row['recipe_id'], label=row['label'],
        menu_available=row['admission']['menu_available'], battle_class=row['battle_class'],
        restrictions=['Direct original fight; no exploration character or proximity entry.',
                      'Authored level, health and difficulty only.',
                      'Current environment; outer campaign intro and reward action chain omitted.',
                      row['admission']['sequence_inventory_limitation']]+(
                      ['Original tutorial callbacks may change party/completion state and autosave.']
                      if row.get('route_contract',{}).get('tutorial_callbacks_retained') else [])) for row in _recipes(catalog)}


_CONSTRUCTION_NAMES=('Default__GameplayStatics','UpdateTriggerComponentsCollision',
    'BeginDeferredActorSpawnFromClass','FinishSpawningActor','K2_DestroyActor','K2_GetPawn',
    'SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame')


def _construction_metadata(scope,transport,context,spawner):
    """Reuse only stabilized static selection, with fresh identity reads.

    Caller owns the same-process read batch. This never caches arena/pawn poses,
    source admission, property values or native dispatch permission.
    """
    from .catalog import capture_matching,capture_selected
    key=(tuple(context['controller']),tuple(context['world']))
    cached=getattr(spawner,'_original_construction_metadata',None)
    if cached is not None and cached['transport'] is transport and cached['context']==key:
        return capture_selected(scope.pid,cached['identities'])
    catalog=capture_matching(scope.pid,names=_CONSTRUCTION_NAMES)
    selected=tuple(obj for obj in catalog.objects if
        (obj.class_name=='Function' and obj.name in _CONSTRUCTION_NAMES) or obj.name=='Default__GameplayStatics')
    if selected and len(selected)<=64 and all(obj.serial>0 for obj in selected):
        spawner._original_construction_metadata=dict(transport=transport,context=key,
            identities=tuple(_identity(obj) for obj in selected))
    else:
        spawner._original_construction_metadata=None
    return catalog


class OriginalTriggerFight:
    """Persistent one-shot composition on the spawner's existing scope/owner.

    Save this object before calling start(). start() also anchors itself on the
    spawner before the first load. Failed preparation stays available to close;
    unknown entry never retries and idle polling never treats a retry gap as a
    completed fight. close() returns False for acknowledged cleanup deferral.
    """
    def __init__(self, spawner, recipe_id='duelliste-main', *, tuning=None):
        from .encounter_tuning import settings
        config = settings(tuning)
        if not config.is_default:
            raise ValueError('Original direct fights currently require authored tuning defaults')
        spawner._scope._check()
        rows = [row for row in _recipes(spawner.catalog) if row['id'] == recipe_id]
        if len(rows) != 1 or rows[0]['admission']['menu_available'] is not True:
            raise ValueError('Original direct-fight recipe is unavailable')
        self.recipe = rows[0]
        self._spawner = spawner; self._scope = spawner._scope
        self._transport = self._scope._session._transport; self._owner = spawner._owner
        self._thread = threading.get_ident()
        self._arena = None; self._parameters = None; self._sequences = None
        self._sequence_ready = False; self._sequence_diagnostic = None
        self._was_active = False
        self._holds = []; self._load_pending = None; self._release_unknown = False
        self._context = None; self._source_root = None; self._trigger_class = None
        self._anchor_attempted = False; self._anchor_removed = False
        self._started = False; self.dispatch_attempted = False; self.entry_acknowledged = False
        self.battle_observed = False; self._private_id = None; self._next_poll = 0.
        self.phase = 'new'; self.error = None; self._battle = None; self._assembly = {}
        self._cleanup_step = None; self.tuning = config.to_dict()
        self._world_replaced = False; self.observation_error = None
        self._source_orientation = False
        self.latency = MenuLatency()

    def _thread_check(self):
        if threading.get_ident() != self._thread:
            raise RuntimeError('Original fight requires its owning Python thread')

    def _batch(self):
        from ._reader import ReadBatch
        return ReadBatch(self._scope.pid, share=True, _executable=self._transport._executable)

    def _current_context(self):
        from .cinematics.original_game_action import controller_context
        # Keep fresh LocalPlayer selection on this candidate's read worker.
        # Outside a batch, the imported utility uses the installed probe.
        with self._batch():
            return controller_context(self._scope._session)

    def _preflight(self):
        self._scope._check()
        if self._spawner._closed or self._owner._scope is not self._scope or self._owner._transport is not self._transport:
            raise RuntimeError('Same-scope reusable enemy owner required')
        if not callable(getattr(self._scope, '_register_native_owner', None)):
            raise RuntimeError('Scoped native cleanup registration required')
        if (self._owner.has_native_work or self._owner.phase != 'ready' or self._owner._closed or
                getattr(self._spawner, '_tuning', None) is not None):
            raise RuntimeError('Retire the current enemy before starting an original fight')
        if getattr(self._transport, '_enemy_spawn_owner', self._owner) is not self._owner:
            raise RuntimeError('Reusable primary owner is no longer current')
        existing = getattr(self._spawner, 'original_fight', None)
        if existing not in (None, self) and existing.phase != 'closed':
            raise RuntimeError('Retire the existing original fight first')
        helper = getattr(self._spawner, 'helper_encounter', None)
        if helper is not None and helper.phase != 'closed': raise RuntimeError('Retire the original helper first')
        for name in ('_owned_battle_arena_owner', '_parameter_research_owner', '_native_visual_stage_owner',
                     '_npc_staging_owner', '_paintress_helper_qa', '_paintress_phase_qa'):
            if getattr(self._transport, name, None) is not None:
                raise RuntimeError('Existing scoped encounter resource must be retired: ' + name)
        for name, expected in _CAPABILITIES.items():
            value = getattr(self._transport, name, 0)
            if type(value) is not int or value != expected:
                raise RuntimeError('Original direct fight capability unavailable: ' + name)

    def _battle_snapshot(self):
        from .catalog import capture_selected
        from .enemy_spawning import _fields
        from ._npc_encounter_preparation import _controller_battle_manager
        from .cinematics.original_game_action import controller_context
        context = self._current_context()
        if context != self._context: raise RuntimeError('Original fight world/controller changed; preserve owners')
        with self._batch():
            c = capture_selected(self._scope.pid, (tuple(context['controller'][1:]),))
            manager, c = _controller_battle_manager(c, c.by_index[context['controller'][1]])
            values, c = _fields(c, manager, ('IsBattleInitialized', 'HasBattleStartedEndFlow',
                                            'CurrentBattleStartParams', 'Enemies', 'PlayerCharacters', 'BattleMapBP'))
            enemies = values['Enemies']; params = values['CurrentBattleStartParams']
            players = values['PlayerCharacters']
            if (enemies.length != len(enemies.items) or players.length != len(players.items) or
                    any(obj is None for obj in players.items)):
                raise RuntimeError('Complete current battle ownership observation required')
            private_id = _private_battle_id(params)
            arena = values['BattleMapBP']; roster = []
            for enemy in enemies.items:
                if enemy is None: raise RuntimeError('Incomplete current enemy roster')
                slot, c = _fields(c, enemy, ('BattleSpotIndex',))
                roster.append(dict(identity=_identity(enemy), class_path=c.path_name(c.by_index[enemy.class_index]),
                                   slot=slot['BattleSpotIndex']))
        if self._current_context() != context:
            raise RuntimeError('Original fight context changed during observation')
        return dict(context=context, manager=_identity(manager), started=values['IsBattleInitialized'], ending=values['HasBattleStartedEndFlow'],
                    private_id=private_id, arena=_identity(arena) if arena else None, roster=roster,
                    characters=[_identity(obj) for obj in (*enemies.items, *players.items)])

    @measure_method('prepare.idle_recheck')
    def _idle(self):
        state = self._battle_snapshot()
        if state['started'] is not False or state['ending'] is not False or state['roster'] or state['arena'] is not None:
            raise RuntimeError('Preserve active battle or transition')
        return state

    @measure_method('prepare.asset_retention')
    def _retain(self, path, *, is_class=False):
        from .assets import load_asset
        from .picto_class_load import load_class
        if self._load_pending is not None: raise RuntimeError('Asset outcome unknown; no replay')
        self._load_pending = path
        result = (load_class if is_class else load_asset)(self._scope, path)
        hold = dict(path=path, handle=result, release_attempted=False, released=False)
        self._holds.append(hold)  # Keep the full invocation before reading its output.
        obj = result.return_value
        self._load_pending = None
        if obj is None: raise RuntimeError('Exact original asset did not load: ' + path)
        return obj

    @measure_method('prepare.construction_inputs')
    def _construction_inputs(self, cls, *, trigger):
        from .catalog import capture_selected
        from .enemy_spawning import _fields, _exact
        names = ('GameplayStatics:BeginDeferredActorSpawnFromClass', 'GameplayStatics:FinishSpawningActor',
                 'Actor:K2_DestroyActor', 'Controller:K2_GetPawn', 'Actor:SetActorEnableCollision',
                 'Actor:SetActorTickEnabled', 'Actor:SetActorHiddenInGame')
        with self._batch():
            c = _construction_metadata(self._scope,self._transport,self._context,self._spawner)
            c = c.with_observations(capture_selected(self._scope.pid, (tuple(self._context['controller'][1:]),
                                     tuple(self._context['world'][1:]), _identity(cls))))
            live = c.by_index[cls.index]
            expected = self.recipe['trigger_class'] if trigger else self.recipe['arena']['class_path']
            if _identity(live) != _identity(cls) or c.path_name(live) != expected:
                raise RuntimeError('Retained original construction class differs')
            pc = c.by_index[self._context['controller'][1]]; values, c = _fields(c, pc, ('Pawn',))
            pawn = values['Pawn']
            if pawn is None: raise RuntimeError('Exploration pawn required')
            values, c = _fields(c, pawn, ('RootComponent',)); values, c = _fields(c, values['RootComponent'], _GEOMETRY)
            if values['AttachParent'] is not None: raise RuntimeError('Unattached exploration pawn required')
            pose = _stored_pose(values, limit=1e7)
            if self._source_orientation and not trigger:
                frame = self.recipe['arena']['frames']['DefaultSceneRoot']
                authored = _pose(frame['location'], frame['rotation'], frame['scale'], limit=1e7)
                pose = (*authored[:4], *pose[4:])
            pose = (*pose[:6], pose[6]+50000., *pose[7:])
            if any(abs(value) > 1e7 for value in pose[4:7]):
                raise RuntimeError('Hidden original staging pose exceeds the existing world bound')
            ids = [pc, pawn, c.by_index[self._context['world'][1]], _exact(c, '/Script/Engine.Default__GameplayStatics'), live]
            ids.extend(_exact(c, '/Script/Engine.'+name) for name in names)
            ids.append(_exact(c, expected+':UpdateTriggerComponentsCollision') if trigger else _exact(c, '/Script/Engine.Actor:K2_DestroyActor'))
        self._idle()
        return tuple(ids), pose

    @measure_method('prepare.arena_frame_validation')
    def _arena_frames(self, staging, *, allow_corrections):
        from .catalog import capture_matching, capture_selected
        from .enemy_spawning import _fields, _exact
        profile = self.recipe['arena']; frames = profile['frames']; children = profile['children']
        with self._batch():
            c = capture_selected(self._scope.pid, (tuple(self._arena.actor_identity),))
            c = c.with_observations(capture_matching(self._scope.pid, names=('K2_SetRelativeTransform', 'GetRelativeTransform')))
            actor = c.by_index[self._arena.actor_identity[0]]
            if _identity(actor) != tuple(self._arena.actor_identity) or c.path_name(c.by_index[actor.class_index]) != profile['class_path']:
                raise RuntimeError('Exact owned original arena changed')
            values, c = _fields(c, actor, tuple(dict.fromkeys(('RootComponent', *frames, *children))))
            setter = _exact(c, '/Script/Engine.SceneComponent:K2_SetRelativeTransform')
            getter = _exact(c, '/Script/Engine.SceneComponent:GetRelativeTransform')
            fixes = []; seen_components = set(); seen_children = set(); observed_children = []
            for name, row in frames.items():
                comp = values[name]
                if (comp is None or comp.outer_index != actor.index or comp.outer_serial != actor.serial or
                        c.path_name(c.by_index[comp.class_index]) != row['class_path'] or _identity(comp) in seen_components):
                    raise RuntimeError('Original component ownership/class differs: ' + name)
                seen_components.add(_identity(comp)); actual, c = _fields(c, comp, _GEOMETRY)
                if row['parent_field'] is None:
                    if actual['AttachParent'] is not None or _identity(values['RootComponent']) != _identity(comp):
                        raise RuntimeError('Owned arena root differs')
                    want = staging
                else:
                    parent = actual['AttachParent']; expected_parent = values[row['parent_field']]
                    if parent is None or _identity(parent) != _identity(expected_parent):
                        raise RuntimeError('Exact original component attachment differs: ' + name)
                    want = _pose(row['location'], row['rotation'], row['scale'])
                if str(actual['AttachSocketName']) != row['socket']:
                    raise RuntimeError('Original attachment socket differs: ' + name)
                if not _same_pose(_stored_pose(actual, limit=1e7), want):
                    if row['parent_field'] is None or not allow_corrections:
                        raise RuntimeError('Original arena frame verification failed: ' + name)
                    fixes.append((name, comp, want))
                if name in children:
                    expected = children[name]; refs, c = _fields(c, comp, ('ChildActor', 'ChildActorClass', 'ChildActorTemplate'))
                    child, child_class, template = (refs[k] for k in ('ChildActor', 'ChildActorClass', 'ChildActorTemplate'))
                    if (child is None or child_class is None or template is None or child.class_index != child_class.index or
                            c.path_name(child_class) != expected['class_path'] or c.path_name(template) != expected['template_path'] or
                            _identity(child) in seen_children):
                        raise RuntimeError('Original child/template differs: ' + name)
                    seen_children.add(_identity(child))
                    if 'slot_index' in expected:
                        slot, c = _fields(c, child, ('SlotIndex',))
                        if type(slot['SlotIndex']) is not int or slot['SlotIndex'] != expected['slot_index']:
                            raise RuntimeError('Original slot index differs: ' + name)
                    observed_children.append(dict(field=name, identity=_identity(child)))
        if len(seen_components) != 20 or len(seen_children) != 14:
            raise RuntimeError('Complete owned original assembly required')
        self._assembly.update(frames_observed=20, children=observed_children, frames_verified=not fixes)
        for name, comp, pose in fixes:
            self._idle()
            self._assembly.setdefault('corrections', {})[name] = dict(attempted=True)
            self._assembly['corrections'][name] = self._arena.set_component_pose_once(comp, setter, getter, pose)
        return fixes

    @measure_method('prepare.entry_dependencies')
    def _entry_inputs(self):
        from .catalog import capture_matching, capture_selected
        from .enemy_spawning import _fields, _exact
        from ._npc_encounter_preparation import _controller_battle_manager
        from .original_trigger_sources import _owned_source, BATTLE_STRUCT
        from .original_encounter_roster import _verify_source
        from .values import StoredMap, StoredMapEntries
        with self._batch():
            c = capture_matching(self._scope.pid, names=('FBattleStartParams', 'StartBattleNEW'), classes=('BP_GameAction_TriggerBattle_C',))
            c = c.with_observations(capture_selected(self._scope.pid, (_identity(self._source_root),
                tuple(self._owner.actor_identity), tuple(self._context['controller'][1:]), tuple(self._context['world'][1:]))))
            root = c.by_index[self._source_root.index]
            if _identity(root) != _identity(self._source_root) or c.path_name(root) != self.recipe['battle_source'].split(':')[0]:
                raise RuntimeError('Retained original action root differs')
            source = _owned_source(c, root, self.recipe['battle_source'])
            anchor = c.by_index[self._owner.actor_identity[0]]
            if _identity(anchor) != tuple(self._owner.actor_identity): raise RuntimeError('Held trigger identity differs')
            v, c = _fields(c, anchor, ('bHidden', 'bActorEnableCollision', 'BP_Interaction_SerializableComponent'))
            component = v['BP_Interaction_SerializableComponent']
            if (v['bHidden'] is not True or v['bActorEnableCollision'] is not False or component is None or
                    component.outer_index != anchor.index or component.outer_serial != anchor.serial):
                raise RuntimeError('Exact hidden, collisionless private trigger required')
            v, c = _fields(c, component, ('GlobalObjectID', 'IsTransient'))
            private = str(v['GlobalObjectID'])
            if v['IsTransient'] is not False or private in ('None', '', '0') or private != anchor.name:
                raise RuntimeError('Private trigger identity differs')
            v, c = _fields(c, c.by_index[self._context['world'][1]], ('OwningGameInstance',))
            v, c = _fields(c, v['OwningGameInstance'], ('InteractedObjects', 'TransientInteractedObjects'))
            if set(v) != {'InteractedObjects', 'TransientInteractedObjects'}: raise RuntimeError('Both complete history maps required')
            for value in v.values():
                if not isinstance(value, (StoredMap, StoredMapEntries)): raise RuntimeError('Incomplete history map')
                entries = value.items.items() if isinstance(value, StoredMap) else value.entries
                if any(str(key) == private for key, _ in entries):
                    raise RuntimeError('Private trigger key already exists; never clear or reuse it')
            manager, c = _controller_battle_manager(c, c.by_index[self._context['controller'][1]])
            identities = (_exact(c, BATTLE_STRUCT), source, root, anchor, manager, _exact(c, _ENTRY))
        _verify_source(self._scope, source, self.recipe['encounter'])
        current = self._idle()
        if current['manager'] != _identity(manager): raise RuntimeError('Current battle manager changed before entry')
        self._private_id = private
        return identities

    @measure_method('battle.prepare_total')
    def prepare(self, *, align_source_orientation=False):
        """Stage the owned arena and collisionless trigger without entering combat.

        A presentation adapter may play an owned introduction before calling
        dispatch_prepared. All entry dependencies are read again after that
        presentation; preparation never authorizes a later stale dispatch.
        """
        from .owned_battle_arena import OwnedBattleArena
        from ._npc_encounter_preparation import bind_original_arena
        self._thread_check()
        if type(align_source_orientation) is not bool:
            raise ValueError('Source orientation selection must be explicit')
        if self._started or self.phase != 'new': raise RuntimeError('Original fight start is one-shot; close before replacement')
        self._preflight()
        self._source_orientation = align_source_orientation
        self._spawner.original_fight = self  # Persistent before the first load/mutation.
        self._started = True; self.phase = 'preparing'
        try:
            # Even an unknown first asset load must participate in the existing
            # revoked-scope ownership-abort path before any leases are released.
            self._scope._register_native_owner(self)
            self._context = self._current_context(); self._idle()
            self._source_root = self._retain(self.recipe['battle_source'].split(':')[0])
            arena_class = self._retain(self.recipe['arena']['class_path'], is_class=True)
            self._trigger_class = self._retain(self.recipe['trigger_class'], is_class=True)
            self._idle()
            self._arena = OwnedBattleArena(self._scope)
            ids, staging = self._construction_inputs(arena_class, trigger=False)
            with self.latency.measure('prepare.arena_native_construction'):
                self._arena.prepare(ids, staging)
            self._arena_frames(staging, allow_corrections=True)
            self._arena_frames(staging, allow_corrections=False)  # Full reread before grounding.
            self._idle()
            with self.latency.measure('prepare.arena_grounding_clearance'):
                self._arena.ground_once(**self.recipe['placement'])
            with self.latency.measure('prepare.arena_camera_focus'):
                self._arena.refresh_camera_focus_once()
            ids, staging = self._construction_inputs(self._trigger_class, trigger=True)
            self._anchor_attempted = True
            with self.latency.measure('prepare.trigger_native_construction'):
                self._owner.spawn_trigger_prepared(ids, staging)
            with self.latency.measure('prepare.arena_binding'):
                bind_original_arena(self._scope, self._owner, self._arena.actor_identity,
                                    expected_class=self.recipe['arena']['class_path'])
            # Optional observation does not change admission or adopt old residuals.
            try:
                from ._original_trigger_sequences import OriginalFightSequenceCleanup
                self._sequences = OriginalFightSequenceCleanup(self._scope, source=self.recipe['battle_source'])
                self._sequences.baseline(); self._sequence_ready = True
            except Exception as error:
                self._sequence_diagnostic = 'Sequence inventory unavailable: ' + str(error)
            self._entry_inputs()
            self.phase = 'prepared'
            return self.status()
        except BaseException as error:
            self.error = f'{type(error).__name__}: {error}'
            self.phase = 'unknown' if self._load_pending else 'preparation_failed'
            raise

    @measure_method('battle.dispatch_total')
    def dispatch_prepared(self, *, track_completion=False):
        """Enter once after a fresh recheck of the held arena and source."""
        from ._battle_parameter_owner import ParameterResearchOwner
        self._thread_check()
        self._scope._check()
        if type(track_completion) is not bool:
            raise ValueError('Completion tracking must be explicit')
        if self.phase != 'prepared' or self.dispatch_attempted:
            raise RuntimeError('Only a prepared original fight may enter once')
        capability = getattr(self._transport, 'battle_completion_receipt_protocol', 0)
        if track_completion and (type(capability) is not int or capability != 1):
            raise RuntimeError('Authoritative battle completion capability unavailable')
        try:
            identities = self._entry_inputs()
            self._parameters = ParameterResearchOwner(self._scope)
            if self._sequence_ready:
                self._sequences.entry_attempted(private_id=self._private_id, arena_identity=self._arena.actor_identity)
            self.dispatch_attempted = True; self.phase = 'entry_pending'
            options = {'track_completion': True} if track_completion else {}
            self._parameters.dispatch_trigger_cleanup(identities, anchor=self._owner, arena=self._arena,
                mode=2 if self.recipe['id']=='sciel-tutorial' else 1, **options)
            self.entry_acknowledged = True
            return self.status()
        except BaseException as error:
            self.error = f'{type(error).__name__}: {error}'
            self.phase = 'unknown' if self.dispatch_attempted or self._load_pending else 'preparation_failed'
            raise

    def start(self):
        self.prepare()
        return self.dispatch_prepared()

    def poll(self):
        from . import RuntimeQueryError
        self._thread_check()
        if self.phase == 'closed' or not self.dispatch_attempted: return self.status()
        if self.phase == 'unknown' and not self.entry_acknowledged: return self.status()
        if time.monotonic() < self._next_poll: return self.status()
        self._next_poll = time.monotonic()+.5
        try:
            if self.phase == 'cleanup_pending':
                self.close(); return self.status()
            if self.entry_acknowledged and self._current_context() != self._context:
                self._world_replaced = True
                self.close(); return self.status()
            self._scope._check(); state = self._battle_snapshot(); self._battle = state
            self.observation_error = None
            if state['started'] is True:
                expected = [(r['class_path'], r['slot']) for r in self.recipe['full_initial_roster']]
                actual = [(r['class_path'], r['slot']) for r in state['roster']]
                if state['private_id'] != self._private_id or state['arena'] != tuple(self._arena.actor_identity):
                    raise RuntimeError('Current original battle ownership differs; preserve owners')
                if not self.battle_observed and actual != expected:
                    if actual and state['ending'] is not True:
                        raise RuntimeError('Initial original battle roster differs; preserve owners')
                else:
                    self.battle_observed = True; self._was_active = True
                    self.phase = 'active'; self.error = None
                    if self._sequence_ready and hasattr(self._sequences, 'observe_active'):
                        try: self._sequences.observe_active(state)
                        except Exception as error: self._sequence_diagnostic = str(error)
            elif state['ending'] is False and not state['roster'] and state['arena'] is None:
                self.phase = 'idle_retained'; self.error = None
                if self._sequence_ready and self._was_active:
                    self._was_active = False  # One global inventory per active->idle edge.
                    try: self._sequences.observe()
                    except Exception as error: self._sequence_diagnostic = str(error)
            elif self.phase != 'cleanup_pending': self.phase = 'entry_pending'
        except RuntimeQueryError as error:
            # This is a failed read, not an uncertain battle invocation. Retry
            # only a fresh observation; never repeat loads, entry or mutation.
            self.observation_error = f'{type(error).__name__}: {error}'
            if self.phase != 'cleanup_pending': self.phase = 'observation_pending'
        except BaseException as error:
            self.error = f'{type(error).__name__}: {error}'; self.phase = 'unknown'; raise
        return self.status()

    def close(self):
        from ._enemy_spawn_wire import EnemyCleanupDeferred
        self._thread_check()
        if self.phase == 'closed': return True
        # No scope._check here: the native owners retain their revoked-scope
        # fallback. No observation/load/mutation planner is introduced on close.
        if self._load_pending or self._release_unknown:
            self.phase = 'unknown'; return False
        self.phase = 'cleanup_pending'
        try:
            self._cleanup_step = 'parameters'
            if self._parameters is not None and not self._parameters.close(): return False
            self._cleanup_step = 'sequences'
            if self._sequences is not None:
                closed = self._sequences.close_after_world_change() if self._world_replaced else self._sequences.close()
                if not closed: return False
            self._cleanup_step = 'trigger'
            if self._anchor_attempted and not self._anchor_removed:
                self._owner.remove(); self._anchor_removed = True
            self._cleanup_step = 'arena'
            if self._arena is not None and not self._arena.close(): return False
            self._cleanup_step = 'source_holds'
            for hold in reversed(self._holds):
                if hold['released']: continue
                handle = hold['handle']
                if hold['release_attempted']:
                    states = [getattr(lease, '_state', None) for lease in handle._leases]
                    if all(state == 'released' for state in states): hold['released'] = True; continue
                    if any(state in ('unknown', 'invalid', 'target_exited') for state in states): self._release_unknown = True
                    return False  # Session owns pending releases; never replay.
                hold['release_attempted'] = True; self._release_unknown = True
                acknowledged = handle.release()
                self._release_unknown = False
                if acknowledged is not True: return False
                hold['released'] = True
            self.phase = 'closed'; self._cleanup_step = None; self.error = None
            return True
        except EnemyCleanupDeferred:
            return False
        except BaseException as error:
            self.error = f'{type(error).__name__}: {error}'; self.phase = 'unknown'; raise

    def status(self):
        return dict(timings=self.latency.snapshot() if hasattr(self,'latency') else None, recipe=self.recipe['id'], catalog_recipe=self.recipe['recipe_id'], phase=self.phase, error=self.error,
            world_replaced=self._world_replaced, observation_error=self.observation_error,
            direct_fight=True, proximity_entry=False, exploration_character_spawned=False,
            dispatch_attempted=self.dispatch_attempted, entry_acknowledged=self.entry_acknowledged,
            battle_observed=self.battle_observed, battle_completed=False, battle=deepcopy(self._battle),
            anchor_identity=self._owner.actor_identity if self._anchor_attempted and not self._anchor_removed else None,
            arena_identity=self._arena.actor_identity if self._arena and self.phase != 'closed' else None,
            grounding=deepcopy(getattr(self._arena, 'grounding', None)), assembly=deepcopy(self._assembly),
            load_pending=self._load_pending, cleanup_step=self._cleanup_step, tuning=deepcopy(self.tuning),
            sequence_inventory=self._sequences.status() if self._sequences else None,
            sequence_inventory_diagnostic=self._sequence_diagnostic,
            sequence_inventory_limitation=self.recipe['admission']['sequence_inventory_limitation'])
