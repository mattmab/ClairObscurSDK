import sys,types,unittest
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
package=types.ModuleType('loading_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from loading_test_builder.loading_ui import LoadingUI,UiProofPending

class LoadingUITests(unittest.TestCase):
    def test_fast_title_transition_retains_built_widgets_for_world_handoff(self):
        original=object();mod=N(session=original,help_minimized=False)
        scope=N(pid=7,_closed=False,close=Mock())
        hud=Mock(state='built');catalog=Mock(state='built')
        first=Mock();second=Mock();first.verify.side_effect=UiProofPending('title ended')
        with patch('loading_test_builder.loading_ui.SessionScope',return_value=scope), \
             patch('loading_test_builder.loading_ui.ReadBatch',side_effect=lambda pid,**options:nullcontext()), \
             patch('loading_test_builder.loading_ui.prepare_panel_metadata'), \
             patch('loading_test_builder.library.Library'), \
             patch('loading_test_builder.hud.BuilderHUD',return_value=hud), \
             patch('loading_test_builder.catalog_menu.CatalogMenu',return_value=catalog), \
             patch('loading_test_builder.loading_ui.OwnedUiProof',side_effect=(first,second)):
            owner=LoadingUI(mod,object());title=object();owner.prepare(title)
        self.assertIs(mod.session,original);self.assertIs(owner.context,title)
        hud.build.assert_called_once();catalog.build.assert_called_once()
        self.assertIsNone(owner.bound)
        first.verify.side_effect=None
        world=N(signature=('world',1))
        with patch('loading_test_builder.loading_ui.ReadBatch',side_effect=lambda pid,**options:nullcontext()):
            owner.bind(world,preparing=True)
        self.assertEqual(owner.bound,world.signature)
        first.verify.assert_called_with(catalog,world,rebind=True,preparing=True)
        second.verify.assert_called_once_with(hud,world,rebind=True,preparing=True)
        owner.bind(world)
        self.assertEqual(second.verify.call_count,1)

if __name__=='__main__':unittest.main()
