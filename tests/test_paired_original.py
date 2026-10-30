from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import paired_original as paired
from expedition33 import pair_source as source
from expedition33.values import StoredMap
from test_simon_original import Scope


class PairArenaMembershipTests(unittest.TestCase):
    def test_inactive_exact_source_arena_rejected_before_pose_or_dispatch(self):
        scope = Scope()
        context = dict(controller=(123,1,2,0x10000),world=(123,2,3,0x20000))
        sequence = SimpleNamespace(class_name='LevelSequence')
        arena, trigger = object(), object()
        catalog = Mock()
        catalog.resolve.return_value = sequence
        catalog.path_name.return_value = paired.phase.SEQUENCE
        catalog.with_observations.return_value = catalog
        catalog.find_path.return_value = arena
        with patch('expedition33.original_encounter_roster._verify_source'), \
                patch.object(paired,'read_values_with_references',return_value=(object(),catalog)) as read, \
                patch.object(paired,'field',return_value=object()), \
                patch.object(paired,'_member',side_effect=(None,object())), \
                patch.object(paired,'_soft_path',return_value=source.ARENA), \
                patch.object(paired,'capture_matching',return_value=catalog), \
                patch.object(paired,'capture_selected',return_value=catalog), \
                patch('expedition33._world_level_membership.observe_actor_membership',
                      side_effect=RuntimeError('Actor level is not visible')) as membership:
            with self.assertRaisesRegex(RuntimeError,'not visible'):
                paired._Provider().dependencies(scope,catalog,
                    SimpleNamespace(actions=(trigger,)),sequence,context)
        membership.assert_called_once_with(scope,arena,expected_context=context)
        self.assertEqual(read.call_count,1)  # Source parameters only; no arena pose or call.


class Provider:
    def __init__(self):
        self.scope = Scope()
        self.current = dict(controller=(123,1,2,0x10000),world=(123,2,3,0x20000),world_path=source.WORLD)
        self.current_history = dict(decoded=True,read_error=None,selected_slot=1,
            context_identities=dict(world=self.current['world']),history=StoredMap({}))
        self.loaded = []
        self.monitor_value = SimpleNamespace(idle=True,sequence_player=None)
        self.monitor_object = Mock()
        self.monitor_object.world_changed = False
        self.monitor_object.observe.side_effect = lambda:self.monitor_value
        self.planner = Mock();self.call = Mock()
        self.invocations = self.dependency_checks = 0
        self.invoke_error = self.dependency_error = None
        self.phase_error = None
        self.phase_calls = 0
        @contextmanager
        def invoke():
            self.invocations += 1
            if self.invoke_error:raise self.invoke_error
            yield None
        self.call.invoke.side_effect = invoke
    def child(self,scope):return self.scope
    def context(self,scope):return dict(self.current)
    def history(self,scope):return self.current_history
    def services(self,*unused):return ('catalog','executor','cinematic','function')
    def load(self,scope,path):
        self.loaded.append(path);return SimpleNamespace(return_value=path)
    def observations(self,*unused):return 'catalog'
    def graph(self,catalog,root):return 'graph',catalog
    def dependencies(self,scope,catalog,*unused):
        self.dependency_checks += 1
        if self.dependency_error:raise self.dependency_error
        return catalog
    def monitor(self,*unused):return self.monitor_object
    def plan(self,*unused):return self.planner,self.call
    def phase(self,*unused):
        self.phase_calls += 1
        if self.phase_error:raise self.phase_error
        return SimpleNamespace(state='pair_sequence_started',asset_path=paired.phase.SEQUENCE,
            requested_id=paired.phase.CINEMATIC_ID,sequence_started=True,camera_target=(123,1,2),camera_class='CineCameraActor')


class PairedOriginalTests(unittest.TestCase):
    def setUp(self):self.scope,self.provider = Scope(),Provider()
    def prepare(self):return paired.prepare(self.scope,disposable_test=True,_provider=self.provider)

    def test_disposable_and_original_world_gates_precede_loads(self):
        with self.assertRaisesRegex(RuntimeError,'disposable'):paired.prepare(self.scope,_provider=self.provider)
        self.assertEqual(self.provider.loaded,[])
        self.provider.current['world_path'] = '/Game/Other.Other'
        with self.assertRaisesRegex(RuntimeError,'CleasTower'):self.prepare()
        self.assertEqual(self.provider.loaded,[])
        self.assertTrue(self.provider.scope.closed)

    def test_played_history_preserves_original_policy_and_slot_is_required(self):
        history = StoredMap({paired.phase.CINEMATIC_ID:True})
        self.provider.current_history['history'] = history
        operation = self.prepare()
        self.addCleanup(operation.close)
        operation.start()
        self.assertIs(self.provider.current_history['history'],history)
        self.assertEqual(self.provider.invocations,1)
        self.assertEqual(operation.status()['repeat_policy'],'original')
        self.assertFalse(operation.status()['repeat_verified'])
        self.provider = Provider();self.provider.current_history['selected_slot'] = True
        with self.assertRaisesRegex(RuntimeError,'slot'):self.prepare()

    def test_exact_root_and_phase_are_retained_without_mutating_preparation(self):
        operation = self.prepare()
        self.assertEqual(self.provider.loaded,[source.ROOT,paired.phase.SEQUENCE])
        self.assertEqual(self.provider.invocations,0)
        self.assertEqual(self.provider.dependency_checks,1)
        operation.close()
        self.assertTrue(self.provider.scope.closed)

    def test_unproved_dependencies_fail_without_dispatch_and_close_scope(self):
        self.provider.dependency_error = RuntimeError('soft arena unreadable')
        with self.assertRaisesRegex(RuntimeError,'soft arena unreadable'):self.prepare()
        self.assertEqual(self.provider.invocations,0)
        self.assertTrue(self.provider.scope.closed)

    def test_start_revalidates_world_graph_arena_and_idle_before_one_shot(self):
        operation = self.prepare()
        self.provider.dependency_error = RuntimeError('arena moved')
        with self.assertRaisesRegex(RuntimeError,'arena moved'):operation.start()
        self.assertEqual(self.provider.invocations,0)
        self.assertFalse(operation.dispatch_attempted)
        self.provider.dependency_error = None
        operation.start()
        self.assertEqual(self.provider.invocations,1)
        with self.assertRaisesRegex(RuntimeError,'one-shot'):operation.start()
        self.assertEqual(self.provider.invocations,1)

    def test_idle_never_proves_completion_or_visibility(self):
        operation = self.prepare();operation.start()
        self.assertEqual(operation.poll()['state'],'dispatch_acknowledged')
        self.provider.monitor_value = SimpleNamespace(idle=False,sequence_player=None)
        self.assertEqual(operation.poll()['state'],'original_graph_active')
        self.provider.monitor_value = SimpleNamespace(idle=True,sequence_player=None)
        status = operation.poll()
        self.assertEqual(status['state'],'idle_after_activity')
        self.assertFalse(status['completion_proved']);self.assertFalse(status['visibility_proved'])

    def test_phase_evidence_is_diagnostic_and_read_errors_do_not_retry(self):
        operation = self.prepare();operation.start()
        self.provider.monitor_value = SimpleNamespace(idle=False,sequence_player=(123,10,1,0x30000))
        status = operation.poll()
        self.assertEqual(status['phase_observation']['asset'],paired.phase.SEQUENCE)
        self.assertTrue(status['phase_observation_current'])
        self.assertFalse(status['visibility_proved'])
        self.provider.phase_error = RuntimeError('camera unreadable')
        status = operation.poll()
        self.assertEqual(status['state'],'original_graph_active')
        self.assertEqual(status['phase_observation_error'],'camera unreadable')
        self.assertFalse(status['phase_observation_current'])
        self.assertEqual(self.provider.invocations,1)

    def test_world_change_is_terminal_and_never_reads_old_services(self):
        operation = self.prepare();operation.start()
        calls = self.provider.monitor_object.observe.call_count
        self.provider.current['world'] = (123,99,1,0x99999)
        self.assertEqual(operation.poll()['state'],'world_changed')
        self.assertEqual(self.provider.monitor_object.observe.call_count,calls)
        self.provider.current['world'] = operation._context['world']
        self.assertEqual(operation.poll()['state'],'world_changed')
        self.assertEqual(self.provider.monitor_object.observe.call_count,calls)
        with self.assertRaises(RuntimeError):operation.start()

    def test_unknown_native_dispatch_is_not_replayed_or_promoted_by_idle(self):
        operation = self.prepare();self.provider.invoke_error = RuntimeError('ack lost')
        with self.assertRaisesRegex(RuntimeError,'ack lost'):operation.start()
        self.assertEqual(operation.poll()['state'],'unknown')
        self.assertTrue(operation.status()['dispatch_unknown'])
        with self.assertRaises(RuntimeError):operation.start()
        self.assertEqual(self.provider.invocations,1)

    def test_close_only_releases_own_planner_monitor_and_scope(self):
        operation = self.prepare();operation.start();operation.close();operation.close()
        self.provider.planner.close.assert_called_once();self.provider.monitor_object.close.assert_called_once()
        self.assertEqual(self.provider.invocations,1)
        self.assertTrue(self.provider.scope.closed)

    def test_plan_uses_existing_explicit_blueprint_codec(self):
        import test_blueprint_invocation
        from expedition33 import _blueprint_wire
        f = test_blueprint_invocation.BlueprintInvocationTests();f.setUp();self.addCleanup(f.doCleanups)
        constraint = f.catalog.by_index[2]
        parameter = f.fixture.field('GameAction','ObjectProperty',0,8,0x8001000000294,
            property_class_index=constraint.index,property_class_serial=constraint.serial,
            property_class_address=hex(constraint.address),property_class_name=constraint.name)
        descriptor = f.descriptor([parameter],8);descriptor.owners = ({'index':7,'size':16},)
        planner = f.planner(descriptor);scope = Mock();scope.invocation_planner.return_value = planner
        _,call = paired._Provider().plan(scope,f.catalog,f.target,f.function,f.target)
        self.assertEqual(call._plan.wire_version,8)
        self.assertEqual(call._plan.objects[0].object,f.target)
        _blueprint_wire.encode_plan(call._plan)


if __name__ == '__main__':unittest.main()
