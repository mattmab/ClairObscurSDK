import unittest
from dataclasses import dataclass
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from contextlib import nullcontext
from expedition33.enums import EnumValue
import title_timing_probe as module
from expedition33.values import StoredStruct

class TimingProbeTests(unittest.TestCase):
    def test_copied_struct_preserves_fields_errors_and_limits(self):
        @dataclass
        class Type: name:str
        value=StoredStruct(Type('Settings'),{'bTickWhenPaused':True},{'NativeClock':'unsupported'}, {},False)
        result=module.copied_json(value)
        self.assertEqual(result['dataclass'],'StoredStruct')
        self.assertEqual(result['fields']['entries'][0]['value'],True)
        self.assertEqual(result['errors']['entries'][0]['value'],'unsupported')
        self.assertEqual(module.copied_json([[[1]]],budget=[1])['items'][0],{'unknown':'serialization bound reached'})
        self.assertTrue(module.copied_json(list(range(200)))['truncated'])

    def test_schema_precedes_stored_read_and_opaque_field_is_unknown(self):
        obj=N(class_index=2);cls=N(index=2);events=[]
        catalog=N(by_index={2:cls,20:N(index=20,serial=2,address=200,name='Settings')},pid=1)
        props=[dict(owner='Player',owner_index=2,name='PlaybackSettings',type='StructProperty',struct_index=20,struct_serial=2,struct_name='Settings'),
               dict(owner='Player',owner_index=2,name='DurationFrames',type='IntProperty')]
        def describe(*args):events.append('describe');return {2:N(properties=props)}
        def read(*args):events.append('read');return N(values={(2,'DurationFrames'):12},errors={(2,'PlaybackSettings'):'unsupported'},truncated=set())
        with patch.object(module,'describe',side_effect=describe),patch.object(module,'read_values',side_effect=read),patch.object(module,'_enrich_structs',side_effect=lambda c,p:(c,[])):
            result=module._sample(catalog,obj)
        self.assertEqual(events,['describe','read'])
        self.assertEqual(result['values'][0]['unknown'],'unsupported')
        self.assertEqual(result['values'][1]['value'],12)
        self.assertIn('does not prove time advancement',result['unknowns'][0])

    def test_missing_descriptor_does_not_guess_values(self):
        with patch.object(module,'describe',side_effect=RuntimeError('sparse dependency')),patch.object(module,'read_values') as read:
            result=module._sample(N(by_index={2:N(index=2)}),N(class_index=2))
        read.assert_not_called()
        self.assertIn('sparse dependency',result['unknowns'][0])

    def test_only_owned_objects_and_exact_asset_chain_are_followed(self):
        obj=lambda i:N(index=i,serial=2,address=1000+i,class_index=10,class_name='MovieScene')
        player,actor,asset,movie=map(obj,range(1,5))
        owners={'MovieSceneSequencePlayer':N(index=10),'LevelSequence':N(index=11)}
        catalog=N(by_index={10:owners['MovieSceneSequencePlayer'],11:owners['LevelSequence']},objects=[],with_observations=lambda _:catalog,find_class=lambda name:owners[name],path_name=lambda _:module.SEQUENCE)
        scope=N(pid=5,_check=Mock(),_session=N(_transport=N(button_action_session=42)))
        sequence=N(scope=scope,player=player,actor=actor,uncertain=False,state='playing')
        mod=N(title_replay=N(sequence=sequence))
        with patch.object(module,'capture_matching',return_value=catalog),patch.object(module,'capture_selected') as selected,patch.object(module,'_sample',return_value={}),patch.object(module,'read_object_reference',side_effect=[(asset,catalog),(movie,catalog)]) as reference:
            result=module.inspect_title_timing(mod)
        self.assertEqual(set(result['objects']),{'player','actor','asset','movie_scene'})
        self.assertEqual(reference.call_args_list[0].args[1:],(player,owners['MovieSceneSequencePlayer'],'Sequence'))
        self.assertEqual(reference.call_args_list[1].args[1:],(asset,owners['LevelSequence'],'MovieScene'))
        self.assertEqual(len(selected.call_args_list[-1].args[1]),4)
        self.assertFalse(result['atomic'])

    def test_nested_struct_dependencies_are_selected_before_values_without_retry(self):
        outer=N(index=20,serial=2,address=200,name='Settings')
        inner=N(index=21,serial=3,address=300,name='TickSettings')
        catalog=N(pid=1,by_index={20:outer,21:inner},with_observations=lambda _:catalog)
        root=dict(type='StructProperty',struct_index=20,struct_serial=2,struct_name='Settings')
        nested=dict(type='StructProperty',struct_index=21,struct_serial=3,struct_name='TickSettings')
        with patch.object(module,'capture_selected') as selected,patch.object(module,'describe',side_effect=[{20:N(properties=[nested])},{21:N(properties=[])}]) as described:
            result,errors=module._enrich_structs(catalog,[root])
        self.assertEqual(errors,[])
        self.assertEqual([c.args[1] for c in selected.call_args_list],[((20,2,200),),((21,3,300),)])
        self.assertEqual(described.call_count,2)

class ClockGetterTests(unittest.TestCase):
    def fixture(self):
        enum=N(index=3,serial=4)
        fn=N(index=2,outer_index=1,name='GetClockSource',class_name='Function')
        catalog=N(find_class=lambda _:N(index=1),objects=[fn],by_index={3:enum})
        prop=dict(flags=0x480,type='EnumProperty',enum_name='EUpdateClockSource',enum_index=3,enum_serial=4)
        planner=N(prepare=Mock(return_value=N(invoke=Mock(return_value=nullcontext(N(return_value=EnumValue(enum,'Tick',0)))))),close=Mock())
        scope=N(invocation_planner=Mock(return_value=planner))
        return enum,catalog,prop,planner,scope

    def test_absent_reflected_getter_has_no_invocations(self):
        enum,catalog,prop,planner,scope=self.fixture();catalog.objects=[]
        result=module.inspect_clock_source(scope,catalog,object())
        self.assertFalse(result['invoked'])
        scope.invocation_planner.assert_not_called()

    def test_exact_enum_getter_validates_membership_and_closes_planner(self):
        enum,catalog,prop,planner,scope=self.fixture()
        with patch.object(module,'describe',return_value={2:N(properties=[prop])}),patch.object(module,'describe_enums',return_value={3:N(members=[N(name='Tick',value=0)])}):
            result=module.inspect_clock_source(scope,catalog,object())
        self.assertTrue(result['invoked'])
        self.assertEqual(result['names'],['Tick'])
        planner.close.assert_called_once()

    def test_getter_with_arguments_is_not_dispatched(self):
        enum,catalog,prop,planner,scope=self.fixture()
        with patch.object(module,'describe',return_value={2:N(properties=[prop,prop])}):
            result=module.inspect_clock_source(scope,catalog,object())
        self.assertFalse(result['invoked'])
        scope.invocation_planner.assert_not_called()

class CurrentTimeGetterTests(unittest.TestCase):
    def fixture(self,numerator=24):
        fn=N(index=2,outer_index=1,name='GetCurrentTime',class_name='Function')
        catalog=N(find_class=lambda _:N(index=1),objects=[fn])
        prop=dict(flags=0x480,type='StructProperty',struct_name='QualifiedFrameTime')
        value=object.__new__(module.NumericStructValue)
        object.__setattr__(value,'path','/Script/CoreUObject.QualifiedFrameTime')
        object.__setattr__(value,'_fields',{'Time':{'FrameNumber':{'Value':48},'SubFrame':0.5},'Rate':{'Numerator':numerator,'Denominator':1}})
        invoke=Mock(return_value=nullcontext(N(return_value=value)))
        planner=N(prepare=Mock(return_value=N(invoke=invoke)),close=Mock())
        scope=N(_session=N(_transport=N(frame_time_values_protocol=1)),supports_frame_time_values=True,invocation_planner=Mock(return_value=planner))
        return catalog,prop,planner,scope,invoke

    def test_protocol_gate_never_dispatches_on_old_runtime(self):
        catalog,prop,planner,scope,invoke=self.fixture()
        for version in (0,True,2):
            scope._session._transport.frame_time_values_protocol=version
            self.assertFalse(module.inspect_current_time(scope,catalog,object())['invoked'])
        invoke.assert_not_called();scope.invocation_planner.assert_not_called()

    def test_copied_frame_time_and_seconds(self):
        catalog,prop,planner,scope,invoke=self.fixture()
        with patch.object(module,'describe',return_value={2:N(properties=[prop])}):
            result=module.inspect_current_time(scope,catalog,object())
        self.assertTrue(result['invoked']);self.assertAlmostEqual(result['seconds'],48.5/24)
        planner.close.assert_called_once()

    def test_zero_rate_is_reported_without_inventing_seconds(self):
        catalog,prop,planner,scope,invoke=self.fixture(0)
        with patch.object(module,'describe',return_value={2:N(properties=[prop])}):
            result=module.inspect_current_time(scope,catalog,object())
        self.assertTrue(result['invoked']);self.assertNotIn('seconds',result)
        self.assertIn('seconds_unknown',result)

    def test_arguments_reject_before_dispatch(self):
        catalog,prop,planner,scope,invoke=self.fixture()
        with patch.object(module,'describe',return_value={2:N(properties=[prop,prop])}):
            result=module.inspect_current_time(scope,catalog,object())
        self.assertFalse(result['invoked']);invoke.assert_not_called()

if __name__=='__main__':unittest.main()
