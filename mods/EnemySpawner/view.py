"""Searchable pattern-derived encounter catalog using the existing native menu."""
import re
from expedition33.mods_workspace_scroll import ScrollWorkspaceView
from expedition33.management import ManagementError
from expedition33.enemy_encounter_preflight import validate_default_encounter
from expedition33.enemy_authored_routes import authored_spawn_profile


def encounter_issue(entry):
    """Use the same admission evidence as spawn; never alter catalog records."""
    profile=authored_spawn_profile(entry)
    try:
        validate_default_encounter(entry,authored_instance_route=profile['route'] if profile else None)
    except ValueError as error:return str(error)
    return None


class EnemyView(ScrollWorkspaceView):
    def __init__(self, registry, model):
        super().__init__(registry)
        self.model = model
        self.screen = getattr(model,'next_screen',None) or 'enemy_catalog'
        model.next_screen = None
        self.category = 'All'
        self.review = False
        self.selected = None
        self.tuning_return = 'enemy_catalog'

    def search(self, query):
        if type(query) is not str or len(query)>256 or '\0' in query:
            raise ManagementError('Search must be at most 256 characters')
        self.query = query.casefold()
        self.page = 0
        if self.screen!='enemy_combat_library':self.screen = 'enemy_catalog'
        return self.render()

    def _rows(self):
        if not self.screen.startswith('enemy_'):
            return super()._rows()
        model = self.model
        helper_catalog = getattr(model, 'helper_catalog', {})
        direct_catalog = getattr(model, 'direct_catalog', {})
        def row(label, operation, argument=None, enabled=True):
            return (label, 'enemy_'+operation, argument, enabled, None)
        mode = 'Isolated (default)' if model.mode=='isolated' else 'Original campaign actions'
        short_mode = 'Isolated (default)' if model.mode=='isolated' else 'Original actions'
        title = 'Enemy spawn catalog'
        warning = ('Suppresses the owned instance’s post-battle game action.' if model.mode=='isolated' else
                   'Original actions may change campaign progress.')
        if self.screen=='enemy_tuning':
            from expedition33.encounter_tuning import settings,DIFFICULTIES
            config=settings(getattr(model,'tuning',None))
            title='Encounter difficulty'
            description=(config.summary()+'\n\nApplies to the next encounter you spawn, including its group. '
                'Changing this menu does not alter an already staged fight.\n\n'
                'Authored level preserves the original encounter. Offset adds or subtracts levels; Override sets a level from 1 to 99. '
                'Health multiplies the enemy health produced by the game. '
                'Difficulty uses the game\'s Easy / Normal / Hard rules for this battle.\n\n'
                'Campaign difficulty and original encounter assets are unchanged. Reset restores all original settings.')
            available=getattr(model.spawner._scope._session._transport,'encounter_tuning_protocol',0)==1
            if not available:description+='\nLoad the updated SDK candidate to enable these controls.'
            level_label=('Authored' if config.level_mode=='authored' else
                f'Offset {config.level:+d}' if config.level_mode=='offset' else f'Override {config.level}')
            rows=[row('Level: '+level_label,'tuning_mode',enabled=available),
                row(f'Enemy health: {config.health:g}x','tuning_health',1,available),
                row('Difficulty: '+DIFFICULTIES[config.difficulty+1],'tuning_difficulty',enabled=available),
                row('Level -1','tuning_level',-1,available and config.level_mode!='authored'),
                row('Level +1','tuning_level',1,available and config.level_mode!='authored'),
                row('Level -5','tuning_level',-5,available and config.level_mode!='authored'),
                row('Level +5','tuning_level',5,available and config.level_mode!='authored'),
                row('Decrease health multiplier','tuning_health',-1,available),
                row('Reset to original settings','tuning_reset'),row('Back to encounter','tuning_back')]
        elif self.screen=='enemy_original_alpha':
            from expedition33.alpha_original_menu import unavailable_reason
            title='Alpha Simon - original battle'
            description=('Starts the original Alpha Simon roster in the selected current-world arena. '
                'Original attacks, defeat, retry, level / health / difficulty and explicit cleanup passed live testing. '
                'This new menu workflow still needs a live preflight.\n\n'
                'A hidden, temporary Gault encounter anchor is held outside combat; only Alpha Simon enters the battle. '
                'An original exploration Simon is not staged. Normal Simon and phase 2 belong to one separate, unresolved two-battle route.\n'
                'Choose an arena, set difficulty, then start. Use Remove owned encounter after returning to exploration.')
            issue=unavailable_reason(model)
            if issue:description+='\nUnavailable: '+issue
            if model._last_error:description+='\nLast operation: '+model._last_error
            rows=[row('Start Alpha Simon battle','original_alpha_begin',enabled=issue is None),
                row('Choose arena','arenas'),row('Remove owned encounter','remove'),row('Back to catalog','catalog')]
        elif self.screen=='enemy_npc_dialogue':
            npc=getattr(model,'npc_encounter',None)
            title='Custom dialogue - Clea'
            if npc is not None and npc.phase=='dialogue_ready':
                dialog=npc.dialogue();description=dialog['text']+'\n\nThis custom conversation starts an isolated encounter. Original quest dialogue is not executed.'
                rows=[row(label,'npc_dialogue',key) for key,label in dialog['choices']]
            else:description='This conversation has ended.';rows=[row('Back to NPC encounters','npc')]
        elif self.screen=='enemy_helpers' or (self.screen=='enemy_details' and self.selected in helper_catalog):
            title='Visages - original boss assembly' if self.screen=='enemy_details' else 'Original boss assemblies'
            helper=getattr(model.spawner,'helper_encounter',None)
            description=('Visages: original Blueprint assembly and original arena, at authored scale. '
                'Approach the visible body to start the original fight. Phase 2 and authored battle cutscenes remain enabled. '
                'The enclosing campaign quest action is not executed. No manual arena selection required. '
                'The body remains collisionless. Use Fight staged Visages if approach is unavailable. '
                'Menu entry and automatic cleanup have passed live testing. '
                'Ground support and party clearance are required; the straight walking route is advisory. '
                'Visible-body approach while mounted, victory and automatic cleanup are verified. '
                'The enemy\'s own turn was not separately reported in that run.')
            if self.screen=='enemy_details':
                recipe=helper_catalog[self.selected]
                description+='\nOriginal encounter: '+recipe['encounter_row']+'\nBody: '+recipe['helper_class']+'\nCombat: '+recipe['battle_class']
            if helper is not None:description+='\nCurrent: '+helper.phase+((' - '+helper.error) if helper.error else '')
            if helper is not None and helper.approach_error:description+='\nApproach unavailable: '+helper.approach_error
            if helper is not None:
                ground=helper.status().get('grounding')
                if ground and ground.get('verified') and ground.get('approach_supported') is False:
                    description+='\nStraight route not clear: walk around obstacles, or use Fight staged Visages.'
            if model._last_error:description+='\nLast operation: '+model._last_error
            npc=getattr(model,'npc_encounter',None)
            available=(model.mode=='isolated' and not model.spawner._owner.has_native_work
                and (helper is None or helper.phase=='closed') and (npc is None or npc.phase=='closed')
                and getattr(model.spawner._scope._session._transport,'owned_helper_source_frame_protocol',0)==1
                and getattr(model.spawner._scope._session._transport,'owned_helper_parameter_preflight_protocol',0)==1
                and getattr(model.spawner._scope._session._transport,'owned_battle_arena_approach_protocol',0)==1
                and getattr(model.spawner._scope._session._transport,'owned_battle_arena_advisory_route_protocol',0)==1)
            rows=[row('Spawn Visages / approach','helper_spawn','visages',available),
                row('Fight staged Visages','helper_begin',enabled=helper is not None and helper.phase=='waiting_for_approach'),
                row('Remove owned boss / arena','remove',enabled=helper is not None and helper.phase!='closed'),
                row('Back to catalog','catalog')]
        elif self.screen=='enemy_npc':
            title='NPC encounters - original battles'
            description=('Proximity: collisionless; starts when approached.\nSolid / overlap: blocks the player; starts from an engine sphere-overlap query.\nCustom dialogue: solid; offers Fight or Leave before starting combat.\n\nAlicia: verified Reacher fight, proximity only.\nChoose a current-world standard arena first. Original arenas, Alpha and campaign dialogue are not included.')
            npc=getattr(model,'npc_encounter',None)
            if npc is not None:description+='\nCurrent NPC: '+npc.phase+((' - '+npc.error) if npc.error else '')
            description+='\n\nCurator / Renoir: verified phase 2 and final cutscene; these remain enabled. Cutscene participants may float in this map. Campaign flag isolation is unverified.'
            description+='\nFrancois: original assembly, fight, win and cleanup verified; proximity only. Original rock sculpture is included.'
            if getattr(model,'_last_error',None):description+='\nLast operation: '+model._last_error
            available=(model.mode=='isolated' and getattr(model,'arena_identity',None) is not None and not model.spawner._owner.has_native_work and (npc is None or npc.phase=='closed'))
            transport=model.spawner._scope._session._transport
            variants=getattr(transport,'npc_interaction_variants_protocol',0)==1
            alicia=getattr(transport,'npc_alicia_encounter_protocol',0)==1
            curator=getattr(transport,'npc_curator_encounter_protocol',0)==1
            francois=getattr(transport,'npc_francois_encounter_protocol',0)==1
            rows=[row('Clea: proximity','npc_spawn',('clea-normal','collisionless_proximity'),available),
                row('Clea: solid / overlap','npc_spawn',('clea-normal','collision_overlap'),available and variants),
                row('Clea: custom dialogue','npc_spawn',('clea-normal','custom_dialogue'),available and variants),
                row('Alicia: proximity','npc_spawn',('alicia-reacher','collisionless_proximity'),available and alicia),
                row('Curator / Renoir: authored phases','npc_spawn',('curator-lumiere','collisionless_proximity'),available and curator),
                row('Francois: proximity','npc_spawn',('francois-esquienest','collisionless_proximity'),available and francois),
                row('Choose arena','arenas'),row('Remove owned NPC','remove',enabled=npc is not None and npc.phase!='closed'),row('Back to catalog','catalog')]
            if npc is not None and npc.phase=='dialogue_ready':rows.insert(0,row('Talk to Clea','npc_resume_dialogue'))
        elif self.screen=='enemy_group':
            title='Encounter group — experimental'
            capacity=getattr(model,'group_capacity',None)
            description=('1. Choose an arena and spawn an original world encounter.\n'
                '2. Walk into it to start combat.\n'
                '3. Open this menu on a player turn and add battle actors.\n'
                'Original encounter members stay intact; additions use their stored enemy definitions. '
                'The next actor is placed clear of overlapping positions. Maximum ten enemies.\n'
                'For more than four total enemies, prepare capacity before spawning the world enemy. '
                'Authored capacity leaves existing encounters unchanged. Added actors remain experimental; metadata matching is not individual combat verification.')
            if getattr(model,'_last_error',None):description+='\nLast operation: '+model._last_error
            elif getattr(model,'_last_operation',None):description+='\nLast operation: '+str(model._last_operation.get('mode'))+'; completed: '+str(model._last_operation.get('completed'))
            rows=[row('Add actor / battle library','combat_library'),
                  row('Next spawn: '+(str(capacity)+' slots' if capacity else 'Authored capacity'),'capacity'),
                  row('Choose arena','arenas'),row('Back to enemy catalog','catalog')]
        elif self.screen=='enemy_combat_details':
            recipe,definition=self.combat_selection
            from expedition33.enemy_combat_additions import resolve_definition
            resolved=resolve_definition(model.catalog,recipe,definition)
            entry=next(e for e in model.catalog['entries'] if e['id']==recipe)
            title='Add '+entry.get('family_label','enemy')
            description=('Enemy definition: '+definition+'\n'+resolved['class_path']+
                '\nEvidence: '+resolved['validation']+'\nAdds one original battle actor to the current SDK-owned encounter on a player turn. '
                'Existing members remain; overlap repair runs after addition. This does not spawn an exploration enemy.')
            rows=[row('Add to current battle','add_combatant',(recipe,definition)),
                  row('Back to battle library','combat_back')]
            if recipe=='a65ad026a55174bc':rows.insert(0,row('Start original Alpha battle','original_alpha'))
        elif self.screen=='enemy_combat_library':
            title='Add to owned battle — experimental'
            description=('Select an enemy to inspect its full definition before adding it on a player turn. '
                'This adds to the active owned fight; it does not create an exploration enemy. '
                'Search character, variant or row name. Assembly and combat exceptions are reported without replacing the existing group.')
            rows=[row('Back to encounter group','group')]
            from expedition33.enemy_combat_additions import resolve_definition
            for entry in model.catalog['entries']:
                if entry.get('role')!='battle':continue
                for definition in sorted(set(entry.get('authored_relationships',{}).get('enemy_definition_rows',[]))):
                    try:resolve_definition(model.catalog,entry['id'],definition)
                    except ValueError:continue
                    searchable=' '.join((entry.get('family_label',''),entry.get('variant',''),definition)).casefold()
                    if self.query and self.query not in searchable:continue
                    label=definition.replace('_',' ')
                    if len(label)>28:label=label[:10]+' … '+label[-15:]
                    rows.append(row(label,'combat_select',(entry['id'],definition)))
        elif self.screen=='enemy_arenas':
            title='Current-world battle arenas'
            observation=getattr(model,'arenas',None)
            description='Refresh, then select a local arena for grounded spawning. Native assembly and world checks run again before spawning. Ordinary-map encounters remain experimental.'
            rows=[row('Refresh current-world arenas','arena_refresh'),row('Back to enemy catalog','catalog')]
            if observation:
                description+='\n'+observation['world_path']
                rows += [row(r['path'].rsplit(':',1)[-1],'arena_select',r['identity']) for r in observation['arenas']]
                if not observation['arenas']:description+='\nNo original arena observed in this world.'
        elif self.screen=='enemy_details':
            entry = next(r for r in model.catalog['entries'] if r['id']==self.selected)
            title = entry['family_label']+' — '+entry['variant']
            issue=encounter_issue(entry) if entry['spawn_available'] else None
            description = '\n'.join([entry['validation'], entry['class_path'], *entry['limitations'],
                'Mode: '+mode, warning])
            if entry['id'] in ('e7e263f066d33733','ab11b529310fbd73'):
                description+='\nNormal Simon uses an intro, first battle, phase-transition cinematic, second battle and outro. Phase 2 is an internal stage, not a standalone original encounter. The original exploration presentation and return path are not yet available.'
            elif entry['id']=='25a4bf79865ca4fb':
                description+='\nThis world Blueprint defaults to YellowForest_Gault. Its original Mirror Renoir encounter link is unresolved; the Monolith cinematic source does not establish that link.'
            elif entry['id']=='e02190410f616184':
                description+='\nThe Monolith Mirror Renoir battle source and intro bindings are identified. Its direct fight and original exploration presentation have not been qualified. Verified Curator / Renoir is a different encounter.'
            if entry.get('verification',{}).get('native_default_preparation')=='verified':
                description+='\nOriginal default preparation and cleanup verified. Individual combat, victory and framing remain untested.'
            if issue:description+='\nEncounter route unresolved: '+issue
            elif entry['spawn_available']:
                description+='\nWalk into the spawned world enemy to start its authored encounter.'
            relationships=entry.get('authored_relationships',{})
            if relationships:
                enemy_rows=relationships.get('enemy_definition_rows',[])
                encounter_rows=sorted({r['row'] for r in relationships.get('authored_encounters',[])})
                if enemy_rows or encounter_rows:
                    description+='\nAuthored data: '+str(len(enemy_rows))+' enemy rows; '+str(len(encounter_rows))+' encounter rows.\n'+', '.join(encounter_rows[:4])
                if relationships.get('authored_world_encounters'):
                    description+='\nWorld encounter defaults: '+', '.join(relationships['authored_world_encounters'])
                if relationships.get('original_visual_assembly'):
                    description+='\nOriginal visible body: '+relationships['original_visual_assembly']['visual_class']
                elif relationships.get('original_visual_assemblies'):
                    bodies=relationships['original_visual_assemblies']
                    description+='\nOriginal body components ('+str(len(bodies))+'): '+', '.join(r['visual_class'] for r in bodies)
                    description+='\nMultiple references retained for assembly validation.'
                sources=relationships.get('authored_world_blueprint_sources',[])
                if sources:
                    world_sources=sorted({r['world_class'].rsplit('.',1)[-1].removesuffix('_C') for r in sources})
                    description+='\nExact authored world sources: '+', '.join(world_sources[:4])
                    description+='\nThese encounters contain this battle class; their exploration appearance and other enemies may differ.'
            rows = [row('Encounter route unresolved' if issue else 'Spawn — '+short_mode,
                        'spawn', entry['id'], entry['spawn_available'] and issue is None),
                    row('Placement / choose arena','arenas'),
                    row('Mode: '+short_mode, 'mode'), row('Back to enemy catalog', 'catalog')]
            if entry.get('catalog_kind')=='shared_parent':
                description+='\nShared behavior parent. Choose an original child variant below; these links do not add new gameplay verification.'
                rows[0]=row('Shared parent — choose variant','spawn',entry['id'],False)
                for child in relationships.get('verified_child_world_recipes',[]):
                    matches=[e for e in model.catalog['entries'] if e['id']==child['recipe_id'] and e['class_path']==child['class_path'] and len(e.get('ancestry',[]))>1 and e['ancestry'][1]==entry['class_path']]
                    if len(matches)==1:rows.append(row('Choose '+child['label'],'select',child['recipe_id']))
            profile=authored_spawn_profile(entry)
            if profile is not None:
                played=profile['validation']=='approach_encounter_completed_through_victory'
                description+='\n'+('Verified authored route: ' if played else 'Prepared authored route: ')+profile['encounter_row']+(
                    '; approach and victory tested.' if played else '; original preparation and initialized selection tested; individual combat untested.')
                if profile['validation']=='approach_encounter_user_confirmed':
                    description=description.replace('Prepared authored route: '+profile['encounter_row']+'; original preparation and initialized selection tested; individual combat untested.',
                        'Fight-tested authored route: '+profile['encounter_row']+'; working fight user-confirmed; victory not explicitly confirmed.')
                description+='\nSelect the '+profile['arena_label']+' and use isolated mode. '+profile['limitation']+'.'
                rows[0]=row('Spawn authored '+entry['family_label']+' — Isolated','spawn',entry['id'],
                    entry['spawn_available'] and model.mode=='isolated' and getattr(model,'arena_identity',None) is not None)
            if not entry['spawn_available']:
                from expedition33.enemy_encounter_sources import authored_encounter_sources
                sources=authored_encounter_sources(model.catalog,entry['id'])
                if sources:
                    source_description='Full authored encounter choices\nIncludes this battle enemy in its original group. The exploration appearance and other enemies may differ.\n'
                    for number,source in enumerate(sources,1):
                        world_entry=next(e for e in model.catalog['entries'] if e['id']==source['recipe_id'])
                        source_issue=encounter_issue(world_entry)
                        world_profile=authored_spawn_profile(world_entry)
                        if world_profile and world_profile['encounter_row']!=source['encounter']:
                            source_issue='Source row differs from the verified authored override'
                        source_description+='\n'+str(number)+'. '+source['encounter']+' → '+source['variant']
                        if source_issue:source_description+=' (encounter route unresolved)'
                        label=source['encounter']
                        if len(label)>22:label=label[:10]+' … '+label[-9:]
                        rows.insert(-1,row(str(number)+'. '+label,'spawn',source['recipe_id'],source_issue is None))
                    description=source_description+'\n\n'+description
            if entry['id']=='a65ad026a55174bc':rows.insert(0,row('Start original Alpha battle','original_alpha'))
            if entry['id'] in direct_catalog:
                direct=direct_catalog[entry['id']]
                reason=model.direct_fight_unavailable_reason(direct['id'])
                description+='\n\n'+direct['label']+'\nNo exploration character or walk-up interaction is spawned.\n'+'\n'.join(direct.get('restrictions',()))
                if reason:description+='\nOriginal fight unavailable: '+reason
                current=getattr(model.spawner,'original_fight',None)
                if current is not None:description+='\nOriginal fight state: '+current.phase
                rows.insert(0,row('Start '+direct['label'],'direct_begin',direct['id'],reason is None))
                if current is not None and current.phase!='closed':
                    rows.insert(1,row('Retire original fight / arena','remove'))
            verification=entry.get('verification',{})
            for key,label in (('encounter','Combat'),('own_enemy_turn','Enemy turn'),('victory','Victory'),('owned_cleanup','Owned cleanup')):
                if key in verification:description+='\n'+label+': '+str(verification[key]).replace('_',' ')
        else:
            entries = [r for r in model.catalog['entries'] if
                (not (r['spawn_available'] or r['id'] in helper_catalog or r['id'] in direct_catalog) if self.review else (r['spawn_available'] or r['id'] in helper_catalog or r['id'] in direct_catalog)) and
                (self.category=='All' or self.category in r['categories']) and
                (not self.query or self.query in (r['class_path']+' '+r['family_label']+' '+r['validation']+' '+helper_catalog.get(r['id'],{}).get('label','')+' '+direct_catalog.get(r['id'],{}).get('label','')).casefold())]
            world_entries=[entry for entry in model.catalog['entries'] if entry['spawn_available']]
            issues={entry['id']:encounter_issue(entry) for entry in world_entries}
            parents=sum(entry.get('catalog_kind')=='shared_parent' for entry in world_entries)
            unresolved=sum(bool(issues[entry['id']]) and entry.get('catalog_kind')!='shared_parent' for entry in world_entries)
            ready=sum(issues[entry['id']] is None and entry.get('catalog_kind')!='shared_parent' for entry in world_entries)
            description = (f"{ready} world routes | {len(helper_catalog)} verified boss assembly | {len(direct_catalog)} original direct fight | {parents} parent entries | {unresolved} unresolved\n"
                f"{len(entries)} matching entries | {len(world_entries)} original-world recipes\n"
                'Mode: '+mode+'\n'+warning+'\n\n'
                '1. Choose an arena for world enemies. Visages includes its original arena.\n'
                '2. Search and select an enemy, then choose Spawn.\n'
                '3. Approach it to start its authored encounter.\n\n'
                'Ready routes use shared spawning; not every variant was individually fought.\n'
                'Needs route entries remain visible with spawning disabled. Shared parents offer concrete variants.\n'
                'Original direct fights create their own arena and start immediately. Battle-only entries may offer full authored encounters. Encounter group adds enemies to an active owned fight.')
            rows = [row('Mode: '+short_mode, 'mode'), row('Category: '+self.category, 'category'),
                    row('Show spawn catalog' if self.review else 'Battle-only / unresolved', 'review'),
                    row('Placement / choose arena','arenas'),row('Encounter group / add actors','group'),row('NPC encounters','npc'),row('Original boss assemblies','helpers'),row('Alpha Simon / original battle','original_alpha'),row('Remove owned enemy', 'remove')]
            description+='\nPlacement: '+('Grounded; arena selected' if getattr(model,'arena_identity',None) is not None else 'QA legacy; no arena selected')
            for entry in entries:
                label=re.sub(r'^BP_(?:jRPG_)?Enemy_?(?:World|Battle)_?', '', entry['variant']).replace('_',' ')
                if entry['id'] in helper_catalog:label=helper_catalog[entry['id']]['label']+' - original assembly'
                elif entry['id'] in direct_catalog:label=direct_catalog[entry['id']]['label']
                # Keep variant suffixes visible instead of clipping every row
                # to the same generated Blueprint prefix.
                if len(label)>40:label=label[:17]+' … '+label[-20:]
                if entry.get('catalog_kind')=='shared_parent':label='Parent — choose variant: '+label
                elif entry['spawn_available'] and issues[entry['id']]:label='Needs route: '+label
                rows.append(row(label,'select',entry['id']))
        if self.screen in ('enemy_catalog','enemy_details','enemy_helpers','enemy_npc','enemy_group','enemy_original_alpha'):
            from expedition33.encounter_tuning import settings
            config=settings(getattr(model,'tuning',None))
            description+='\n\nNext encounter: '+config.summary()
            rows.insert(0,row('Encounter difficulty / level / HP','tuning'))
        return title, description, rows

    def activate(self, revision, token, *, value=None, reset=False):
        command = self._commands.get(token)
        if command and command[0]=='back' and self.screen in ('enemy_details','enemy_combat_details','enemy_combat_library','enemy_group','enemy_npc','enemy_npc_dialogue','enemy_helpers','enemy_tuning','enemy_original_alpha'):
            if revision!=self._revision:raise ManagementError('Stale enemy control')
            self.screen={'enemy_combat_details':'enemy_combat_library','enemy_combat_library':'enemy_group',
                         'enemy_group':'enemy_catalog','enemy_details':'enemy_catalog','enemy_npc':'enemy_catalog','enemy_npc_dialogue':'enemy_npc','enemy_helpers':'enemy_catalog','enemy_original_alpha':'enemy_catalog','enemy_tuning':self.tuning_return}[self.screen];self.page=0
            return self.render()
        if command is None or not command[0].startswith('enemy_'):
            return super().activate(revision, token, value=value, reset=reset)
        self._check()
        if revision!=self._revision or not command[2]:
            raise ManagementError('Stale or unavailable enemy control; refresh')
        operation, argument, _ = command
        self._invalidate()
        if operation.startswith('enemy_tuning'):
            from expedition33.encounter_tuning import settings
            config=settings(getattr(self.model,'tuning',None))
            if operation=='enemy_tuning':self.tuning_return=self.screen;self.screen='enemy_tuning';self.page=0
            elif operation=='enemy_tuning_back':self.screen=self.tuning_return;self.page=0
            elif operation=='enemy_tuning_mode':
                modes=('authored','offset','override');mode=modes[(modes.index(config.level_mode)+1)%3]
                self.model.configure_tuning(level_mode=mode,level=1 if mode=='override' else 0)
            elif operation=='enemy_tuning_level':
                low,high=(-98,98) if config.level_mode=='offset' else (1,99)
                self.model.configure_tuning(level=max(low,min(high,config.level+argument)))
            elif operation=='enemy_tuning_health':
                maximum=getattr(self.model.spawner._scope._session._transport,'encounter_tuning_max_health_multiplier',100)
                choices=tuple(v for v in (.1,.25,.5,.75,1.,1.5,2.,3.,5.,10.,20.,50.,100.,250.,500.,1000.) if v<=maximum)
                index=min(range(len(choices)),key=lambda i:abs(choices[i]-config.health))
                self.model.configure_tuning(health=choices[max(0,min(len(choices)-1,index+argument))])
            elif operation=='enemy_tuning_difficulty':self.model.configure_tuning(difficulty=((config.difficulty+2)%4)-1)
            elif operation=='enemy_tuning_reset':self.model.configure_tuning(level_mode='authored',level=0,health=1.,difficulty=-1)
        elif operation=='enemy_mode':
            self.model.mode = 'original_campaign_actions' if self.model.mode=='isolated' else 'isolated'
        elif operation=='enemy_category':
            categories=('All','Nevrons','Gestrals','NPCs','Main Characters','Unknown/Unclassified')
            self.category=categories[(categories.index(self.category)+1)%len(categories)]
            self.page=0
        elif operation=='enemy_review':
            self.review=not self.review
            self.page=0
        elif operation=='enemy_select':
            self.selected=argument
            self.model.selected=argument
            self.screen='enemy_details'
            self.page=0
        elif operation=='enemy_catalog':
            self.screen='enemy_catalog'
            self.page=0
        elif operation=='enemy_original_alpha':
            self.screen='enemy_original_alpha';self.page=0
        elif operation=='enemy_original_alpha_begin':
            self.status=self.model.queue_original_alpha()
        elif operation=='enemy_direct_begin':
            self.status=self.model.queue_original_fight(argument)
        elif operation=='enemy_helpers':
            self.screen='enemy_helpers';self.page=0
        elif operation=='enemy_helper_spawn':
            self.status=self.model.queue_helper(argument)
        elif operation=='enemy_helper_begin':
            self.status=self.model.queue_helper_battle()
        elif operation=='enemy_npc':
            self.screen='enemy_npc';self.page=0
        elif operation=='enemy_npc_spawn':
            self.status=self.model.queue_npc(*argument)
        elif operation=='enemy_npc_resume_dialogue':
            self.screen='enemy_npc_dialogue';self.page=0
        elif operation=='enemy_npc_dialogue':
            self.status=self.model.queue_dialogue(argument)
        elif operation=='enemy_group':
            self.screen='enemy_group';self.page=0
        elif operation=='enemy_combat_library':
            self.screen='enemy_combat_library';self.query='';self.page=0
        elif operation=='enemy_combat_back':
            self.screen='enemy_combat_library';self.page=0
        elif operation=='enemy_combat_select':
            self.combat_selection=argument;self.screen='enemy_combat_details';self.page=0
        elif operation=='enemy_capacity':
            choices=(None,5,6,7,8,9,10)
            self.model.group_capacity=choices[(choices.index(self.model.group_capacity)+1)%len(choices)]
        elif operation=='enemy_add_combatant':
            self.status=self.model.queue_addition(*argument)
        elif operation=='enemy_arenas':
            self.screen='enemy_arenas';self.page=0
        elif operation=='enemy_arena_refresh':
            self.status=self.model._request('inspect_arenas')
        elif operation=='enemy_arena_select':
            self.model.select_arena(argument);self.screen='enemy_catalog';self.page=0
        elif operation=='enemy_spawn':
            self.status=self.model._request(self.model.mode, argument)
        elif operation=='enemy_remove':
            self.status=self.model._request('remove')
        return self.render()
