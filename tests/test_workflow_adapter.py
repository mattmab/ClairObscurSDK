import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from expedition33.catalog import CatalogObject

spec=importlib.util.spec_from_file_location('workflow_commands',Path(__file__).resolve().parents[1]/'scripts/cinematics_controller_commands.py')
adapter=importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)

class WorkflowAdapterTests(unittest.TestCase):
    def test_selector_is_freshly_validated_and_failure_clears_cache(self):
        obj=CatalogObject(1,2,3,65536,'Default__Actor','Actor','Class',4,-1,0,0,0)
        catalog=Mock(objects=[obj]); catalog.resolve.return_value=obj
        mod=Mock(); loader=Mock(); loader._loaded={'Cinematics':(None,mod)}
        with patch('expedition33.catalog.capture_matching',return_value=catalog) as matching, patch('expedition33.catalog.capture_selected',return_value=catalog) as selected:
            registry=adapter.commands(SimpleNamespace(pid=1),loader)
            handler=registry['sdk.object.lookup'].handler
            handler();handler()
            self.assertEqual(matching.call_count,1)
            selected.assert_called_once_with(1,((2,3,65536),))
            catalog.resolve.assert_called_once_with(obj)
            selected.side_effect=RuntimeError('identity changed')
            with self.assertRaisesRegex(RuntimeError,'identity changed'):handler()
            handler()
            self.assertEqual(matching.call_count,2)

    def test_catalog_is_bounded_and_arbitrary_execution_absent(self):
        mod=Mock();mod.discovery={'all':[{'id':str(i)} for i in range(155)]}
        loader=Mock();loader._loaded={'Cinematics':(None,mod)}
        registry=adapter.commands(SimpleNamespace(pid=1),loader)
        self.assertNotIn('py',registry);self.assertNotIn('exec',registry)
        catalog=registry['cinematics.catalog'].handler
        self.assertEqual(len(catalog()['rows']),20)
        for args in ({'limit':21},{'offset':-1},{'limit':True}):
            with self.assertRaises(ValueError):catalog(**args)
