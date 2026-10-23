"""Original split-boss assemblies using the existing SDK owned transactions.

No mod or research-harness imports. The first supported recipe is Visages;
source frame, original parameters and battle lifetime remain native gates.
"""
import json
import math
import time
from copy import deepcopy
from pathlib import Path
from ._scope import SessionScope
from ._reader import ReadBatch
from .catalog import capture_matching, capture_selected
from .enemy_spawning import _exact, _fields
from .cinematics.original_game_action import controller_context
from .owned_battle_arena import OwnedBattleArena
from ._battle_parameter_owner import ParameterResearchOwner
from ._enemy_spawn_wire import EnemyCleanupDeferred


def recipes():
    return json.loads(Path(__file__).with_name('_original_helper_recipes.json').read_text(encoding='utf8'))['recipes']


def catalog_recipes(catalog):
    """Join admitted helper recipes to exact cached relationships, without mutation.

    A battle class is never relabelled as a world-spawn recipe. Missing or
    ambiguous joins remain in the review catalog and cannot select this route.
    """
    result = {}
    candidates = recipes()
    for recipe in candidates:
        key = recipe.get('catalog_id')
        if sum(r.get('catalog_id') == key for r in candidates) != 1:
            continue
        if not all(recipe.get(flag) is True for flag in ('catalog_admitted', 'menu_available', 'walk_up_verified')):
            continue
        matches = [entry for entry in catalog['entries'] if entry.get('id') == key]
        if len(matches) != 1:
            continue
        entry = matches[0]
        if entry.get('role') != 'battle' or entry.get('spawn_available') is not False or entry.get('class_path') != recipe.get('battle_class'):
            continue
        relationships = entry.get('authored_relationships', {})
        bodies = relationships.get('original_visual_assemblies', [])
        if relationships.get('original_visual_assembly'):
            bodies = [*bodies, relationships['original_visual_assembly']]
        if not any(body.get('battle_class') == recipe['battle_class'] and
                   body.get('visual_class') == recipe.get('helper_class') and
                   body.get('property') == 'LinkedDummyCharacterClass' for body in bodies):
            continue
        encounter = recipe.get('encounter_row')
        # Encounter names and enemy-definition names are separate identities.
        # Legacy verified recipes omit enemy_definition_row when both are equal.
        definition = recipe.get('enemy_definition_row', encounter)
        matching_encounters = [
            row for row in relationships.get('authored_encounters', [])
            if row.get('row') == encounter and row.get('enemy_row') == definition and row.get('slot') == 0
        ]
        if (not isinstance(encounter, str) or not encounter or
            not isinstance(definition, str) or not definition or
            definition not in relationships.get('enemy_definition_rows', []) or
            len(matching_encounters) != 1):
            continue
        if recipe.get('supported_policies') != ['isolated'] or recipe.get('preserve_authored_battle_phases') is not True:
            continue
        proof = recipe.get('admission_evidence', {})
        if (proof.get('approach') != 'automatic_visible_body_approach_while_mounted' or
            proof.get('victory') != 'user_confirmed' or
            proof.get('cleanup') != 'verified_with_idle_manager_empty_roster_and_independent_root_retirement'):
            continue
        result[key] = deepcopy(recipe)
    return result


def pose(position, yaw):
    if len(position)!=3 or not all(math.isfinite(v) for v in (*position,yaw)):
        raise ValueError('Finite upright frame required')
    angle=math.radians(yaw)/2
    return (0.,0.,math.sin(angle),math.cos(angle),*position,0.,1.,1.,1.,0.)


def compose(arena_pose, relative_position, relative_yaw):
    angle=2*math.atan2(arena_pose[2],arena_pose[3]);x,y,z=relative_position
    return pose((arena_pose[4]+math.cos(angle)*x-math.sin(angle)*y,
        arena_pose[5]+math.sin(angle)*x+math.cos(angle)*y,arena_pose[6]+z),
        math.degrees(angle)+relative_yaw)


def check_retained_inputs(previous, current):
    if len(previous)!=len(current):raise RuntimeError('Retained entry input count changed')
    for old,new in zip(previous,current):
        if (old.index,old.address)!=(new.index,new.address) or (old.serial and old.serial!=new.serial):
            raise RuntimeError('Retained entry input replaced; preserve owners')


def bounds_approach(position, center, extent):
    """Distance to an observed component AABB, not its submerged actor root.

    This is an interaction region, not a claim about mesh triangle collision.
    Keep all three axes so a body on another elevation cannot start a fight.
    """
    if any(len(v)!=3 for v in (position,center,extent)):
        raise ValueError('Three-dimensional approach bounds required')
    if any(type(x) not in (int,float) or not math.isfinite(x) or abs(x)>1.e7
           for v in (position,center,extent) for x in v):
        raise ValueError('Finite approach bounds required')
    if any(x<=0 or x>1.e5 for x in extent):
        raise ValueError('Nonempty bounded component extent required')
    nearest=tuple(max(c-e,min(p,c+e)) for p,c,e in zip(position,center,extent))
    return nearest,math.dist(position,nearest)


def grounded_bounds_approach(position, center, extent, grounding):
    """Bridge only a component's vertical gap to verified arena ground.

    Giant authored bodies straddle the floor. Keep each original XY footprint
    separate; do not union empty horizontal space or ignore altitude entirely.
    This interaction envelope does not change physical collision or placement.
    """
    bounds_approach(position,center,extent)
    if not all(grounding.get(k) is True for k in ('supported','clearance','verified')):
        raise ValueError('Verified arena ground required for body approach')
    low,high=grounding.get('minimum'),grounding.get('maximum')
    if any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1.e7 for v in (low,high)) or not 0<=high-low<=100:
        raise ValueError('Bounded verified ground interval required')
    bottom=min(center[2]-extent[2],low);top=max(center[2]+extent[2],high)
    return bounds_approach(position,(*center[:2],(bottom+top)/2),(*extent[:2],(top-bottom)/2))


def _approach_profile(source):
    kind = source.get('kind', 'static_socket_part')
    if kind == 'static_socket_part':
        if source.get('class_path') != '/Script/Engine.StaticMeshComponent':
            raise ValueError('Exact original static approach class required')
        return 'StaticMesh', 'Body'
    if (kind == 'skeletal_body' and source.get('field') == 'Body' and
        source.get('class_path') == '/Script/Engine.SkeletalMeshComponent' and
        source.get('parent_field') == 'DefaultSceneRoot' and source.get('socket') == 'None'):
        return 'SkinnedAsset', 'DefaultSceneRoot'
    raise ValueError('Unsupported original approach profile')


class OriginalHelperEncounter:
    def __init__(self, spawner, recipe_id,*,tuning=None):
        from .encounter_tuning import settings,EncounterTuningOwner
        self.tuning=settings(tuning);EncounterTuningOwner.check_available(spawner._scope,self.tuning);self._tuning=None
        spawner._scope._check()
        choices=[r for r in recipes() if r['id']==recipe_id]
        if len(choices)!=1:raise ValueError('Unknown original helper recipe')
        if spawner._owner.has_native_work:raise RuntimeError('Retire existing enemy first')
        transport=spawner._scope._session._transport
        for name in ('owned_helper_source_frame_protocol','owned_helper_parameter_preflight_protocol','owned_battle_arena_approach_protocol'):
            cap=getattr(transport,name,0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Original helper capability unavailable: '+name)
        self.recipe=choices[0];self._owner=spawner._owner
        if self.recipe.get('source_presentation') is not None:
            from ._original_helper_presentation import _validate_profile
            _validate_profile(self.recipe['source_presentation'])
            cap=getattr(transport,'generated_world_asset_load_protocol',0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Retained source World capability unavailable')
        if self.recipe.get('require_clear_approach',True) is False:
            cap=getattr(transport,'owned_battle_arena_advisory_route_protocol',0)
            if type(cap) is not int or cap!=1:raise RuntimeError('Original helper advisory route capability unavailable')
        self._scope=SessionScope(spawner._scope);self._transport=transport
        self._arena=None;self._inputs=None;self._root=None;self._context=None
        self._presentation_report={}
        self.phase='new';self.error=None;self._next_poll=0.;self._armed=False
        self.dispatch_attempted=False;self.battle_observed=False;self.battle_completed=False
        self.approach_point=None;self._helper_name=None
        self.battle_entry_point=None;self._approach_planner=None;self._approach_calls={}
        self._pawn_call=None;self._pawn_identity=None;self._pawn_planner=None
        self._pawn_rebinds=0;self._pawn_read_state='unobserved'
        self.approach_observation=None;self.approach_error=None

    def status(self):
        return dict(recipe=self.recipe['id'],phase=self.phase,error=self.error,
            helper_identity=self._owner.actor_identity if self.phase!='closed' else None,
            arena_identity=self._arena.actor_identity if self._arena and self.phase!='closed' else None,
            approach_point=self.approach_point,approach_armed=self._armed,
            battle_entry_point=self.battle_entry_point,approach_observation=self.approach_observation,
            approach_error=self.approach_error,
            source_presentation=deepcopy(getattr(self,'_presentation_report',{})),
            approach_pawn_identity=self._pawn_identity,pawn_rebinds=self._pawn_rebinds,
            pawn_read_state=self._pawn_read_state,
            grounding=deepcopy(getattr(self._arena,'grounding',None)),
            dispatch_attempted=self.dispatch_attempted,battle_observed=self.battle_observed,
            battle_completed=self.battle_completed)

    def _batch(self):
        return ReadBatch(self._scope.pid,share=True,_executable=self._transport._executable)

    def _pawn_frame(self):
        c=capture_selected(self._scope.pid,(tuple(self._context['controller'][1:]),))
        pc=c.by_index[self._context['controller'][1]]
        fields,c=_fields(c,pc,('Pawn',));pawn=fields['Pawn']
        if pawn is None:raise RuntimeError('Exploration pawn unavailable')
        fields,c=_fields(c,pawn,('RootComponent',))
        values,c=_fields(c,fields['RootComponent'],('AttachParent','RelativeLocation','RelativeRotation'))
        if values['AttachParent'] is not None:raise RuntimeError('Attached pawn root unsupported')
        return pose(tuple(values['RelativeLocation'].fields[k] for k in ('X','Y','Z')),values['RelativeRotation'].fields['Yaw'])

    def stage(self):
        if self.phase!='new':raise RuntimeError('Original helper staging is never replayed')
        self.phase='preparing'
        try:
            self._context=controller_context(self._scope._session)
            with self._batch():start=self._pawn_frame()
            self._arena=OwnedBattleArena(self._scope)
            staging=(*start[:6],start[6]+50000.,*start[7:])
            self._arena.prepare_original(self.recipe['arena_class'],staging)
            with self._batch():
                c=capture_selected(self._scope.pid,(self._arena.actor_identity,))
                c=c.with_observations(capture_matching(self._scope.pid,names=('K2_SetRelativeTransform','GetRelativeTransform')))
                arena=c.by_index[self._arena.actor_identity[0]]
                fields,c=_fields(c,arena,tuple(r['field'] for r in self.recipe['arena_components']))
                setter=_exact(c,'/Script/Engine.SceneComponent:K2_SetRelativeTransform')
                getter=_exact(c,'/Script/Engine.SceneComponent:GetRelativeTransform')
                for frame in self.recipe['arena_components']:
                    if abs(frame['rotation'][0])>1e-6 or abs(frame['rotation'][2])>1e-6 or any(abs(v-1)>1e-6 for v in frame['scale']):
                        raise RuntimeError('Unsupported original arena component frame')
                    component=fields[frame['field']]
                    if frame['override_required']:
                        self._arena.set_component_pose_once(component,setter,getter,pose(frame['position'],frame['rotation'][1]))
                    values,c=_fields(c,component,('RelativeLocation','RelativeRotation','RelativeScale3D'))
                    for key,axes,expected in (('RelativeLocation',('X','Y','Z'),frame['position']),
                            ('RelativeRotation',('Pitch','Yaw','Roll'),frame['rotation']),
                            ('RelativeScale3D',('X','Y','Z'),frame['scale'])):
                        if any(abs(values[key].fields[a]-v)>.001 for a,v in zip(axes,expected)):
                            raise RuntimeError('Original arena component frame differs: '+frame['field'])
            ground=self._arena.ground_once(forward_approach=True,
                diagnostics=getattr(self._transport,'owned_battle_arena_approach_diagnostics_protocol',0)==1,
                require_clear_approach=self.recipe.get('require_clear_approach',True))
            self.battle_entry_point=tuple(ground['positions'][0])
            arena_pose=(*staging[:4],*ground['after'],*staging[7:])
            self._prepare_helper(compose(arena_pose,self.recipe['helper_relative_position'],self.recipe['helper_relative_yaw']))
            from .assets import load_asset
            self._root=load_asset(self._scope,self.recipe['source_asset']).return_value
            if self._root is None:raise RuntimeError('Original trigger asset unavailable')
            self._inputs=self._entry_inputs()
            params=ParameterResearchOwner(self._scope)
            params.match(self._inputs[:3])
            params.entry_arena_cleanup(self._inputs,mode=1,anchor_owner=self._owner._owner,dispatch=False,arena_policy=1)
            params.close()
            if not self.tuning.is_default:
                from .encounter_tuning import EncounterTuningOwner
                self._tuning=EncounterTuningOwner(self._scope,self._owner._owner,self.tuning)
                self._tuning.arm(self._owner.actor_identity)
            # Query setup failure must not replace the proven explicit entry
            # route with a guessed radius around the distant combat slot.
            try:self._prepare_approach_query()
            except Exception as error:self.approach_error=f'{type(error).__name__}: {error}'
            self.phase='waiting_for_approach'
            return self.status()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise

    def _prepare_helper(self,transform):
        from .picto_class_load import load_class
        cls=load_class(self._scope,self.recipe['helper_class']).return_value
        if cls is None:raise RuntimeError('Original helper class unavailable')
        paths=('GameplayStatics:BeginDeferredActorSpawnFromClass','GameplayStatics:FinishSpawningActor',
            'Actor:K2_DestroyActor','Controller:K2_GetPawn','Actor:SetActorEnableCollision',
            'Actor:SetActorTickEnabled','Actor:SetActorHiddenInGame','CharacterMovementComponent:SetMovementMode')
        with self._batch():
            c=capture_matching(self._scope.pid,names=('Default__GameplayStatics',)+tuple(p.split(':')[1] for p in paths))
            c=c.with_observations(capture_selected(self._scope.pid,(tuple(self._context['controller'][1:]),tuple(self._context['world'][1:]))))
            pc=c.by_index[self._context['controller'][1]];fields,c=_fields(c,pc,('Pawn',))
            ids=(pc,fields['Pawn'],c.by_index[self._context['world'][1]],_exact(c,'/Script/Engine.Default__GameplayStatics'),cls,
                *(_exact(c,'/Script/Engine.'+p) for p in paths))
            if controller_context(self._scope._session)!=self._context:raise RuntimeError('Travel during helper preparation')
        self._owner.spawn_visual_prepared(ids,transform)
        if self.recipe.get('source_presentation') is not None:
            from ._original_helper_presentation import prepare_source_presentation
            prepare_source_presentation(self._scope,self._owner,self.recipe['source_presentation'],self._presentation_report)
        with self._batch():
            c=capture_matching(self._scope.pid,names=('Default__KismetSystemLibrary','Conv_ObjectToSoftObjectReference','Conv_SoftObjectReferenceToObject'))
            c=c.with_observations(capture_selected(self._scope.pid,(self._owner.actor_identity,self._arena.actor_identity)))
            actor=c.by_index[self._owner.actor_identity[0]]
            self._helper_name=c.path_name(actor).rsplit('.',1)[-1]
            fields,c=_fields(c,actor,('Body',))
            ids=(c.by_index[self._arena.actor_identity[0]],*(_exact(c,'/Script/Engine.'+p) for p in
                ('Default__KismetSystemLibrary','KismetSystemLibrary:Conv_ObjectToSoftObjectReference','KismetSystemLibrary:Conv_SoftObjectReferenceToObject')))
        self._owner.bind_visual_arena(ids)
        self._owner.configure_visual_tick(fields['Body'])
        self._arena.qualify_helper_once(actor,pose(self.recipe['helper_relative_position'],self.recipe['helper_relative_yaw']))

    def _prepare_approach_query(self):
        with self._batch():
            c=capture_selected(self._scope.pid,(self._owner.actor_identity,tuple(self._context['controller'][1:])))
            actor=c.by_index[self._owner.actor_identity[0]]
            sources=self.recipe['approach_components']
            profiles={source['field']:_approach_profile(source) for source in sources}
            fields,c=_fields(c,actor,tuple(dict.fromkeys([s['field'] for s in sources]+['Body']+[p[1] for p in profiles.values()])))
            components={}
            for source in sources:
                component=fields[source['field']]
                if (component is None or component.outer_index!=actor.index or
                    c.path_name(c.by_index[component.class_index])!=source['class_path']):
                    raise RuntimeError('Original approach component ownership/class differs')
                mesh_field,parent_field=profiles[source['field']]
                values,c=_fields(c,component,(mesh_field,'AttachParent','AttachSocketName','bVisible','bHiddenInGame'))
                parent=values['AttachParent'];expected_parent=fields[parent_field];mesh=values[mesh_field]
                if (parent is None or expected_parent is None or expected_parent.outer_index!=actor.index or
                    (parent.index,parent.serial,parent.address)!=(expected_parent.index,expected_parent.serial,expected_parent.address)
                    or values['AttachSocketName']!=source['socket'] or mesh is None or c.path_name(mesh)!=source['mesh_path']
                    or not values['bVisible'] or values['bHiddenInGame']):
                    raise RuntimeError('Original visible body assembly differs')
                components[source['field']]=component
            c=c.with_observations(capture_matching(self._scope.pid,names=('Default__KismetSystemLibrary','GetComponentBounds','K2_GetActorLocation','Vector')))
            self._approach_planner=self._scope.invocation_planner(catalog=c,selected_results=True)
            self._approach_calls={name:self._approach_planner.prepare(_exact(c,'/Script/Engine.Default__KismetSystemLibrary'),
                _exact(c,'/Script/Engine.KismetSystemLibrary:GetComponentBounds'),Component=component) for name,component in components.items()}

    def _bind_pawn_query(self,pawn,c):
        # Separate planner: possession changes must not revoke body-bound calls.
        worlds=[o for o in c.outer_chain(pawn) if o.class_name=='World']
        if len(worlds)!=1 or (worlds[0].index,worlds[0].serial,worlds[0].address)!=tuple(self._context['world'][1:]):
            raise RuntimeError('Possessed pawn belongs to another world; preserve owners')
        c=c.with_observations(capture_matching(self._scope.pid,names=('K2_GetActorLocation','Vector')))
        planner=self._scope.invocation_planner(catalog=c,selected_results=True)
        try:call=planner.prepare(pawn,_exact(c,'/Script/Engine.Actor:K2_GetActorLocation'))
        except BaseException:
            planner.close();raise
        if self._pawn_planner is not None:self._pawn_planner.close()
        if self._pawn_identity is not None:self._pawn_rebinds+=1
        self._pawn_planner=planner;self._pawn_call=call
        self._pawn_identity=(pawn.index,pawn.serial,pawn.address)

    def _pawn_position(self):
        # A moving RelativeLocation can change during an external struct read.
        # The existing getter copies it on the game thread without moving it.
        c=capture_selected(self._scope.pid,(tuple(self._context['controller'][1:]),))
        values,c=_fields(c,c.by_index[self._context['controller'][1]],('Pawn',));pawn=values['Pawn']
        if pawn is None:
            self._pawn_read_state='waiting_for_possession';return None
        owner,c=_fields(c,pawn,('Controller',));owner=owner['Controller']
        if owner is None or (owner.index,owner.serial,owner.address)!=tuple(self._context['controller'][1:]):
            self._pawn_read_state='waiting_for_possession';return None
        if (pawn.index,pawn.serial,pawn.address)!=self._pawn_identity:
            self._bind_pawn_query(pawn,c)
        with self._pawn_call.invoke() as result:
            if result.outcome!='dispatch_returned':raise RuntimeError('Pawn location getter did not return')
            position=tuple(result.return_value[a] for a in 'XYZ')
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in position):
                raise RuntimeError('Invalid pawn location')
        # Never dispatch using an actor that lost possession during the getter.
        c=capture_selected(self._scope.pid,(tuple(self._context['controller'][1:]),))
        values,c=_fields(c,c.by_index[self._context['controller'][1]],('Pawn',));current=values['Pawn']
        if current is None or (current.index,current.serial,current.address)!=self._pawn_identity:
            self._pawn_read_state='possession_changed_during_read';return None
        self._pawn_read_state='observing';return position

    def _observe_approach(self,position):
        observed=[]
        for name,call in self._approach_calls.items():
            with call.invoke() as result:
                if result.outcome!='dispatch_returned' or set(result.outputs)!= {'Origin','BoxExtent','SphereRadius'}:
                    raise RuntimeError('Component bounds result differs')
                center=tuple(result.outputs['Origin'][a] for a in 'XYZ')
                extent=tuple(result.outputs['BoxExtent'][a] for a in 'XYZ')
                radius=result.outputs['SphereRadius']
                if not math.isfinite(radius) or not 0<radius<=1.e5:
                    raise RuntimeError('Component bounds radius rejected')
            raw_nearest,raw_distance=bounds_approach(position,center,extent)
            nearest,distance=raw_nearest,raw_distance
            if self.recipe.get('grounded_body_approach',False):
                nearest,distance=grounded_bounds_approach(position,center,extent,self._arena.grounding)
            observed.append(dict(component=name,center=center,extent=extent,nearest=nearest,distance_cm=distance,
                raw_distance_cm=raw_distance,grounded_body_approach=self.recipe.get('grounded_body_approach',False)))
        closest=min(observed,key=lambda item:item['distance_cm'])
        self.approach_point=closest['nearest']
        self.approach_observation=dict(**closest,player=position,components=observed,
            battle_anchor_distance_cm=math.dist(position,self.battle_entry_point))
        return closest['distance_cm']

    def _poll_approach(self,position):
        if self.approach_error is not None:return
        try:distance=self._observe_approach(position)
        except Exception as error:
            self.approach_error=f'{type(error).__name__}: {error}'
            return
        # Never initiate immediately if an assembly was staged around the
        # player: require an observed outside position before entering.
        if distance>=400:self._armed=True
        if self._armed and distance<=300:self._dispatch()

    def _entry_inputs(self):
        from .original_trigger_sources import _owned_source,BATTLE_STRUCT
        from ._npc_encounter_preparation import _controller_battle_manager
        with self._batch():
            c=capture_matching(self._scope.pid,classes=('BP_GameAction_TriggerBattle_C',),
                names=(self.recipe['source_asset'].rsplit('.',1)[-1],'FBattleStartParams','StartBattleNEW','GetActorOfClass'))
            c=c.with_observations(capture_selected(self._scope.pid,(self._owner.actor_identity,tuple(self._context['controller'][1:]))))
            root=_exact(c,self.recipe['source_asset'])
            source=_owned_source(c,root,self.recipe['source_trigger'])
            manager,c=_controller_battle_manager(c,c.by_index[self._context['controller'][1]])
            inputs=(_exact(c,BATTLE_STRUCT),source,root,c.by_index[self._owner.actor_identity[0]],manager,
                _exact(c,'/Game/jRPGTemplate/Blueprints/Components/AC_jRPG_BattleManager.AC_jRPG_BattleManager_C:StartBattleNEW'))
            if self._inputs is not None:check_retained_inputs(self._inputs,inputs)
            if controller_context(self._scope._session)!=self._context:raise RuntimeError('Travel during entry preparation')
            if self._owner.lookup_original_helper(_exact(c,'/Script/Engine.GameplayStatics:GetActorOfClass'))!=self._owner.actor_identity:
                raise RuntimeError('Original helper lookup differs')
            return inputs

    def _dispatch(self):
        if self.dispatch_attempted:raise RuntimeError('Helper battle dispatch is never replayed')
        inputs=self._entry_inputs()
        self._scope._session._native_menu_service.close_menu()
        params=ParameterResearchOwner(self._scope)
        self.dispatch_attempted=True;self.phase='battle_pending'
        params.entry_arena_cleanup(inputs,mode=1,anchor_owner=self._owner._owner,dispatch=True,arena_policy=1)
        params.close()

    def begin(self):
        """Enter the staged original encounter explicitly, without moving the player.

        Large authored visual assemblies can extend away from their arena
        entry anchor. This uses exactly the same one-shot preflight and native
        ownership checks as approach entry, never the enclosing quest action.
        """
        self._scope._check()
        if self.phase!='waiting_for_approach':raise RuntimeError('A staged waiting helper encounter is required')
        try:self._dispatch()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise
        return self.status()

    def poll(self):
        if self.phase not in ('waiting_for_approach','battle_pending','battle_active'):return self.status()
        if time.monotonic()<self._next_poll:return self.status()
        self._next_poll=time.monotonic()+.5
        try:
            if controller_context(self._scope._session)!=self._context:raise RuntimeError('World/controller changed; preserve owned cleanup')
            if self.phase=='waiting_for_approach':
                if self.approach_error is None:
                    with self._batch():position=self._pawn_position()
                    if position is not None:self._poll_approach(position)
                    else:self.approach_observation=None
            else:
                from ._npc_encounter_preparation import _controller_battle_manager
                with self._batch():
                    c=capture_selected(self._scope.pid,(tuple(self._context['controller'][1:]),))
                    manager,c=_controller_battle_manager(c,c.by_index[self._context['controller'][1]])
                    values,c=_fields(c,manager,('IsBattleInitialized','HasBattleStartedEndFlow','CurrentBattleStartParams','BattleMapBP','Enemies'))
                    if values['IsBattleInitialized']:
                        params=values['CurrentBattleStartParams'].fields
                        ids=[v for k,v in params.items() if k.startswith('EnemyGlobalID_')]
                        arena=values['BattleMapBP']
                        if ids!=[self._helper_name] or arena is None or (arena.index,arena.serial,arena.address)!=self._arena.actor_identity:
                            raise RuntimeError('Active battle ownership differs; preserve owners')
                        self.battle_observed=True;self.phase='battle_active'
                    elif self.battle_observed and not values['HasBattleStartedEndFlow'] and values['Enemies'].length==0 and values['BattleMapBP'] is None:
                        self.battle_completed=True
                if self.battle_completed:self.close()
            return self.status()
        except BaseException as error:
            self.phase='failed';self.error=f'{type(error).__name__}: {error}';raise

    def close(self):
        if self.phase=='closed':return True
        if getattr(self,'_tuning',None) is not None:self._tuning.close()
        try:
            if self._owner.has_native_work:self._owner.remove()
        except EnemyCleanupDeferred:return False
        if self._arena is not None and not self._arena.close():return False
        if self._approach_planner is not None:self._approach_planner.close()
        if self._pawn_planner is not None:self._pawn_planner.close()
        self._scope.close();self.phase='closed';return True
