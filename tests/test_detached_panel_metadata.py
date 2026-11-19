import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import ui_shell_proof as proof

class DetachedMetadataTests(unittest.TestCase):
    def test_game_instance_class_is_rediscovered_and_retired_controller_is_excluded(self):
        function=N(index=1,serial=0,class_name='Function')
        instance_class=N(index=2,serial=0,class_name='Class')
        stable_function=N(index=1,serial=1234,class_name='Function')
        stable_class=N(index=2,serial=2345,class_name='Class')
        catalog=Mock(objects=[function,instance_class]);catalog.subset.return_value=catalog
        session=N(_menu_schema_observations={})
        scope=N(pid=7,_session=session,_leases=[],invocation_planner=Mock(return_value=Mock()))
        panel=N(scope=scope,_planner=Mock(_catalog=catalog),_functions={},_defaults={},
                widget=object(),tree=object(),canvas=object(),player=object())
        owner=Mock();owner.prepare.return_value=N(by_index={1:stable_function})
        def admitted(c,o):
            if o is function:return o
            raise ValueError('outside whitelist')
        with patch('expedition33._metadata_stabilization.script_function',side_effect=admitted), \
             patch('expedition33._metadata_stabilization.process_preparation',return_value=owner), \
             patch.object(proof,'refresh_panel_metadata',return_value=(stable_class,)) as refresh, \
             patch('expedition33._stable_lease.fresh_catalog_replacing',return_value=object()) as recapture:
            proof.prepare_panel_metadata(panel)
        refresh.assert_called_once_with(7,(instance_class,))
        self.assertEqual(recapture.call_args.args[1],(stable_function,stable_class))
        self.assertNotIn(panel.player,catalog.subset.call_args.args[0])

