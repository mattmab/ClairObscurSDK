"""Original-world enemy catalog on the standard SDK mod lifecycle."""
from expedition33.management import ModDefinition, Action, Report


class Mod:
    def __init__(self):
        self.session = None
        self.request = None
        self.inspect = None
        self.catalog = None
        self.helper_catalog = {}
        self.direct_catalog = {}
        self.selected = None
        self.mode = 'isolated'
        self.native = None
        self.want_open = False
        self.spawner = None
        self._pending = None
        self._last_operation = None
        self._last_error = None
        self.arenas = None
        self.arena_identity = None
        self._pending_arena = None
        self._pending_positions = None
        self._pending_activate = True
        self.group_capacity = None
        self.npc_encounter=None;self._npc_pending=None;self._npc_remove=False;self._npc_dialogue_choice=None;self._npc_dialogue_presented=False
        self._pending_addition = None
        self._helper_pending = None
        self._helper_begin = False
        self.tuning = None
        self._pending_tuning = None
        self._original_pending = None
        self._direct_pending = None

    def configure_tuning(self,**changes):
        from expedition33.encounter_tuning import settings,EncounterTuningOwner
        value=settings(self.tuning).to_dict();value.update(changes)
        config=settings(value)
        if self.session is not None:EncounterTuningOwner.check_available(self.session,config)
        self.tuning=config
        return config

    def _capture_tuning(self):
        from expedition33.encounter_tuning import settings,EncounterTuningOwner
        config=settings(self.tuning)
        EncounterTuningOwner.check_available(self.session,config)
        return config

    def management(self):
        return ModDefinition('enemy.spawner.candidate', 'Enemy Spawner',
            version='0.1.0-local-candidate',
            description='193 original-world recipes plus experimental owned-battle additions. Grounded current-world spawning requires an observed arena. Pattern-derived entries are labelled; isolated mode is the default.',
            actions=(Action('catalog', 'Open enemy catalog', self.open),
                     Action('spawn', 'Spawn selected â€” Isolated (default)', self.isolated),
                     Action('spawn-original', 'Spawn selected â€” Original campaign actions', self.original),
                     Action('remove', 'Remove owned enemy', self.remove),
                     Action('status', 'Encounter status / mode details', self.status)))

    def enable(self, session):
        self.session = session
        from expedition33.enemy_spawning import EnemySpawner
        self.spawner = EnemySpawner(session)
        self.catalog = self.spawner.catalog
        self.helper_catalog = self.spawner.original_helper_catalog()
        self.direct_catalog = self.spawner.original_fight_catalog()
        self.selected = next(row['id'] for row in self.catalog['entries'] if row['spawn_available'])
        self.request = self.queue
        self.inspect = self.current_status
        from .view import EnemyView
        self.native = session._session._native_menu_service.for_view(lambda registry: EnemyView(registry,self))

    def open(self, _=None):
        self.want_open = True
        return 'Opening enemy catalog'

    def queue(self,mode,enemy_id=None,*,experimental_battle_positions=None,activate=True):
        self._check_direct_conflict(allow_remove=mode=='remove')
        if self._original_pending is not None:raise RuntimeError('Original battle entry is pending')
        if mode in ('isolated','original_campaign_actions') and enemy_id in self.helper_catalog:
            if mode != 'isolated' or activate is not True or experimental_battle_positions is not None:
                raise ValueError('Original helper catalog routes require isolated approach entry and their original arena')
            return self.queue_helper(self.helper_catalog[enemy_id]['id'])
        helper=self.spawner.helper_encounter
        if self._helper_pending is not None or (mode!='remove' and helper is not None and helper.phase!='closed'):
            raise RuntimeError('Retire the original helper encounter before another world operation')
        if self.npc_encounter is not None and self.npc_encounter.phase!='closed':raise RuntimeError('Retire the NPC encounter before another world operation')
        if mode not in ('isolated','original_campaign_actions','remove','inspect_arenas'):raise ValueError('Unknown encounter mode')
        if self._pending is not None or self._pending_addition is not None:raise RuntimeError('An enemy operation is already pending')
        if type(activate) is not bool:raise ValueError('Enemy activation flag must be bool')
        if not activate and (mode not in ('isolated','original_campaign_actions') or self.arena_identity is None):
            raise ValueError('Deferred activation requires a selected arena and a spawn request')
        if experimental_battle_positions is not None:
            if type(experimental_battle_positions) is not int or not 5<=experimental_battle_positions<=10:
                raise ValueError('Experimental battle position count must be 5..10')
            if mode not in ('isolated','original_campaign_actions') or self.arena_identity is None:
                raise ValueError('Experimental positions require a selected arena and a spawn request')
        self._pending_tuning=self._capture_tuning() if mode in ('isolated','original_campaign_actions') else None
        self._pending=(mode,enemy_id)
        self._pending_arena=self.arena_identity
        self._pending_positions=experimental_battle_positions
        self._pending_activate=activate
        return 'Preparing '+mode+'; closing the menu before the operation.'

    def queue_npc(self,route='clea-normal',variant='collisionless_proximity'):
        self._check_direct_conflict()
        if self._original_pending is not None:raise RuntimeError('Original battle entry is pending')
        if self._helper_pending is not None or (self.spawner.helper_encounter is not None and self.spawner.helper_encounter.phase!='closed'):
            raise RuntimeError('Retire the original helper encounter first')
        from expedition33.npc_encounters import routes
        matches=[r for r in routes() if r['id']==route]
        if len(matches)!=1 or variant not in matches[0]['variants']:raise ValueError('Unknown NPC encounter variation')
        if self.mode!='isolated':raise ValueError('NPC encounter requires isolated mode')
        if route=='alicia-reacher' and getattr(self.spawner._scope._session._transport,'npc_alicia_encounter_protocol',0)!=1:raise RuntimeError('Current Alicia encounter runtime required')
        if route=='curator-lumiere' and getattr(self.spawner._scope._session._transport,'npc_curator_encounter_protocol',0)!=1:raise RuntimeError('Current Curator encounter runtime required')
        if route=='francois-esquienest' and getattr(self.spawner._scope._session._transport,'npc_francois_encounter_protocol',0)!=1:raise RuntimeError('Current Francois encounter runtime required')
        if self.arena_identity is None:raise ValueError('Choose a current-world standard arena first')
        if self._pending is not None or self._pending_addition is not None or self._npc_pending is not None:raise RuntimeError('Another operation is pending')
        if self.spawner._owner.has_native_work or (self.npc_encounter is not None and self.npc_encounter.phase!='closed'):raise RuntimeError('Retire the existing encounter first')
        self._pending_tuning=self._capture_tuning()
        self._npc_pending=(route,variant,tuple(self.arena_identity))
        return 'Preparing original '+matches[0]['name']+'. Approach to start the fight.'+(' Authored phases and cutscenes are included.' if matches[0].get('authored_sequences') else '')

    def queue_dialogue(self,choice):
        if choice not in ('fight','leave') or self.npc_encounter is None or self.npc_encounter.phase!='dialogue_ready':raise ValueError('No matching active NPC dialogue')
        if self._npc_dialogue_choice is not None:raise RuntimeError('Dialogue choice already pending')
        self._npc_dialogue_choice=choice
        return 'Choosing '+choice

    def current_status(self):
        helper=self.spawner.helper_encounter
        return dict(self.spawner.status(),pending=self._pending or self._pending_addition or self._npc_pending or self._helper_pending or self._direct_pending or (('original_alpha_roster','a65ad026a55174bc') if self._original_pending else None),last_operation=self._last_operation,error=self._last_error,npc_encounter=self.npc_encounter.status() if self.npc_encounter is not None else None,helper_encounter=helper.status() if helper is not None else None)

    def _check_direct_conflict(self,*,allow_remove=False):
        if self._direct_pending is not None:raise RuntimeError('Original direct fight is pending')
        current=getattr(self.spawner,'original_fight',None)
        if not allow_remove and current is not None and current.phase!='closed':
            raise RuntimeError('Retire the original direct fight first')

    def _check_direct_start(self,recipe_id,*,tuning=None):
        self._check_direct_conflict()
        if self.mode!='isolated':raise ValueError('Original direct fights require isolated mode')
        recipes=[r for r in self.direct_catalog.values() if r['id']==recipe_id and r.get('menu_available') is True]
        if len(recipes)!=1:raise ValueError('Original direct fight is unavailable')
        if any(getattr(self,key,None) is not None for key in ('_pending','_pending_addition','_npc_pending','_helper_pending','_original_pending')):
            raise RuntimeError('Another encounter operation is pending')
        if self.spawner._owner.has_native_work or any(owner is not None and owner.phase!='closed'
                for owner in (self.npc_encounter,self.spawner.helper_encounter)):
            raise RuntimeError('Retire the existing encounter first')
        from expedition33.encounter_tuning import settings
        if not settings(self.tuning if tuning is None else tuning).is_default:
            raise ValueError('This original fight currently uses authored level, HP and difficulty; reset encounter settings first')
        transport=self.spawner._scope._session._transport
        for name in ('enemy_trigger_entry_research_protocol','battle_entry_dispatch_research_protocol','owned_battle_arena_grounding_protocol'):
            value=getattr(transport,name,0)
            if type(value) is not int or value!=1:raise RuntimeError('Original direct fight requires the current trigger/arena runtime')
        return recipes[0]

    def direct_fight_unavailable_reason(self,recipe_id):
        try:self._check_direct_start(recipe_id)
        except (ValueError,RuntimeError) as error:return str(error)
        return None

    def queue_original_fight(self,recipe_id):
        self._check_direct_start(recipe_id)
        self._direct_pending=dict(recipe_id=recipe_id,tuning=self._capture_tuning())
        return 'Starting the original fight with its own arena; closing the menu first.'

    def queue_helper(self,recipe_id='visages'):
        self._check_direct_conflict()
        if self._original_pending is not None:raise RuntimeError('Original battle entry is pending')
        if recipe_id!='visages' or self.mode!='isolated':raise ValueError('Visages currently supports isolated entry only')
        if any(v is not None for v in (self._pending,self._pending_addition,self._npc_pending,self._helper_pending)):
            raise RuntimeError('Another operation is pending')
        if self.spawner._owner.has_native_work or (self.npc_encounter is not None and self.npc_encounter.phase!='closed'):
            raise RuntimeError('Retire the existing encounter first')
        if self.spawner.helper_encounter is not None and self.spawner.helper_encounter.phase!='closed':
            raise RuntimeError('Retire the existing helper encounter first')
        self._pending_tuning=self._capture_tuning()
        self._helper_pending=recipe_id
        return 'Preparing original Visages assembly and arena. Approach the visible body to enter.'

    def queue_helper_battle(self):
        helper=self.spawner.helper_encounter
        if self._helper_begin or helper is None or helper.phase!='waiting_for_approach':
            raise RuntimeError('No staged boss is waiting for entry')
        self._helper_begin=True
        return 'Starting the staged original fight; closing menu first.'

    def queue_addition(self,recipe_id,definition_row):
        self._check_direct_conflict()
        if self._original_pending is not None:raise RuntimeError('Original battle entry is pending')
        if self._helper_pending is not None or (self.spawner.helper_encounter is not None and self.spawner.helper_encounter.phase!='closed'):
            raise RuntimeError('Original helper encounters do not support battle additions')
        if self._pending is not None or self._pending_addition is not None:raise RuntimeError('An enemy operation is already pending')
        from expedition33.enemy_combat_additions import resolve_definition
        definition=resolve_definition(self.catalog,recipe_id,definition_row)
        self._pending_addition=(definition['recipe_id'],definition['definition_row'])
        return 'Adding original battle actor; closing the menu before engine calls.'

    def queue_original_alpha(self):
        self._check_direct_conflict()
        from expedition33.alpha_original_menu import queue
        return queue(self)

    def poll(self):
        if self._direct_pending is not None:
            pending=self._direct_pending;self._direct_pending=None
            self._last_operation=dict(mode='original_direct_fight',recipe_id=pending['recipe_id'],completed=False)
            try:
                self.native.parent.close_menu();self.want_open=False
                self._check_direct_start(pending['recipe_id'],tuning=pending['tuning'])
                self._last_operation['result']=self.spawner.start_original_fight(pending['recipe_id'],tuning=pending['tuning'])
                self._last_operation['completed']=True;self._last_error=None
            except Exception as error:self._last_error=str(error)
        direct=getattr(self.spawner,'original_fight',None)
        if direct is not None and direct.phase not in ('closed','failed') and (direct.phase!='unknown' or getattr(direct,'entry_acknowledged',False)):
            try:self.spawner.poll_original_fight()
            except Exception as error:self._last_error=str(error)
        from expedition33.alpha_original_menu import poll as poll_original_alpha
        poll_original_alpha(self)
        if self._helper_pending is not None:
            recipe=self._helper_pending;self._helper_pending=None
            tuning=self._pending_tuning;self._pending_tuning=None
            self.native.parent.close_menu();self.want_open=False
            try:
                self._last_operation=dict(mode='original_helper',result=self.spawner.stage_original_helper(recipe,**({'tuning':tuning} if tuning is not None and not tuning.is_default else {})),completed=True)
                self._last_error=None
            except Exception as error:self._last_error=str(error)
        helper=self.spawner.helper_encounter
        if self._helper_begin:
            self._helper_begin=False;self.native.parent.close_menu();self.want_open=False
            try:
                self._last_operation=dict(mode='original_helper_entry',result=helper.begin(),completed=True)
                self._last_error=None
            except Exception as error:self._last_error=str(error)
        if helper is not None and helper.phase not in ('closed','failed'):
            try:self.spawner.poll_original_helper()
            except Exception as error:self._last_error=str(error)
        if self._npc_remove:
            self._npc_remove=False;self.native.parent.close_menu()
            if not self.npc_encounter.close():self._last_error='NPC retirement deferred until battle completes'
        if self._npc_pending is not None:
            route,variant,arena=self._npc_pending;self._npc_pending=None;self.native.parent.close_menu();self.want_open=False
            tuning=self._pending_tuning;self._pending_tuning=None
            try:
                from expedition33.npc_encounters import NpcEncounter
                self.npc_encounter=NpcEncounter(self.session,route=route,variant=variant,**({'tuning':tuning} if tuning is not None and not tuning.is_default else {}))
                self._last_operation=dict(mode='npc_approach',result=self.npc_encounter.stage(arena),completed=True)
                self._last_error=None;self._npc_dialogue_presented=False
            except Exception as error:self._last_error=str(error)
        if self._npc_dialogue_choice is not None:
            choice=self._npc_dialogue_choice;self._npc_dialogue_choice=None
            self.native.parent.close_menu();self.want_open=False
            try:self.npc_encounter.choose_dialogue(choice)
            except Exception as error:self._last_error=str(error)
        if self.npc_encounter is not None and self.npc_encounter.phase not in ('closed','failed'):
            try:self.npc_encounter.poll()
            except Exception as error:self._last_error=str(error)
        if self.npc_encounter is not None:
            if self.npc_encounter.phase=='dialogue_ready' and not self._npc_dialogue_presented:
                self._npc_dialogue_presented=True;self.next_screen='enemy_npc_dialogue';self.want_open=True
            elif self.npc_encounter.phase=='waiting_for_approach':self._npc_dialogue_presented=False
        # The SDK owns encounter identity/phase checks and the once-only
        # journal. Ordinary encounters without extra positions are untouched.
        if self._pending is None and self._pending_addition is None and not self.want_open and (direct is None or direct.phase=='closed'):
            self.spawner.poll_expanded_formation()
        if self._pending_addition is not None:
            recipe,row=self._pending_addition;self._pending_addition=None
            self.native.parent.close_menu()
            self._last_operation=dict(mode='add_combatant',enemy_id=recipe,definition_row=row,completed=False)
            try:
                self._last_operation['addition']=self.spawner.add_combatant(recipe,definition_row=row,experimental=True)
                # Original slots 0..2 retain their authored placement. Only
                # later slots need the experimental expanded formation.
                if self._last_operation['addition']['slot']>=3:
                    self._last_operation['formation']=self.spawner.arrange_combatants(experimental=True)
                self._last_operation['completed']=True;self._last_error=None
            except Exception as error:self._last_error=str(error)
            self.next_screen='enemy_group';self.want_open=True
        if self._pending is not None:
            mode,enemy_id=self._pending;self._pending=None
            tuning=self._pending_tuning;self._pending_tuning=None
            tuning_options={'tuning':tuning} if tuning is not None and not tuning.is_default else {}
            arena=self._pending_arena;self._pending_arena=None
            positions=self._pending_positions;self._pending_positions=None
            activate=self._pending_activate;self._pending_activate=True
            self.native.parent.close_menu()
            try:
                if mode=='inspect_arenas':
                    self.arenas=self.spawner.inspect_arenas()
                    self.arena_identity=None
                    self._last_operation=dict(mode=mode,completed=True)
                    self._last_error=None
                    self.next_screen='enemy_arenas'
                    self.want_open=True
                    return
                authored_options=None
                if mode!='remove':
                    from expedition33.enemy_authored_routes import authored_spawn_profile
                    recipe=next(r for r in self.catalog['entries'] if r['id']==enemy_id)
                    if authored_spawn_profile(recipe) is not None:
                        authored_options=self.spawner.prepare_authored_spawn(enemy_id,policy=mode,
                            arena_identity=arena,activate=activate,experimental_battle_positions=positions)
                    from expedition33.enemy_encounter_preflight import validate_default_encounter
                    validate_default_encounter(recipe,authored_instance_route=
                        authored_options.get('authored_instance_route') if authored_options else None)
                if mode!='remove' and arena is not None:
                    self.spawner.inspect_arena_assembly(arena)
                self.spawner.remove()
                if mode!='remove':
                    if authored_options is not None:spawned=self.spawner.spawn(enemy_id,**authored_options,**tuning_options)
                    elif arena is None:spawned=self.spawner.spawn(enemy_id,policy=mode,**tuning_options)
                    else:spawned=self.spawner.spawn(enemy_id,policy=mode,arena_identity=arena,grounded=True,
                        **({'experimental_battle_positions':positions} if positions is not None else {}),
                        **({'activate':False} if not activate else {}),**tuning_options)
                    self._adopt_bound_arena(arena,spawned)
                self._last_operation=dict(mode=mode,enemy_id=enemy_id,completed=True)
                self._last_error=None
            except Exception as error:
                self._last_error=str(error)
        if self.want_open:
            self.want_open=False
            try:
                self.native.parent.close_menu()
                self.native.open()
            except Exception as error:
                # A rejected presentation must not tear down an active enemy
                # owner. The menu service retains its own failed owner; keep
                # console/status/removal available and do not auto-retry it.
                self._last_error='Menu unavailable; owner retained: '+str(error)

    def _adopt_bound_arena(self,observed,status):
        # Native ownership may assign an initially zero weak-object serial.
        # Keep the acknowledged identity for the same observed index/address;
        # never accept a replacement actor or relax later SDK admission checks.
        if (observed is None or type(status) is not dict or not status.get('has_owned_enemy') or
            status.get('stage') not in ('prepared','active') or self.arenas is None):return False
        bound=status.get('arena_identity')
        if (type(bound) not in (list,tuple) or len(bound)!=3 or any(type(v) is not int for v in bound) or
            observed[1]!=0 or bound[1]<=0 or (observed[0],observed[2])!=(bound[0],bound[2]) or
            self.arena_identity!=tuple(observed)):return False
        rows=[row for row in self.arenas['arenas'] if tuple(row['identity'])==tuple(observed)]
        if len(rows)!=1:return False
        rows[0]['identity']=tuple(bound);self.arena_identity=tuple(bound)
        return True

    def select_arena(self,identity):
        self._check_direct_conflict()
        if self._original_pending is not None:raise RuntimeError('Original battle entry is pending')
        if self._pending is not None or self._pending_addition is not None:raise RuntimeError('An enemy operation is pending')
        if self.arenas is None or not any(tuple(row['identity'])==tuple(identity) for row in self.arenas['arenas']):
            raise ValueError('Refresh current-world arenas before selecting one')
        self.arena_identity=tuple(identity)

    def _request(self, mode, enemy_id=None):
        if mode=='remove' and self.npc_encounter is not None and self.npc_encounter.phase!='closed':
            self._npc_remove=True;return 'Requesting owned NPC retirement'

        if self.request is None:
            raise RuntimeError('Enemy Spawner is not enabled')
        options={}
        if mode in ('isolated','original_campaign_actions') and self.group_capacity is not None:
            options['experimental_battle_positions']=self.group_capacity
        return self.request(mode, enemy_id or self.selected,**options)

    def isolated(self, _=None):
        return self._request('isolated')

    def original(self, _=None):
        return self._request('original_campaign_actions')

    def remove(self, _=None):
        return self._request('remove')

    def status(self, _=None):
        current = self.inspect() if self.inspect else 'Host not connected'
        return Report('Enemy encounters', str(current), entries=(
            ('Isolated encounter (default)', 'Uses a unique instance ID and suppresses the spawned instanceâ€™s authored post-battle game action. Existing placed enemies and their history IDs are untouched. Combat completion/rewards remain under validation.'),
            ('Original campaign actions', 'Keeps the Blueprintâ€™s authored post-battle game action. Completing the encounter may change campaign progress. Uses a unique spawn ID.'),
            ('Availability', 'World recipes preserve authored encounters. Choose an observed arena for experimental grounded spawning outside QA. Encounter group adds exact stored battle definitions to an active owned fight; unresolved records remain available for review.'),))

    def disable(self):
        self._original_pending = None
        self._direct_pending = None
        if self.npc_encounter is not None and not self.npc_encounter.close():raise RuntimeError('NPC cleanup deferred until its owned encounter can retire')
        if self.spawner is not None and not self.spawner.close():
            raise RuntimeError('Enemy cleanup deferred until the owned encounter can retire')
        if self.native is not None:
            self.native.close()
            self.native = None
        self.spawner = None
        self.session = None
        self.request = self.inspect = None
