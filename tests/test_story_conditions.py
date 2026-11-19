import unittest
from unittest.mock import patch
from types import SimpleNamespace
from expedition33.story_conditions import StoryConditions

class StoryConditionTests(unittest.TestCase):
    def test_cinematic_gate_reads_saved_history_without_writing_flags(self):
        from expedition33.values import StoredMap
        gi=SimpleNamespace(class_name='BP_jRPG_GI_Custom_C',object_flags=0)
        owner=object.__new__(StoryConditions);owner.scope=SimpleNamespace(pid=42,_check=lambda:None,_session=SimpleNamespace())
        c=SimpleNamespace(objects=(gi,))
        values=SimpleNamespace(errors={},truncated=set(),values={(1,'InteractedCinematics'):StoredMap({'LuneArrives':True})})
        with patch('expedition33.catalog.capture_matching',return_value=c),patch('expedition33.values.read_values_with_references',return_value=(values,c)):
            self.assertTrue(owner.played_cinematic('LuneArrives',{'visit':(1,2,3)}))
            self.assertFalse(owner.played_cinematic('OtherCinematic',{'visit':(1,2,3)}))
            values.errors={'history':'incomplete'}
            with self.assertRaises(RuntimeError):owner.played_cinematic('LuneArrives',{'visit':(1,2,3)})

if __name__=='__main__':unittest.main()
