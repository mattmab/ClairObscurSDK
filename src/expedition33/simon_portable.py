"""Experimental isolated Simon replay, qualified initially on the Continent.

Uses the two exact original battle parameter sources and owned copies of the
three original sequences. It does not dispatch the original campaign graph or
its map-specific exit/reward tail. Battle continuation requires the original
controller's scoped POST result receipt; cinematic continuation requires the
owned player's qualified finite endpoint, never a timer or idle inference.
"""
import math

from . import simon_source
from ._original_trigger_fight import OriginalTriggerFight, _construction_metadata
from .enemy_spawning import EnemySpawner, load_catalog
from ._reader import ReadBatch,shared_operation
from .catalog import capture_selected
from .cinematics.original_game_action import controller_context
from .cinematics.history import field, identity
from .values import read_values_with_references, StoredStruct
from .cinematic_context_panel import CinematicContextPanel
from .sequences import OwnedLevelSequence
from ._menu_latency import MenuLatency, measure_method

WORLD = '/Game/Levels/WorldMap/Level_WorldMap_Main_V2.Level_WorldMap_Main_V2'
SCENES = {stage.name: stage.sequence for stage in simon_source.STAGES if stage.sequence}


def _snapshot(scope):
    """Copy the exact current context and reciprocal exploration pawn position."""
    with shared_operation(scope.pid, _executable=scope._session._transport._executable):
        from .cinematics.controller_anchor import context_observer
        observe=context_observer(scope)
        context = observe()
        c = capture_selected(scope.pid, (tuple(context['controller'][1:]), tuple(context['world'][1:])))
        controller = c.by_index[context['controller'][1]]
        values, c = read_values_with_references(c, controller, fields=('Pawn',))
        pawn = field(values, 'Pawn', 'ObjectProperty')
        if pawn is None:
            raise RuntimeError('Current exploration pawn is unavailable')
        values, c = read_values_with_references(c, c.by_index[context['world'][1]],
                                               fields=('PersistentLevel',))
        level = field(values, 'PersistentLevel', 'ObjectProperty')
        if level is None or level.class_name != 'Level' or (pawn.outer_index, pawn.outer_serial) != (level.index, level.serial):
            raise RuntimeError('Exploration pawn is outside the current PersistentLevel')
        values, c = read_values_with_references(c, level, fields=('OwningWorld', 'bIsVisible'))
        world = field(values, 'OwningWorld', 'ObjectProperty')
        if world is None or identity(world) != tuple(context['world']) or field(values, 'bIsVisible', 'BoolProperty') is not True:
            raise RuntimeError('Exploration level is not current and visible')
        values, c = read_values_with_references(c, pawn, fields=('Controller', 'RootComponent'))
        reciprocal = field(values, 'Controller', 'ObjectProperty')
        root = field(values, 'RootComponent', 'ObjectProperty')
        if reciprocal is None or identity(reciprocal) != tuple(context['controller']) or root is None:
            raise RuntimeError('Exploration pawn/controller relationship changed')
        if (root.outer_index, root.outer_serial) != (pawn.index, pawn.serial):
            raise RuntimeError('Exploration root is not owned by its pawn')
        values, c = read_values_with_references(c, root, fields=('AttachParent', 'RelativeLocation'))
        position = field(values, 'RelativeLocation', 'StructProperty')
        if (field(values, 'AttachParent', 'ObjectProperty') is not None or
                not isinstance(position, StoredStruct) or position.errors or position.truncated or
                c.path_name(c.resolve(position.type_object)) != '/Script/CoreUObject.Vector'):
            raise RuntimeError('Complete unattached exploration frame required')
        xyz = tuple(position.fields[k] for k in 'XYZ')
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e7 for v in xyz):
            raise RuntimeError('Bounded finite exploration position required')
        if observe() != context:
            raise RuntimeError('Exploration context changed during observation')
        return context, identity(pawn), xyz


class PortableSimon:
    """Persist this object before start; poll on the owning SDK thread."""
    def __init__(self, scope, *, disposable_test=False):
        scope._check()
        if disposable_test is not True:
            raise RuntimeError('Portable Simon requires verified disposable save/config isolation')
        capability = getattr(scope._session._transport, 'battle_completion_receipt_protocol', 0)
        if type(capability) is not int or capability != 1:
            raise RuntimeError('Portable Simon requires authoritative battle completion receipts')
        self.scope = scope
        self._scope = scope
        self.state = 'new'
        self.error = None
        self.context = self.initial_pawn = self.initial_position = None
        self.spawner = self.fight = self.sequence = self.panel = self.presentation = None
        self.scene = None
        self.receipts = []
        self.completed_scenes = []
        self.return_position = None
        self._scene_delta = None
        self._closing = False
        self._warm_scope=None
        self._warm_holds=[]
        self._warm_release_unknown=False
        self._warm_pending=None
        self._preload_context=None
        self._preload_ready=False
        self._battle_timings=[]
        self.latency = MenuLatency()
        scope._register_native_owner(self)

    def _current(self):
        with ReadBatch(self.scope.pid, share=True,
                       _executable=self.scope._session._transport._executable):
            if controller_context(self.scope._session, project=True) != self.context:
                raise RuntimeError('Portable Simon world/controller was replaced; no continuation')

    @measure_method('encounter.preload')
    def preload(self):
        """Retain presentation/source assets before entry; no actors or combat.

        May be called ahead of start on the owning SDK thread. Native source,
        geometry and dispatch checks still run fresh when start is requested.
        """
        if self.state!='new':raise RuntimeError('Portable Simon preload is one-shot')
        self.state='preloading'
        from ._scope import SessionScope
        from .assets import load_asset
        from .picto_class_load import load_class
        try:
            context,_,_=_snapshot(self.scope)
            if context['world_path']!=WORLD:raise RuntimeError('Portable Simon candidate currently admits only the Continent')
            self._preload_context=context
            self._warm_scope=SessionScope(self.scope)
            from ._original_trigger_fight import _recipes
            recipes={row['id']:row for row in _recipes(load_catalog())}
            first,second=recipes['simon-normal'],recipes['simon-phase2']
            if (first['battle_source'].split(':')[0]!=second['battle_source'].split(':')[0] or
                    first['arena']['class_path']!=second['arena']['class_path'] or
                    first['trigger_class']!=second['trigger_class']):
                raise RuntimeError('Original Simon stages no longer share the verified source/classes')
            assets=tuple((name,SCENES[name],False) for name in ('intro','transition','outro'))+(
                ('source',first['battle_source'].split(':')[0],False),
                ('arena_class',first['arena']['class_path'],True),('trigger_class',first['trigger_class'],True))
            for name,path,is_class in assets:
                self._warm_pending=path
                with self.latency.measure('preload.'+name):
                    retained=(load_class if is_class else load_asset)(self._warm_scope,path)
                self._warm_holds.append(dict(handle=retained,attempted=False,released=False))
                self._warm_pending=None
                if retained.return_value is None:raise RuntimeError('Original Simon preload returned no asset: '+name)
            with ReadBatch(self.scope.pid,share=True,_executable=self.scope._session._transport._executable):
                with self.latency.measure('preload.construction_metadata'):
                    _construction_metadata(self.scope,self.scope._session._transport,context,self)
            with ReadBatch(self.scope.pid,share=True,_executable=self.scope._session._transport._executable):
                if controller_context(self.scope._session,project=True)!=context:
                    raise RuntimeError('Portable Simon preload context changed')
            self._preload_ready=True
            self.state='preloaded'
        except BaseException as error:
            self.state,self.error='blocked',str(error);raise
        return self.status()

    @measure_method('encounter.prepare_battle')
    def _prepare_battle(self, recipe):
        self._scene_delta = None
        self.fight = OriginalTriggerFight(self.spawner, recipe)
        self.spawner.original_fight = self.fight
        self.fight.prepare(align_source_orientation=True)
        # Copy while the arena is positively owned and prepared. The outro may
        # outlive its retirement; it must never query that retired actor.
        original = self.fight.recipe['arena']['frames']['DefaultSceneRoot']['location']
        grounding = self.fight._arena.grounding
        if not isinstance(grounding, dict) or grounding.get('verified') is not True:
            raise RuntimeError('Verified prepared arena grounding required for cinematic placement')
        after = grounding.get('after')
        if (type(after) not in (tuple, list) or len(after) != 3 or
                not isinstance(original, dict) or set(original) != set('XYZ')):
            raise RuntimeError('Complete original and grounded arena positions required')
        source = tuple(original[k] for k in 'XYZ')
        if any(type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1e7
               for v in (*source, *after)):
            raise RuntimeError('Finite bounded arena positions required')
        delta = tuple(after[i] - source[i] for i in range(3))
        if any(abs(v) > 1e7 for v in delta):
            raise RuntimeError('Cinematic translation exceeds the native origin bound')
        self._scene_delta = delta

    @measure_method('encounter.scene_prepare_and_play')
    def _start_scene(self, name):
        self._current()
        self.scene = name
        self.state = name + '_preparing'
        # Grounding preserves the authored arena rotation. Translation therefore
        # preserves the scenes' original spatial relationship to that arena.
        if self._scene_delta is None:
            raise RuntimeError('Prepared cinematic placement is unavailable')
        delta = self._scene_delta
        if self.panel is None:
            self.panel = CinematicContextPanel(self.scope._session)
            with self.latency.measure('scene.ui_build_once'):
                self.panel.build()
        if self.panel.state != 'built' or self.panel.uncertain:
            raise RuntimeError('Cinematic context panel was not safely detached before scene entry')
        with self.latency.measure('scene.ui_open_fresh_owner'):
            self.panel.open()
        self.sequence = OwnedLevelSequence(self.scope._session)
        with self.latency.measure('scene.sequence_build'):
            self.sequence.build(self.panel, SCENES[name], capture_camera=True, origin_translation=delta)
        with self.latency.measure('scene.completion_prepare'):
            self.sequence.prepare_completion()
        self._current()
        self.state = name + '_play_pending'
        with self.latency.measure('scene.play_dispatch'):
            self.sequence.play()
        self.state = name

    @measure_method('encounter.scene_cleanup')
    def _close_scene(self):
        if self.sequence is not None:
            with self.latency.measure('scene.sequence_close'):
                self.sequence.close()
            self.sequence = None
        # Kept for retirement of an earlier construction attempt. New context
        # panels are permanently invisible and have no opacity owner.
        if self.presentation is not None:
            self.presentation.close()
            self.presentation = None
        if self.panel is not None:
            with self.latency.measure('scene.ui_detach_retain_tree'):
                if self.panel.hide() is not True:
                    from ._sequence_owner import SequenceCleanupDeferred
                    raise SequenceCleanupDeferred('Cinematic context input retirement deferred')

    @measure_method('encounter.start')
    def start(self):
        if self.state not in ('new','preloaded'):
            raise RuntimeError('Portable Simon start is one-shot')
        if self.state=='new':self.preload()
        self.state = 'preparing'
        try:
            self.context, self.initial_pawn, self.initial_position = _snapshot(self.scope)
            if self.context['world_path'] != WORLD:
                raise RuntimeError('Portable Simon candidate currently admits only the Continent')
            if self.context!=self._preload_context:
                raise RuntimeError('Portable Simon preloaded context was replaced; close before retry')
            self.spawner=EnemySpawner(self.scope)
            self.spawner._original_construction_metadata=getattr(self,'_original_construction_metadata',None)
            self._prepare_battle('simon-normal')
            self._start_scene('intro')
        except BaseException as error:
            self.state, self.error = 'blocked', str(error)
            raise
        return self.status()

    def poll(self):
        if getattr(self, '_closing', False):
            return self.status()
        if self.state in ('new', 'preloading', 'preloaded', 'blocked', 'closed', 'completed', 'defeated'):
            return self.status()
        try:
            self._current()
            if self.state in SCENES:
                evidence = self.sequence.completion()
                if evidence['state'] in ('unknown', 'interrupted', 'cancelled'):
                    raise RuntimeError('Cinematic ended without qualified endpoint evidence')
                if not evidence['endpoint_observed']:
                    return self.status()
                self.completed_scenes.append(self.scene)
                self.state = self.scene + '_cleanup'
            if self.state.endswith('_cleanup'):
                scene = self.scene
                self._close_scene()
                self._current()
                if scene in ('intro', 'transition'):
                    self.state = 'battle_entry_pending'
                    self.fight.dispatch_prepared(track_completion=True)
                    self.state = 'battle1' if scene == 'intro' else 'battle2'
                else:
                    context, pawn, position = _snapshot(self.scope)
                    self.return_position = position
                    if (context != self.context or pawn != self.initial_pawn or
                            math.dist(position, self.initial_position) > 1.):
                        raise RuntimeError('Portable encounter did not restore its exploration start position')
                    self.state = 'completed'
            elif self.state in ('battle1', 'battle2'):
                receipt = self.fight._parameters.completion_receipt()
                self.fight.poll()
                if receipt.state in ('unknown', 'revoked'):
                    raise RuntimeError('Battle completion context was lost; no continuation')
                if receipt.state == 'ready':
                    self.receipts.append(receipt)
                    self.state = ('victory_' if receipt.result == 'victory' else 'defeat_') + self.state
            elif self.state.startswith(('victory_', 'defeat_')):
                with self.latency.measure('battle.retirement'):
                    if not self.fight.close():
                        return self.status()
                self._battle_timings.append(dict(recipe=self.fight.recipe['id'],timings=self.fight.latency.snapshot()))
                self._current()
                if self.state.startswith('defeat_'):
                    self.state = 'defeated'
                elif self.state == 'victory_battle1':
                    self._prepare_battle('simon-phase2')
                    self._start_scene('transition')
                else:
                    # The immutable translation was copied before retirement.
                    self._start_scene('outro')
        except BaseException as error:
            from ._sequence_owner import SequenceCleanupDeferred
            if isinstance(error, SequenceCleanupDeferred) and self.state.endswith('_cleanup'):
                return self.status()
            self.state, self.error = 'blocked', str(error)
            raise
        return self.status()

    def status(self):
        return {'state': self.state, 'error': self.error, 'experimental': True,
                'campaign_tail_included': False, 'completed_scenes': tuple(self.completed_scenes),
                'battle_results': tuple(r.result for r in self.receipts),
                'initial_position': self.initial_position, 'return_position': self.return_position,
                'closing': getattr(self, '_closing', False),
                'timings': self.latency.snapshot() if hasattr(self, 'latency') else None,
                'preloaded': getattr(self,'_preload_ready',False),
                'preload_pending': getattr(self,'_warm_pending',None),
                'battle_timings': tuple(getattr(self,'_battle_timings',())),
                'current_battle_timings': self.fight.latency.snapshot() if getattr(self,'fight',None) is not None and hasattr(self.fight,'latency') else None,
                'camera_path_clearance_qualified': False, 'live_accepted': False}

    def _release_preloads(self):
        if getattr(self,'_warm_pending',None) is not None or getattr(self,'_warm_release_unknown',False):return False
        for hold in reversed(getattr(self,'_warm_holds',())):
            if hold['released']:continue
            handle=hold['handle']
            if hold['attempted']:
                states=[getattr(lease,'_state',None) for lease in handle._leases]
                if all(state=='released' for state in states):hold['released']=True;continue
                if any(state in ('unknown','invalid','target_exited') for state in states):self._warm_release_unknown=True
                return False
            hold['attempted']=True;self._warm_release_unknown=True
            acknowledged=handle.release()
            self._warm_release_unknown=False
            if acknowledged is not True:return False
            hold['released']=True
        if getattr(self,'_warm_scope',None) is not None:
            self._warm_scope.close();self._warm_scope=None
        self._preload_ready=False
        return True

    def close(self):
        if self.state == 'closed':
            return True
        self._closing = True
        if getattr(self,'_warm_pending',None) is not None:return False
        try:
            self._close_scene()
        except BaseException as error:
            from ._sequence_owner import SequenceCleanupDeferred
            if isinstance(error, SequenceCleanupDeferred):
                return False
            raise
        if self.panel is not None:
            if self.panel.close_owned_tree() is not True:
                return False
            self.panel = None
        if self.spawner is not None and self.spawner.close() is not True:
            return False
        if not self._release_preloads():return False
        self.state = 'closed'
        return True
