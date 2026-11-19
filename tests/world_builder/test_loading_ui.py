import sys,types,unittest
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
package=types.ModuleType('loading_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from loading_test_builder.loading_ui import LoadingUI,UiProofPending,stabilize_tree,select_controller

class LoadingUITests(unittest.TestCase):
    def test_controller_discovery_uses_admitted_identity_during_title_transition(self):
        old=N(pid=7,index=1,serial=2,address=3,object_flags=0)
        current=N(pid=7,index=4,serial=5,address=6,object_flags=0)
        catalog=N(select=lambda kind:[old,current])
        self.assertIs(select_controller(catalog,(7,4,5,6)),current)
        with self.assertRaises(UiProofPending):select_controller(catalog,(7,8,9,10))
        with self.assertRaises(UiProofPending):select_controller(catalog)

    def test_zero_serial_tree_is_owned_and_rediscovered_before_children(self):
        old_tree=N(serial=0);stable=N(serial=1234)
        owner_class=N(index=12);current=object();fresh=object();metadata=object()
        panel=N(tree=old_tree,scope=N(pid=7),widget=object(),_class=Mock(return_value=owner_class),
                _planner=Mock(),_functions={'old':1},_defaults={'old':1})
        discover=Mock()
        with patch('expedition33._stable_lease.stabilize_owned_tree',return_value=(stable,None)) as acquire, \
             patch('expedition33._stable_lease.rediscover_owned_tree',return_value=(metadata,stable,fresh)) as refresh:
            stabilize_tree(panel,current,discover)
        acquire.assert_called_once_with(panel.scope,current,panel.widget,old_tree,owner_class)
        refresh.assert_called_once_with(7,discover,panel.widget,stable,12)
        self.assertIs(panel.tree,stable)
        self.assertFalse(panel._functions);self.assertFalse(panel._defaults)
        panel._planner.refresh_from.assert_called_once_with(metadata)
        panel._planner.adopt_observations.assert_called_once_with(fresh)

    def test_already_stable_tree_does_not_acquire_again(self):
        panel=N(tree=N(serial=1234),_planner=Mock())
        current=object()
        with patch('expedition33._stable_lease.stabilize_owned_tree') as acquire:
            stabilize_tree(panel,current,Mock())
        acquire.assert_not_called()
        panel._planner.adopt_observations.assert_called_once_with(current)

    def test_discovery_failure_resumes_same_owner_before_any_widget_build(self):
        from expedition33 import RuntimeQueryError
        mod=N(session=object(),help_minimized=False)
        scope=N(pid=7,_closed=False,close=Mock())
        hud=Mock(state='new');catalog=Mock(state='new')
        catalog.discover.side_effect=[RuntimeQueryError('GC'),None]
        with patch('loading_test_builder.loading_ui.SessionScope',return_value=scope), \
             patch('loading_test_builder.loading_ui.ReadBatch',side_effect=lambda pid,**options:nullcontext()), \
             patch('loading_test_builder.loading_ui.prepare_panel_metadata'), \
             patch('loading_test_builder.library.Library') as library, \
             patch('loading_test_builder.hud.BuilderHUD',return_value=hud) as make_hud, \
             patch('loading_test_builder.catalog_menu.CatalogMenu',return_value=catalog) as make_catalog, \
             patch('loading_test_builder.loading_ui.OwnedUiProof',side_effect=(Mock(),Mock())):
            owner=LoadingUI(mod,object());title=N(kind='title',signature=('title',1))
            with self.assertRaises(UiProofPending):owner.prepare(title)
            self.assertTrue(owner.preparation_pending)
            hud.build.assert_not_called();catalog.build.assert_not_called()
            owner.observe_title(title)
            self.assertFalse(owner.preparation_pending)
            self.assertEqual(owner.bound,title.signature)
            hud.build.assert_called_once();catalog.build.assert_called_once()
            library.assert_called_once();make_hud.assert_called_once();make_catalog.assert_called_once()

    def test_cold_menu_discovery_never_requests_full_asset_scan(self):
        from expedition33 import RuntimeQueryError
        from loading_test_builder.catalog_menu import CatalogMenu,MENU_NAMES
        menu=CatalogMenu.__new__(CatalogMenu)
        menu.mod=N(session=N(pid=7));menu.library=Mock(registry_complete=False)
        with patch('loading_test_builder.catalog_menu.capture') as full, \
             patch('loading_test_builder.catalog_menu.capture_matching',side_effect=RuntimeQueryError('GC')) as bounded:
            with self.assertRaises(RuntimeQueryError):menu.discover()
        full.assert_not_called();menu.library.refresh.assert_not_called()
        bounded.assert_called_once_with(7,names=sorted(MENU_NAMES),classes=('PlayerController','GameEngine'))

    def test_fast_title_transition_retains_built_widgets_for_world_handoff(self):
        original=object();mod=N(session=original,help_minimized=False)
        scope=N(pid=7,_closed=False,close=Mock())
        hud=Mock(state='new');catalog=Mock(state='new')
        first=Mock();second=Mock();first.verify.side_effect=UiProofPending('title ended')
        with patch('loading_test_builder.loading_ui.SessionScope',return_value=scope), \
             patch('loading_test_builder.loading_ui.ReadBatch',side_effect=lambda pid,**options:nullcontext()), \
             patch('loading_test_builder.loading_ui.prepare_panel_metadata'), \
             patch('loading_test_builder.library.Library'), \
             patch('loading_test_builder.hud.BuilderHUD',return_value=hud), \
             patch('loading_test_builder.catalog_menu.CatalogMenu',return_value=catalog), \
             patch('loading_test_builder.loading_ui.OwnedUiProof',side_effect=(first,second)):
            owner=LoadingUI(mod,object());title=N(kind='title',signature=('title',1));owner.prepare(title)
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
