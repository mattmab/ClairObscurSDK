import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_conditions import StoryConditions
from expedition33.values import StoredMap

class CinematicSelectionTests(unittest.TestCase):
    def test_prepared_game_instance_uses_selected_identity_not_registry_discovery(self):
        gi=N(index=12,serial=34,address=56,class_name='BP_jRPG_GI_Custom_C',object_flags=0)
        obj=object.__new__(StoryConditions)
        obj.scope=N(pid=1,_check=Mock(),_session=N(_story_construction_resources=N(resources=N(gi=gi))))
        catalog=N(objects=[gi])
        # Empty history is sufficient to verify lookup routing and false default.
        history=object.__new__(StoredMap)
        object.__setattr__(history,'items',{})
        values=N(values={(12,'InteractedCinematics'):history},errors={},truncated=False)
        with patch('expedition33.story_conditions.capture_selected',return_value=catalog) as selected,patch('expedition33.catalog.capture_matching') as discovery,patch('expedition33.values.read_values_with_references',return_value=(values,catalog)):
            self.assertFalse(obj.played_cinematic('Opening',{}))
        selected.assert_called_once_with(1,((12,34,56),))
        discovery.assert_not_called()
