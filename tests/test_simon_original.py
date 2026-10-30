from contextlib import contextmanager
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import simon_original as simon
from expedition33 import simon_source as source
from expedition33.values import StoredMap, StoredStruct


class Scope:
    pid = 123
    def __init__(self): self.closed = False
    def _check(self):
        if self.closed: raise RuntimeError('scope closed')
    def close(self): self.closed = True


class Provider:
    def __init__(self):
        self.scope = Scope()
        self.current = dict(controller=(123,1,2,0x10000),world=(123,2,3,0x20000),world_path=source.WORLD)
        self.current_history = dict(decoded=True,read_error=None,selected_slot=1,
            context_identities=dict(world=self.current['world']),history=StoredMap({}))
        self.loaded = []
        self.monitor_value = SimpleNamespace(idle=True)
        self.monitor_object = Mock()
        self.monitor_object.observe.side_effect = lambda:self.monitor_value
        self.planner = Mock()
        self.call = Mock()
        self.invocations = 0
        self.invoke_error = None
        self.dependency_error = None
        self.dependency_checks = 0
        @contextmanager
        def invoke():
            self.invocations += 1
            if self.invoke_error is not None: raise self.invoke_error
            yield None
        self.call.invoke.side_effect = invoke
    def child(self,scope): return self.scope
    def context(self,scope): return dict(self.current)
    def history(self,scope): return self.current_history
    def services(self,scope,context): return ('catalog','executor','cinematic','function')
    def load(self,scope,path):
        self.loaded.append(path)
        return SimpleNamespace(return_value=path)
    def observations(self,*args): return 'catalog'
    def graph(self,catalog,root): return 'graph',catalog
    def dependencies(self,scope,catalog,*args):
        self.dependency_checks += 1
        if self.dependency_error is not None: raise self.dependency_error
        return catalog
    def monitor(self,*args): return self.monitor_object
    def plan(self,*args): return self.planner,self.call


class SimonOriginalTests(unittest.TestCase):
    def setUp(self):
        self.scope = Scope()
        self.provider = Provider()
    def prepare(self):
        return simon.prepare(self.scope,disposable_test=True,_provider=self.provider)

    def test_requires_explicit_disposable_setup_before_preparation(self):
        with self.assertRaisesRegex(RuntimeError,'disposable'):
            simon.prepare(self.scope,_provider=self.provider)
        self.assertEqual(self.provider.loaded,[])

    def test_original_world_only_and_no_travel(self):
        self.provider.current['world_path'] = '/Game/Other.Other'
        with self.assertRaisesRegex(RuntimeError,'exact original world'):
            self.prepare()
        self.assertEqual(self.provider.loaded,[])
        self.assertTrue(self.provider.scope.closed)

    def test_already_played_history_preserves_original_policy(self):
        for cinematic_id in ('SimonIntro','SimonPhaseTransition','SimonOutro'):
            with self.subTest(cinematic_id=cinematic_id):
                self.provider = Provider()
                history = StoredMap({cinematic_id:True})
                self.provider.current_history['history'] = history
                prepared = self.prepare()
                self.addCleanup(prepared.close)
                prepared.start()
                self.assertIs(self.provider.current_history['history'],history)
                self.assertEqual(self.provider.invocations,1)
                self.assertEqual(prepared.status()['repeat_policy'],'original')
                self.assertFalse(prepared.status()['repeat_verified'])

    def test_loads_exact_graph_and_three_original_sequences(self):
        prepared = self.prepare()
        self.assertEqual(self.provider.loaded,[source.ROOT] + [stage.sequence for stage in source.STAGES if stage.sequence])
        self.assertFalse(prepared.dispatch_attempted)
        self.assertEqual(self.provider.invocations,0)
        self.assertTrue(prepared.status()['includes_campaign_tail'])
        prepared.close()
        self.assertTrue(self.provider.scope.closed)

    def test_busy_or_unprovable_dependencies_fail_without_dispatch(self):
        self.provider.monitor_value.idle = False
        with self.assertRaisesRegex(RuntimeError,'busy'):
            self.prepare()
        self.assertEqual(self.provider.invocations,0)
        self.provider = Provider()
        def unsupported(*unused):
            raise simon.UnsupportedSimonDependency('SequenceToPlay SoftObjectProperty unsupported')
        self.provider.dependencies = unsupported
        with self.assertRaisesRegex(simon.UnsupportedSimonDependency,'SoftObjectProperty'):
            self.prepare()
        self.assertEqual(self.provider.invocations,0)
        self.assertTrue(self.provider.scope.closed)

    def test_start_revalidates_context_history_and_idle(self):
        prepared = self.prepare()
        self.provider.current['controller'] = (123,99,1,0x99999)
        with self.assertRaisesRegex(RuntimeError,'changed before dispatch'):
            prepared.start()
        self.assertEqual(self.provider.invocations,0)
        self.assertFalse(prepared.dispatch_attempted)

    def test_one_shot_full_root_dispatch_and_observation_only(self):
        prepared = self.prepare()
        prepared.start()
        self.assertEqual(self.provider.dependency_checks,2)
        self.assertEqual(self.provider.invocations,1)

        with self.assertRaisesRegex(RuntimeError,'one-shot'):
            prepared.start()
        self.provider.monitor_value.idle = False
        self.assertEqual(prepared.poll()['state'],'original_graph_active')
        self.provider.monitor_value.idle = True
        status = prepared.poll()
        self.assertEqual(status['state'],'idle_after_activity')
        self.assertFalse(status['completion_proved'])
        self.assertFalse(status['visibility_proved'])
        self.assertEqual(self.provider.invocations,1)

    def test_arena_dependency_rechecked_immediately_before_dispatch(self):
        prepared = self.prepare()
        self.provider.dependency_error = RuntimeError('arena unloaded')
        with self.assertRaisesRegex(RuntimeError,'arena unloaded'):
            prepared.start()
        self.assertFalse(prepared.dispatch_attempted)
        self.assertEqual(self.provider.invocations,0)

    def test_unknown_dispatch_is_not_replayed_or_reclassified_by_idle(self):
        prepared = self.prepare()
        self.provider.invoke_error = RuntimeError('ack lost')
        with self.assertRaisesRegex(RuntimeError,'ack lost'):
            prepared.start()
        self.provider.monitor_value.idle = False
        self.assertEqual(prepared.poll()['state'],'unknown')
        self.provider.monitor_object.observe.side_effect = RuntimeError('old world')
        self.assertEqual(prepared.poll()['state'],'unknown')
        with self.assertRaises(RuntimeError): prepared.start()
        self.assertEqual(self.provider.invocations,1)

    def test_close_only_releases_own_scope_and_observations(self):
        prepared = self.prepare()
        prepared.start()
        prepared.close(); prepared.close()
        self.provider.planner.close.assert_called_once()
        self.provider.monitor_object.close.assert_called_once()
        self.assertEqual(self.provider.invocations,1)
        self.assertEqual(prepared.state,'closed')

    def test_only_explicit_blueprint_planner_is_used(self):
        scope = Mock()
        planner = scope.invocation_planner.return_value
        out = simon._Provider().plan(scope,'catalog','executor','function','root')
        planner.prepare_blueprint.assert_called_once_with('executor','function',GameAction='root')
        planner.prepare.assert_not_called()
        self.assertEqual(out,(planner,planner.prepare_blueprint.return_value))

    def test_missing_stored_dependency_fails_with_exact_field(self):
        stored = StoredStruct(None,{}, {'SequenceToPlay_x':'STRUCT_MEMBER_TYPE_UNSUPPORTED'},
                              {'SequenceToPlay_x':'SoftObjectProperty'},False)
        with self.assertRaisesRegex(simon.UnsupportedSimonDependency,'SequenceToPlay_x.*SoftObjectProperty'):
            simon._member(stored,'SequenceToPlay_','SoftObjectProperty')

    def test_executor_argument_uses_real_explicit_blueprint_codec(self):
        import test_blueprint_invocation
        from expedition33 import _blueprint_wire
        fixture = test_blueprint_invocation.BlueprintInvocationTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        constraint = fixture.catalog.by_index[2]
        parameter = fixture.fixture.field('GameAction','ObjectProperty',0,8,
            0x8001000000294, property_class_index=constraint.index,
            property_class_serial=constraint.serial,property_class_address=hex(constraint.address),
            property_class_name=constraint.name)
        descriptor = fixture.descriptor([parameter],8)
        descriptor.owners = ({'index':7,'size':16},)
        planner = fixture.planner(descriptor)
        scope = Mock()
        scope.invocation_planner.return_value = planner
        _,call = simon._Provider().plan(scope,fixture.catalog,fixture.target,
                                       fixture.function,fixture.target)
        self.assertEqual(call._plan.wire_version,8)
        self.assertEqual(call._plan.parameter_size,8)
        self.assertEqual(call._plan.allocation_extent,16)
        self.assertEqual(call._plan.objects[0].object,fixture.target)
        _blueprint_wire.encode_plan(call._plan)

    def test_soft_path_requires_typed_native_copy(self):
        from expedition33.values import StoredSoftObjectPath
        package = '/Game/Cinematics/Simon/SimonIntro/MCS_SimonIntro'
        typed = StoredSoftObjectPath(package,'MCS_SimonIntro','')
        self.assertEqual(simon._soft_path(typed,'intro'),package+'.MCS_SimonIntro')
        with self.assertRaises(simon.UnsupportedSimonDependency):
            simon._soft_path(package+'.MCS_SimonIntro','intro')

    def test_transition_uses_actual_byte_enum_identity_and_membership(self):
        from expedition33.enums import EnumMember
        obj = SimpleNamespace(index=20,serial=1,address=0x20000)
        enum = SimpleNamespace(index=21)
        value = StoredStruct(obj,{simon.TRANSITION_FIELD:2},{},
                             {simon.TRANSITION_FIELD:'ByteProperty'},False)
        catalog = Mock(pid=123)
        catalog.path_name.return_value = simon.TRANSITION_STRUCT
        selected_catalog = Mock(by_index={21:enum})
        selected_catalog.path_name.return_value = simon.TRANSITION_ENUM
        selected = SimpleNamespace(catalog=selected_catalog,
            descriptors={20:SimpleNamespace(properties=[dict(name=simon.TRANSITION_FIELD,
                                      type='ByteProperty',enum_index=21)])})
        with patch('expedition33.reflection.describe_selected',return_value=selected) as describe, \
             patch('expedition33.enums.describe_enums',return_value={21:SimpleNamespace(members=(EnumMember('ToBattle',2),))}):
            simon._validate_transition(catalog,value)
            describe.assert_called_once_with(123,((20,1,0x20000),))
            selected_catalog.path_name.return_value = '/Game/Other.Other'
            with self.assertRaisesRegex(RuntimeError,'enum identity'):
                simon._validate_transition(catalog,value)
        with self.assertRaisesRegex(RuntimeError,'value differs'):
            simon._validate_transition(catalog,replace(value,fields={simon.TRANSITION_FIELD:True}))
