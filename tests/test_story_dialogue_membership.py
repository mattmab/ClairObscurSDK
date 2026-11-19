import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.story_dialogue import controller_dialogue_system


class ControllerDialogueMembershipTests(unittest.TestCase):
    def fixture(self):
        system=N(index=9,serial=2,address=0x90000,class_name='BP_DialogueSystemComponent_C',
                 outer_index=8,outer_serial=3,object_flags=0)
        owner=N(index=8,object_flags=0)
        key=(1,'BP_DialogueSystemComponent')
        value=N(types={key:'ObjectProperty'},values={key:system},errors={},truncated=False)
        return N(by_index={8:owner}),value,system,key

    def test_reads_current_component_each_time_without_world_scan(self):
        catalog,value,system,key=self.fixture()
        with patch('expedition33.values.capture_selected_values',return_value=(catalog,{8:value})) as read,\
                patch('expedition33.catalog.capture_matching',side_effect=AssertionError('Global scan')):
            self.assertIs(controller_dialogue_system(99,[8,3,0x80000])[1],system)
            other=N(**vars(system));other.index=10;other.address=0xa0000
            value.values[key]=other
            self.assertIs(controller_dialogue_system(99,(8,3,0x80000))[1],other)
            self.assertEqual(read.call_count,2)

    def test_stale_foreign_retired_missing_and_partial_membership_fail(self):
        for case in ('serial','outer','retired','class','null','owner','errors','truncated','missing'):
            with self.subTest(case=case):
                catalog,value,system,key=self.fixture()
                if case=='serial':system.outer_serial=4
                elif case=='outer':system.outer_index=7
                elif case=='retired':system.object_flags=0x20
                elif case=='class':system.class_name='OtherComponent'
                elif case=='null':value.values[key]=None
                elif case=='owner':catalog.by_index[8].object_flags=0x10
                elif case=='errors':value.errors[key]='unavailable'
                elif case=='truncated':value.truncated=True
                else:value.values.clear()
                with patch('expedition33.values.capture_selected_values',return_value=(catalog,{8:value})):
                    with self.assertRaises(RuntimeQueryError):controller_dialogue_system(99,(8,3,0x80000))


if __name__=='__main__':unittest.main()
