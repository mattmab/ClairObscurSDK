"""Original-world enemy spawning through SDK-owned native transactions.

QA is the runtime-verified world. Negotiated current-world staging is experimental
and requires grounded preparation plus an observed arena. Discovery-only/battle-only
records remain unavailable. Isolated
policy suppresses the owned instance's post-battle action; it is not a blanket
claim that all authored encounters are campaign-neutral.
"""
import json
import math
import struct
import re
import time
from pathlib import Path
from ._enemy_spawn_owner import EnemySpawnOwner
from .catalog import capture_matching,capture_selected
from .values import read_values_with_references
from ._reader import ReadBatch
from .picto_class_load import load_class
from .cinematics.original_game_action import controller_context

QA_WORLD='/Game/QA/Map_BattleTesting.Map_BattleTesting'
POLICIES=('isolated','original_campaign_actions')
BASE='/Game/jRPGTemplate/Blueprints/Basics/BP_jRPG_Enemy_World_Base_Seamless.BP_jRPG_Enemy_World_Base_Seamless_C'


def load_catalog(path=None):
    """Load exact cached catalog data; this does not scan or load game assets."""
    path=Path(path) if path is not None else Path(__file__).with_name('_enemy_catalog.json')
    if path.stat().st_size>10*1024*1024:raise ValueError('Enemy catalog exceeds supported size')
    data=json.loads(path.read_text(encoding='utf8'))
    if type(data) is not dict or type(data.get('schema')) is not int or data.get('schema')!=1 or type(data.get('entries')) is not list:
        raise ValueError('Unsupported enemy catalog')
    if not 1<=len(data['entries'])<=4096:raise ValueError('Enemy catalog entry count is invalid')
    ids=set()
    for entry in data['entries']:
        if type(entry) is not dict:raise ValueError('Enemy catalog entries must be objects')
        key=entry.get('id');class_path=entry.get('class_path')
        if type(key) is not str or not key or key in ids:raise ValueError('Invalid or duplicate enemy recipe ID')
        if type(class_path) is not str or not re.fullmatch(r'/Game/(?:[A-Za-z0-9_]+/)*([A-Za-z0-9_]+)\.(?i:\1)_C',class_path):
            raise ValueError('Invalid enemy class path')
        if type(entry.get('spawn_available')) is not bool:raise ValueError('Enemy spawn availability must be explicit')
        ids.add(key)
    return data


def _exact(catalog,path):
    rows=[o for o in catalog.objects if catalog.path_name(o)==path]
    if len(rows)!=1:raise RuntimeError('Missing or ambiguous enemy prerequisite: '+path)
    return rows[0]


def _fields(catalog,obj,names):
    values,catalog=read_values_with_references(catalog,obj,fields=names)
    if values.errors:raise RuntimeError('Enemy prerequisite fields could not be read: '+str(values.errors))
    return {key[1]:value for key,value in values.values.items()},catalog


class EnemySpawner:
    """One mod-scoped enemy owner on the shared SDK session.

    spawn() preserves original construction and encounter selection. The game
    starts combat through its own overlap; this service never forces a battle.
    Call remove() before replacement. Unknown outcomes remain owned for cleanup.
    """
    def __init__(self,scope,*,catalog_path=None):
        scope._check()
        retirement=getattr(scope._session._transport,'enemy_retirement_protocol',0)
        if type(retirement) is not int or retirement!=1:
            raise RuntimeError('Native runtime lacks battle-aware enemy retirement; update the SDK runtime')
        if getattr(scope._session._transport,'enemy_pose_protocol',0)!=1:raise RuntimeError('Native runtime lacks the bounded enemy pawn-pose query')
        self.catalog=load_catalog(catalog_path)
        self._entries={row['id']:row for row in self.catalog['entries']}
        self._scope=scope;self._owner=EnemySpawnOwner(scope);self._classes={}
        self._closed=False;self._record={};self.helper_encounter=None;self._tuning=None
        self.original_fight=None

    def original_fight_catalog(self):
        """Read direct original-fight recipes; these do not imply world spawning."""
        from ._original_trigger_fight import direct_fight_recipes
        return direct_fight_recipes(self.catalog)

    def start_original_fight(self,recipe_id,*,tuning=None):
        """Start an admitted original fight with a persistently owned arena/trigger."""
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        current=getattr(self,'original_fight',None)
        if current is not None and current.phase!='closed':
            raise RuntimeError('Retire the existing original fight first')
        if self._owner.has_native_work or self._tuning is not None:
            raise RuntimeError('Retire the existing owned encounter first')
        if self.helper_encounter is not None and self.helper_encounter.phase!='closed':
            raise RuntimeError('Retire the existing helper encounter first')
        from ._original_trigger_fight import OriginalTriggerFight
        self.original_fight=OriginalTriggerFight(self,recipe_id,tuning=tuning)
        return self.original_fight.start()

    def poll_original_fight(self):
        current=getattr(self,'original_fight',None)
        return current.poll() if current is not None else None

    def _check_no_original_fight(self):
        current=getattr(self,'original_fight',None)
        if current is not None and current.phase!='closed':
            raise RuntimeError('Retire the original direct fight before another operation')

    def original_helper_catalog(self):
        """Read admitted original-helper routes separately from world recipes."""
        from .original_helper_encounters import catalog_recipes
        return catalog_recipes(self.catalog)

    def stage_original_helper(self,recipe_id='visages',*,tuning=None):
        """Stage an original split-boss assembly and its owned original arena.

        The SDK keeps both owners through authored battle phases. Approach the
        visible body to enter; poll_original_helper services it, including mounts.
        Failed or uncertain attempts stay owned until explicit retirement.
        """
        self._scope._check()
        self._check_no_original_fight()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if self.helper_encounter is not None and self.helper_encounter.phase!='closed':
            raise RuntimeError('Retire the existing helper encounter first')
        from .original_helper_encounters import OriginalHelperEncounter
        self.helper_encounter=OriginalHelperEncounter(self,recipe_id,tuning=tuning)
        return self.helper_encounter.stage()

    def poll_original_helper(self):
        if self.helper_encounter is None:return None
        return self.helper_encounter.poll()

    def inspect_arenas(self):
        """Read original current-world arena identities; readiness remains unverified."""
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        from ._enemy_arenas import observe_battle_arenas
        return observe_battle_arenas(self._scope._session)

    def prepare_authored_spawn(self,recipe_id,*,policy='isolated',arena_identity=None,
                               activate=True,experimental_battle_positions=None):
        """Validate the tested instance route before retiring an existing owner.

        Returns arguments for spawn(); never creates an actor or starts a battle.
        Arena observation is fresh; native spawn still checks identity/world.
        """
        from .enemy_authored_routes import prepare_route
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if recipe_id not in self._entries:raise ValueError('Unknown enemy recipe')
        capability=getattr(self._scope._session._transport,'enemy_authored_encounter_research_protocol',0)
        return prepare_route(self._entries[recipe_id],policy,arena_identity,self.inspect_arenas(),capability,
            activate=activate,experimental_battle_positions=experimental_battle_positions)

    def inspect_helper_link(self,battle_actor_identity):
        """Read a battle component's exact link to this owner's visual helper.

        This is diagnostic evidence only; it does not admit encounter entry,
        prove battle ownership, or change lifetime/retirement state.
        """
        from .enemy_helper_links import inspect_original_helper_link
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if not self._owner.has_native_work or self._owner.actor_identity is None:
            raise RuntimeError('Owned original helper required')
        return inspect_original_helper_link(self._scope,battle_actor_identity,self._owner.actor_identity)

    def authored_sources(self,recipe_id):
        """Return deterministic full-encounter source recipes without promotion."""
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        from .enemy_encounter_sources import authored_encounter_sources
        return authored_encounter_sources(self.catalog,recipe_id)

    def place_combatant(self,actor_identity,destination,*,experimental=False):
        """Move a later combatant and refresh its original combat home.

        Explicit experimental operation for this service's active encounter.
        The three initial slots and original arena spots are never edited.
        No navigation or ground-support guarantee follows from teleport success.
        A movement attempt is not replayed, including after an uncertain result.
        """
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if experimental is not True:raise ValueError('Combat placement requires explicit experimental=True')
        if (type(actor_identity) not in (tuple,list) or len(actor_identity)!=3 or
            any(type(v) is not int for v in actor_identity) or actor_identity[0]<0 or
            actor_identity[1]<0 or not 0x10000<=actor_identity[2]<=0x7fffffffffff):
            raise ValueError('Expected an observed combatant identity')
        if (type(destination) not in (tuple,list) or len(destination)!=3 or
            any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in destination)):
            raise ValueError('Expected three finite world destination coordinates')
        capability=getattr(self._scope._session._transport,'enemy_combat_placement_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Native runtime lacks combat placement')
        if self._owner.phase!='active' or self._owner.arena_identity is None:
            raise RuntimeError('Combat placement requires an active owned encounter')
        with ReadBatch(self._scope.pid):
            context=controller_context(self._scope._session)
            c=capture_matching(self._scope.pid,names=('K2_GetActorLocation','K2_GetActorRotation',
                'K2_TeleportTo','UpdateInitialTransform'),classes=('AC_jRPG_BattleManager_C',))
            c=c.with_observations(capture_selected(self._scope.pid,(tuple(actor_identity),)))
            actor=c.by_index[actor_identity[0]]
            managers=[o for o in c.objects if o.class_name=='AC_jRPG_BattleManager_C' and
                o.outer_index==context['controller'][1] and not o.object_flags&0x30]
            if len(managers)!=1:raise RuntimeError('Current combat manager is missing or ambiguous')
            manager=managers[0]
            values,c=_fields(c,manager,('Enemies','BattleMapBP'))
            arena=values['BattleMapBP']
            if arena is None or (arena.index,arena.serial,arena.address)!=self._owner.arena_identity:
                raise RuntimeError('Active arena differs from the owned encounter')
            roster=values['Enemies']
            values,c=_fields(c,actor,('AC_jRPG_CombatMovement','BattleSpotIndex'))
            slot=values['BattleSpotIndex'];movement=values['AC_jRPG_CombatMovement']
            if type(slot) is not int or not 3<=slot<=9 or roster.length!=len(roster.items) or slot>=roster.length:
                raise RuntimeError('Combat placement is limited to later slots 3..9')
            member=roster.items[slot]
            if member is None or (member.index,member.serial,member.address)!=tuple(actor_identity):
                raise RuntimeError('Combatant is not in the owned encounter roster')
            if movement is None:raise RuntimeError('Original combat movement component missing')
            prerequisites=(manager,actor,movement,
                _exact(c,'/Script/Engine.Actor:K2_GetActorLocation'),
                _exact(c,'/Script/Engine.Actor:K2_GetActorRotation'),
                _exact(c,'/Script/Engine.Actor:K2_TeleportTo'),
                _exact(c,'/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_CombatMovement.AC_jRPG_CombatMovement_C:UpdateInitialTransform'))
            if controller_context(self._scope._session)!=context:raise RuntimeError('Travel context changed before combat placement')
        entry=dict(actor_identity=tuple(actor_identity),requested_destination=tuple(destination),
            attempted=True,acknowledged=False,home_verified=False)
        self._record.setdefault('combat_placements',[]).append(entry)
        try:
            response=self._owner.place_combatant(prerequisites,tuple(destination))
            values=struct.unpack_from('<12d',response,4096)
            entry.update(acknowledged=True,home_verified=True,before_location=values[:3],
                before_rotation=values[3:6],after_location=values[6:9],after_rotation=values[9:12])
        except BaseException as error:
            entry['error']=str(error);raise
        return dict(entry)

    def add_combatant(self,recipe_id,*,definition_row=None,experimental=False):
        """Add an original battle actor to this owned encounter, explicitly experimental."""
        self._check_no_original_fight()
        from .enemy_combat_additions import add_combatant
        return add_combatant(self,recipe_id,definition_row=definition_row,experimental=experimental)

    def start_authored_encounter(self,recipe_id,*,experimental=False,dispatch=False):
        """Prepare or enter an original roster using this owner's held anchor.

        This experimental route preserves the original battle definition; it
        does not establish the requested enemy's exploration assembly. Default
        dispatch=False verifies an owned copy and entry preflight only.
        """
        self._check_no_original_fight()
        from .original_encounter_roster import enter_original
        return enter_original(self,recipe_id,experimental=experimental,dispatch=dispatch)

    def plan_combat_formation(self,*,spacing=450.):
        """Read current owned roster and plan later positions without moving it."""
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if self._owner.phase!='active' or self._owner.arena_identity is None:
            raise RuntimeError('Formation planning requires an active owned encounter')
        from .enemy_combat_formation import plan_added_positions
        with ReadBatch(self._scope.pid):
            context=controller_context(self._scope._session)
            c=capture_matching(self._scope.pid,classes=('AC_jRPG_BattleManager_C',))
            managers=[o for o in c.objects if o.class_name=='AC_jRPG_BattleManager_C' and
                o.outer_index==context['controller'][1] and not o.object_flags&0x30]
            if len(managers)!=1:raise RuntimeError('Expected current controller battle manager')
            state,c=_fields(c,managers[0],('Enemies','BattleMapBP','IsBattleInitialized','HasBattleStartedEndFlow'))
            arena=state['BattleMapBP'];roster=state['Enemies']
            if (arena is None or (arena.index,arena.serial,arena.address)!=tuple(self._owner.arena_identity) or
                state['IsBattleInitialized'] is not True or state['HasBattleStartedEndFlow'] is not False or
                roster.length!=len(roster.items) or not 4<=roster.length<=10 or any(o is None for o in roster.items)):
                raise RuntimeError('Owned active four-to-ten enemy formation could not be verified')
            identities=[];locations=[]
            for slot,actor in enumerate(roster.items):
                values,c=_fields(c,actor,('RootComponent','BattleSpotIndex'))
                if values['BattleSpotIndex']!=slot or values['RootComponent'] is None:
                    raise RuntimeError('Formation roster no longer matches original spot indices')
                pose,c=_fields(c,values['RootComponent'],('AttachParent','RelativeLocation'))
                if pose['AttachParent'] is not None:raise RuntimeError('Attached roots are unsupported for formation planning')
                locations.append(tuple(pose['RelativeLocation'].fields[k] for k in ('X','Y','Z')))
                identities.append((actor.index,actor.serial,actor.address))
            if controller_context(self._scope._session)!=context:raise RuntimeError('Travel during formation planning')
        planned=plan_added_positions(locations,spacing=spacing)
        return dict(arena_identity=tuple(self._owner.arena_identity),
            preserved_actor_identities=tuple(identities[:3]),
            placements=tuple(dict(row,actor_identity=identities[row['slot']]) for row in planned),
            ground_support_verified=False,assembly_clearance_verified=False)

    def arrange_combatants(self,*,spacing=450.,experimental=False):
        """Place later enemies using a complete plan and existing bounded adapter.

        Partial/unknown results stay journaled for retirement, never replayed or
        silently rolled back. Original three actors and arena spots are preserved.
        """
        if experimental is not True:raise ValueError('Formation placement requires explicit experimental=True')
        plan=self.plan_combat_formation(spacing=spacing)
        attempted={tuple(row['actor_identity']) for row in self._record.get('combat_placements',()) if row.get('attempted')}
        if any(tuple(row['actor_identity']) in attempted for row in plan['placements']):
            raise RuntimeError('Formation contains an already attempted actor; not replayed')
        journal=dict(plan,attempted=True,completed=False,results=[])
        self._record.setdefault('combat_formations',[]).append(journal)
        try:
            for row in plan['placements']:
                journal['results'].append(self.place_combatant(row['actor_identity'],row['destination'],experimental=True))
            journal['completed']=True
        except BaseException as error:
            journal['error']=str(error);raise
        return dict(journal)

    def poll_expanded_formation(self):
        """Repair an opted-in owned encounter once at action selection.

        Waiting performs observation only. An attempted repair is never retried
        for the same roster, including partial failures and unknown outcomes.
        """
        self._scope._check()
        if (self._closed or self._owner.phase!='active' or
            self._owner.actor_identity is None or self._owner.arena_identity is None or
            self._record.get('extra_battle_positions',{}).get('total_count',0)<5 or
            self._record.get('automatic_combat_formations')):
            return None
        now=time.monotonic()
        if now<self._record.get('_formation_next_observation',0):return None
        self._record['_formation_next_observation']=now+2.
        from .enemy_combat_additions import _observe
        try:
            with ReadBatch(self._scope.pid):snapshot=_observe(self)
        except Exception as error:
            self._record['formation_wait_reason']=str(error)
            return None
        identities=tuple(snapshot['identities'])
        if len(identities)<4:return None
        attempts=self._record.setdefault('automatic_combat_formations',[])
        # Journal before entering the canonical mutation path. Neither a failed
        # preflight nor an uncertain dispatch is automatically replayed.
        journal=dict(roster=identities,attempted=True,completed=False)
        attempts.append(journal)
        self._record.pop('formation_wait_reason',None)
        try:
            journal['formation']=self.arrange_combatants(experimental=True)
            journal['completed']=True
        except Exception as error:
            journal['error']=str(error)
        return dict(journal)

    def inspect_assembly(self,recipe_id,*,load=False,include_hierarchy=False):
        """Observe original native body and optional SCS hierarchy.

        Loading is explicit and scoped. This is metadata evidence, never a
        spawn/animation verification result. Inherited templates stay distinct.
        """
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if type(recipe_id) is not str or recipe_id not in self._entries:raise ValueError('Unknown enemy recipe')
        from .enemy_metadata import inspect_class
        return inspect_class(self._scope,self._entries[recipe_id]['class_path'],load=load,include_hierarchy=include_hierarchy)

    def prepare_battle_positions(self,total_count,*,experimental=False):
        """Stage disposable original spot components before entering combat.

        This enables the explicit capacity experiment only. It does not spawn a
        roster or certify ground support, camera framing, turns or targeting.
        Removal/shutdown retires these components with the owned encounter.
        """
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if experimental is not True:raise ValueError('Extra battle positions require explicit experimental=True')
        if type(total_count) is not int or not 5<=total_count<=10:
            raise ValueError('Experimental battle position count must be 5..10')
        capability=getattr(self._scope._session._transport,'enemy_extra_spots_protocol',0)
        if type(capability) is not int or capability!=1:
            raise RuntimeError('Native runtime lacks experimental extra battle positions')
        if self._owner.phase not in ('initialized','active') or self._owner.arena_identity is None:
            raise RuntimeError('Stage and bind an owned enemy before preparing battle positions')
        names=('ChildActorComponent','BP_jRPG_EnemyBattleSpot_C','AddComponentByClass',
            'FinishAddComponent','SetChildActorClass','K2_DestroyComponent','GetAllChildActors')
        with ReadBatch(self._scope.pid):
            catalog=capture_matching(self._scope.pid,names=names)
            catalog=catalog.with_observations(capture_selected(self._scope.pid,(tuple(self._owner.arena_identity),)))
            prerequisites=(catalog.by_index[self._owner.arena_identity[0]],
                _exact(catalog,'/Script/Engine.ChildActorComponent'),
                _exact(catalog,'/Game/jRPGTemplate/Blueprints/Other/Battle/BP_jRPG_EnemyBattleSpot.BP_jRPG_EnemyBattleSpot_C'),
                *(_exact(catalog,path) for path in (
                    '/Script/Engine.Actor:AddComponentByClass','/Script/Engine.Actor:FinishAddComponent',
                    '/Script/Engine.ChildActorComponent:SetChildActorClass',
                    '/Script/Engine.ActorComponent:K2_DestroyComponent','/Script/Engine.Actor:GetAllChildActors')))
        response=self._owner.prepare_extra_spots(prerequisites,total_count)
        report=dict(total_count=total_count,enemy_slot_mask=struct.unpack_from('<Q',response,4096)[0],
            experimental=True,structural_validation='native_observed',ground_support='unverified',
            combat_capacity='unverified',original_slots_modified=False)
        self._record['extra_battle_positions']=report
        return report

    def inspect_placement_clearance(self,center,half_extent):
        """Read-only axis-aligned visibility sweep, ignoring the current pawn.

        A clear result is not a guarantee for other channels or animation poses.
        """
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        point,half=tuple(center),tuple(half_extent)
        if len(point)!=3 or len(half)!=3 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in (*point,*half)) or any(v<=0 or v>1e5 for v in half):
            raise ValueError('Expected a bounded finite clearance center and positive half extents')
        capability=getattr(self._scope._session._transport,'enemy_clearance_protocol',0)
        if type(capability) is not int or capability!=1:raise RuntimeError('Native runtime lacks the enemy clearance query')
        context=controller_context(self._scope._session)
        with ReadBatch(self._scope.pid):
            catalog=capture_matching(self._scope.pid,names=('K2_GetPawn','Default__KismetSystemLibrary','BoxTraceSingle'))
            catalog=catalog.with_observations(capture_selected(self._scope.pid,(context['world'][1:],context['controller'][1:])))
            pc=catalog.by_index[context['controller'][1]];values,catalog=_fields(catalog,pc,('Pawn',))
            prerequisites=(catalog.by_index[context['world'][1]],pc,values['Pawn'],
                _exact(catalog,'/Script/Engine.Controller:K2_GetPawn'),
                _exact(catalog,'/Script/Engine.Default__KismetSystemLibrary'),
                _exact(catalog,'/Script/Engine.KismetSystemLibrary:BoxTraceSingle'))
        response=self._owner.inspect_clearance(prerequisites,(*point,*half))
        return dict(world_identity=tuple(context['world'][1:]),world_path=context['world_path'],
                    center=point,half_extent=half,blocked=bool(struct.unpack_from('<I',response,4096)[0]),
                    trace_channel='visibility',ignored_actor='current pawn',read_only=True,
                    limitation='Sampled volume only; not every channel, attachment or animation pose.')

    def inspect_arena_assembly(self,arena_identity):
        """Native structural observation of one current-world original arena.

        Does not enable spawning or claim streaming completion. Inspect only
        while this spawner is ready and has no owned enemy.
        """
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if type(arena_identity) not in (tuple,list) or len(arena_identity)!=3 or any(type(v) is not int for v in arena_identity):
            raise ValueError('Expected an observed arena identity')
        observation=self.inspect_arenas()
        if not any(tuple(row['identity'])==tuple(arena_identity) for row in observation['arenas']):
            raise ValueError('Arena does not belong to the current world observation')
        context=controller_context(self._scope._session)
        if tuple(context['world'][1:])!=tuple(observation['world_identity']):
            raise RuntimeError('World changed before arena assembly query')
        with ReadBatch(self._scope.pid):
            catalog=capture_matching(self._scope.pid,names=('K2_GetPawn',))
            catalog=catalog.with_observations(capture_selected(self._scope.pid,(context['world'][1:],context['controller'][1:],tuple(arena_identity))))
            pc=catalog.by_index[context['controller'][1]]
            values,catalog=_fields(catalog,pc,('Pawn',))
            prerequisites=(catalog.by_index[context['world'][1]],pc,values['Pawn'],
                           _exact(catalog,'/Script/Engine.Controller:K2_GetPawn'),catalog.by_index[arena_identity[0]])
        response=self._owner.inspect_arena_assembly(prerequisites)
        enemy_mask,party_mask,slots,enabled,transforms,_=struct.unpack_from('<2Q4I',response,4096)
        return dict(arena_identity=tuple(arena_identity),world_identity=observation['world_identity'],
                    enemy_slot_mask=enemy_mask,party_slot_mask=party_mask,slot_count=slots,
                    streaming_source_enabled=bool(enabled),transform_components_checked=transforms,
                    structural_validation='native_observed',streaming_completion='unverified',
                    spawn_support='QA only',read_only=True)

    def status(self):
        current=getattr(self,'original_fight',None)
        return dict(self._record,native_phase=self._owner.phase,has_owned_enemy=self._owner.has_native_work,
                    actor_identity=self._owner.actor_identity,arena_identity=self._owner.arena_identity,supported_worlds=[QA_WORLD],
                    original_fight=current.status() if current is not None else None)

    def spawn(self,recipe_id,*,policy='isolated',arena_identity=None,grounded=False,experimental_battle_positions=None,activate=True,authored_instance_route=None,tuning=None):
        self._scope._check()
        self._check_no_original_fight()
        from .encounter_tuning import settings,EncounterTuningOwner
        tuning=settings(tuning);EncounterTuningOwner.check_available(self._scope,tuning)
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if type(grounded) is not bool:raise ValueError('Grounded spawning flag must be bool')
        if type(activate) is not bool:raise ValueError('Enemy activation flag must be bool')
        if not activate and not grounded:raise ValueError('Deferred activation requires grounded preparation')
        if experimental_battle_positions is not None:
            if type(experimental_battle_positions) is not int or not 5<=experimental_battle_positions<=10:
                raise ValueError('Experimental battle position count must be 5..10')
            if not grounded or arena_identity is None:
                raise ValueError('Experimental positions require grounded preparation and a bound arena')
            capability=getattr(self._scope._session._transport,'enemy_extra_spots_protocol',0)
            if type(capability) is not int or capability!=1:
                raise RuntimeError('Native runtime lacks experimental extra battle positions')
        if grounded and arena_identity is None:raise ValueError('Grounded spawning requires an observed arena identity')
        if policy not in POLICIES:raise ValueError('Unknown encounter policy')
        if type(recipe_id) is not str or recipe_id not in self._entries:raise ValueError('Unknown enemy recipe')
        recipe=self._entries[recipe_id]
        authored_profile=None
        if authored_instance_route is not None:
            from .enemy_authored_routes import authored_spawn_profile
            authored_profile=authored_spawn_profile(dict(recipe,id=recipe_id),include_unverified=True)
            if (type(authored_instance_route) is not int or authored_profile is None or
                authored_instance_route!=authored_profile['route']):
                raise ValueError('Unverified authored instance route for this recipe')
            if not grounded or policy!='isolated':raise ValueError('Authored route candidate requires grounded isolated staging')
            capability=getattr(self._scope._session._transport,'enemy_authored_encounter_research_protocol',0)
            if type(capability) is not int or capability not in (2,3,4,5,6,7) or (authored_instance_route==2 and capability<3) or (authored_instance_route>=3 and capability<4) or (authored_instance_route>=7 and capability<5) or (authored_instance_route>=8 and capability<6) or (authored_instance_route>=12 and capability<7):raise RuntimeError('Authored instance encounter research unavailable')
        if not recipe['spawn_available']:raise ValueError('This entry still requires assembly/encounter validation')
        from .enemy_encounter_preflight import validate_default_encounter
        validate_default_encounter(recipe,authored_instance_route=authored_instance_route)
        if self._owner.has_native_work:raise RuntimeError('Remove the current owned enemy before spawning another')
        context=controller_context(self._scope._session)
        from ._enemy_world_policy import validate_spawn_world
        validate_spawn_world(context['world_path'],grounded,arena_identity,self._scope._session._transport)
        if grounded:
            capability=getattr(self._scope._session._transport,'enemy_grounded_spawn_protocol',0)
            if type(capability) is not int or capability!=2:raise RuntimeError('Native runtime lacks staged grounded enemy spawning')
        if arena_identity is not None:
            capability=getattr(self._scope._session._transport,'enemy_arena_binding_protocol',0)
            if type(capability) is not int or capability!=1:raise RuntimeError('Native runtime lacks owned-instance arena binding')
            self.inspect_arena_assembly(arena_identity)
        self._record=dict(recipe_id=recipe_id,class_path=recipe['class_path'],policy=policy,
                          validation=recipe.get('validation'),grounded_requested=grounded,stage='loading_class')
        try:
            if recipe['class_path'] not in self._classes:
                self._classes[recipe['class_path']]=load_class(self._scope,recipe['class_path'])
            cls=self._classes[recipe['class_path']].return_value
            self._record['stage']='observing_spawn_prerequisites'
            names=('Default__GameplayStatics','BeginDeferredActorSpawnFromClass','FinishSpawningActor','K2_DestroyActor',
                   'K2_GetPawn','K2_GetActorLocation','K2_GetActorRotation','SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame','SetMovementMode')
            if authored_instance_route is not None:names+=('DT_jRPG_Encounters','Default__'+recipe['class_path'].rsplit('.',1)[-1])
            with ReadBatch(self._scope.pid):
                c=capture_matching(self._scope.pid,names=names).with_observations(capture_selected(self._scope.pid,(context['world'][1:],context['controller'][1:])))
                pc=c.by_index[context['controller'][1]];world=c.by_index[context['world'][1]]
                values,c=_fields(c,pc,('Pawn',));pawn=values['Pawn']
                ids=[pc,pawn,world,_exact(c,'/Script/Engine.Default__GameplayStatics'),cls]
                ids.extend(_exact(c,'/Script/Engine.'+path) for path in ('GameplayStatics:BeginDeferredActorSpawnFromClass',
                    'GameplayStatics:FinishSpawningActor','Actor:K2_DestroyActor','Controller:K2_GetPawn'))
                ids.extend(_exact(c,'/Script/Engine.Actor:'+name) for name in ('SetActorEnableCollision','SetActorTickEnabled','SetActorHiddenInGame'))
                location_fn=_exact(c,'/Script/Engine.Actor:K2_GetActorLocation')
                rotation_fn=_exact(c,'/Script/Engine.Actor:K2_GetActorRotation')
            self._record['stage']='sampling_pawn_pose'
            raw_pose=self._owner.pawn_pose((*ids,location_fn,rotation_fn))
            x,y,z,pitch,yaw_degrees,roll=struct.unpack_from('<6d',raw_pose,4096)
            location=dict(X=x,Y=y,Z=z)
            yaw=math.radians(yaw_degrees)
            pose=(0,0,math.sin(yaw/2),math.cos(yaw/2),location['X']+1600*math.cos(yaw)-500*math.sin(yaw),
                  location['Y']+1600*math.sin(yaw)+500*math.cos(yaw),location['Z']+150,0,1,1,1,0)
            self._record['stage']='spawning'
            if grounded:
                pose=(*pose[:6],location['Z']+50000,*pose[7:])
                prepared_ids=(*ids,_exact(c,'/Script/Engine.CharacterMovementComponent:SetMovementMode'))
                if authored_instance_route is not None:
                    encounter_table=_exact(c,'/Game/jRPGTemplate/Datatables/DT_jRPG_Encounters.DT_jRPG_Encounters')
                    original_cdo=_exact(c,recipe['class_path'].rsplit('.',1)[0]+'.Default__'+recipe['class_path'].rsplit('.',1)[-1])
                    self._record['authored_cdo_before_spawn']=[original_cdo.index,original_cdo.serial,original_cdo.address]
                    self._owner.spawn_authored_prepared((*prepared_ids,encounter_table,original_cdo),pose,route=authored_instance_route)
                else:self._owner.spawn_prepared(prepared_ids,pose)
            else:self._owner.spawn(ids,pose)
            self._record.update(stage='spawn_acknowledged',actor_identity=self._owner.actor_identity)
            if authored_instance_route is not None:
                self._record['authored_instance_encounter']=dict(route=authored_instance_route,row=authored_profile['encounter_row'],
                    source=authored_profile.get('source','WorldMap placed Sprong, export 4144'),runtime_validation='construction_selection_verified',encounter_tested=False)
            if grounded:
                self._record['stage']='placing_on_ground'
                with ReadBatch(self._scope.pid):
                    placement_catalog=capture_matching(self._scope.pid,names=('Default__KismetSystemLibrary','LineTraceSingle','BreakHitResult','GetComponentBounds','K2_GetActorLocation','K2_GetActorRotation','K2_SetActorLocationAndRotation','BoxTraceSingle','K2_GetComponentToWorld'))
                    placement_ids=(_exact(placement_catalog,'/Script/Engine.Default__KismetSystemLibrary'),
                        _exact(placement_catalog,'/Script/Engine.KismetSystemLibrary:LineTraceSingle'),
                        _exact(placement_catalog,'/Script/Engine.GameplayStatics:BreakHitResult'),
                        _exact(placement_catalog,'/Script/Engine.KismetSystemLibrary:GetComponentBounds'),
                        _exact(placement_catalog,'/Script/Engine.Actor:K2_GetActorLocation'),
                        _exact(placement_catalog,'/Script/Engine.Actor:K2_GetActorRotation'),
                        _exact(placement_catalog,'/Script/Engine.Actor:K2_SetActorLocationAndRotation'),
                        _exact(placement_catalog,'/Script/Engine.KismetSystemLibrary:BoxTraceSingle'),
                        _exact(placement_catalog,'/Script/Engine.SceneComponent:K2_GetComponentToWorld'))
                placement=self._owner.place_prepared(placement_ids)
                measured=struct.unpack_from('<30d',placement,4096)
                self._record['grounded_placement']=dict(actor_location=measured[:3],ground_max_z=measured[24],
                    ground_min_z=measured[25],clearance_radius=measured[26],distance_from_player=measured[27],
                    ground_samples=int(measured[28]),capsule_clear=bool(measured[29]),capsule_extent=measured[9:12])
            if arena_identity is not None:
                self._record['stage']='binding_arena'
                with ReadBatch(self._scope.pid):
                    arena_catalog=capture_matching(self._scope.pid,names=('Default__KismetSystemLibrary','Conv_ObjectToSoftObjectReference','Conv_SoftObjectReferenceToObject'))
                    arena_catalog=arena_catalog.with_observations(capture_selected(self._scope.pid,(tuple(arena_identity),)))
                    binding_ids=(arena_catalog.by_index[arena_identity[0]],_exact(arena_catalog,'/Script/Engine.Default__KismetSystemLibrary'),
                                 _exact(arena_catalog,'/Script/Engine.KismetSystemLibrary:Conv_ObjectToSoftObjectReference'),
                                 _exact(arena_catalog,'/Script/Engine.KismetSystemLibrary:Conv_SoftObjectReferenceToObject'))
                self._owner.bind_arena(binding_ids)
                self._record['arena_identity']=self._owner.arena_identity
            with ReadBatch(self._scope.pid):
                c=capture_matching(self._scope.pid,names=('BP_Enemy_SerializableComponent','OnEnemyBattleStateLoaded','ResetState'))
                c=c.with_observations(capture_selected(self._scope.pid,(self._owner.actor_identity,)))
                actor=c.by_index[self._owner.actor_identity[0]]
                component=_exact(c,c.path_name(actor)+'.BP_Enemy_SerializableComponent')
                initialize=_exact(c,BASE+':OnEnemyBattleStateLoaded');activate_function=_exact(c,BASE+':ResetState')
            self._record['stage']='initializing'
            self._owner.initialize(component,initialize,policy=int(policy=='original_campaign_actions'))
            if not tuning.is_default:
                self._tuning=EncounterTuningOwner(self._scope,self._owner._owner,tuning)
                self._record['tuning']=self._tuning.arm(self._owner.actor_identity)
            if authored_instance_route is not None:self._record['authored_instance_encounter']['runtime_validation']='initialization_selection_verified'
            if experimental_battle_positions is not None:
                self._record['stage']='preparing_battle_positions'
                self.prepare_battle_positions(experimental_battle_positions,experimental=True)
            if activate:
                self._owner.activate(activate_function);self._record['stage']='active'
                if authored_instance_route is not None:self._record['authored_instance_encounter']['runtime_validation']='activation_selection_verified'
            else:self._record['stage']='prepared'
            return self.status()
        except BaseException as error:
            self._record['error']=str(error)
            raise

    def activate(self):
        """Release an explicitly prepared actor after its setup is verified."""
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        if self._owner.phase!='initialized' or self._record.get('stage')!='prepared':
            raise RuntimeError('Enemy is not in the prepared state')
        with ReadBatch(self._scope.pid):
            catalog=capture_matching(self._scope.pid,names=('ResetState',))
            function=_exact(catalog,BASE+':ResetState')
        self._owner.activate(function)
        self._record['stage']='active'
        return self.status()

    def remove(self):
        self._scope._check()
        if self._closed:raise RuntimeError('Enemy spawner is closed')
        current=getattr(self,'original_fight',None)
        if current is not None and current.phase!='closed':
            if not current.close():raise RuntimeError('Original fight retirement deferred until battle completes')
            self._record={}
            return self.status()
        if self.helper_encounter is not None and self.helper_encounter.phase!='closed':
            if not self.helper_encounter.close():raise RuntimeError('Original helper retirement deferred until battle completes')
        if getattr(self,'_tuning',None) is not None:self._tuning.close();self._tuning=None
        self._owner.remove();self._record={}
        return self.status()

    def close(self):
        if self._closed:return True
        current=getattr(self,'original_fight',None)
        if current is not None and not current.close():return False
        if getattr(self,'_tuning',None) is not None:self._tuning.close();self._tuning=None
        if self.helper_encounter is not None and not self.helper_encounter.close():return False
        if not self._owner.close():return False
        self._closed=True
        for retained in self._classes.values():retained.release()
        self._classes.clear()
        return True
