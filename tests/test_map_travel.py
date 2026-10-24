import contextlib
import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('map_travel_mod', ROOT / 'mods/MapTravel/mod.py', submodule_search_locations=[str(ROOT / 'mods/MapTravel')])
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


class MapTravelTests(unittest.TestCase):
    def test_arrival_does_not_attach_destination_button_to_retiring_scope(self):
        model=mod.Mod()
        model.native=Mock()
        model.request=SimpleNamespace(state='arrived',destination={'title':'Destination'},error=None)
        model.native.parent.travel_recovery=model.request
        model._new_pause_entry=Mock()
        model._finish()
        model._new_pause_entry.assert_not_called()
        self.assertIsNone(model.pause)
        self.assertIsNone(model.native.parent.travel_recovery)

    def test_pause_entry_uses_copied_host_readiness_and_keeps_legacy_default(self):
        from types import SimpleNamespace
        model=mod.Mod();model.native=object()
        ready=lambda:None
        for provider,expected in ((ready,ready),(False,None),(None,None)):
            model.session=SimpleNamespace(_session=SimpleNamespace(_menu_readiness=provider))
            with patch.object(mod,'PauseMenuEntry') as entry:
                model._new_pause_entry()
            self.assertIs(entry.call_args.kwargs['readiness'],expected)
            self.assertEqual(entry.call_args.kwargs['label'],'Map Travel')

    def test_route_rejection_keeps_sdk_and_menu_alive(self):
        model = mod.Mod()
        model.native = Mock()
        model.native.parent.travel_recovery_pending = False
        model.maps = [dict(package='test', title='Test', normal_route={'level_id':'Test'})]
        error = mod.InvocationError('rejected', outcome='not_dispatched', native_error=1810)
        with patch.object(mod, 'travel_to_entrance', side_effect=error) as dispatch:
            model.travel('test')
        dispatch.assert_called_once()
        model.native.parent.dispose_menu.assert_not_called()
        self.assertFalse(model.pending_open)
        self.assertIn('entrance route rejected', model.message)
        self.assertIsNone(model.request)


    def test_process_shell_travel_detaches_without_destroying_reusable_widgets(self):
        from types import SimpleNamespace as N
        model=mod.Mod();request=Mock(state='new')
        parent=N(travel_recovery_pending=False,menu=Mock(),prepare_travel=Mock(),dispose_menu=Mock())
        model.native=N(parent=parent);model.session=object();model.pause=Mock()
        model.maps=[dict(package='test',title='Test',normal_route={'level_id':'Test'})]
        with patch.object(mod,'travel_to_entrance'),patch.object(mod,'Travel',return_value=request):model.travel('test')
        parent.prepare_travel.assert_called_once();parent.dispose_menu.assert_not_called()
        parent.menu.panel.close_owned_tree.assert_not_called();request.start.assert_called_once()
        self.assertIs(parent.travel_recovery,request)

    def test_catalog_excludes_streaming_and_non_gameplay_maps(self):
        rows = mod.installed_maps([
            'Sandfall/Content/Levels/OrangeForest/Level_OraneForest_Main.umap\tdate',
            'Sandfall/Content/Levels/OrangeForest/Level_OraneForest_Main.umap\tdate',
            'Sandfall/Content/Levels/OrangeForest/_Generated_/CELL.umap\tdate',
            'Sandfall/Content/Levels/UI/MainMenu/Level_MainMenu.umap\tdate',
            'Sandfall/Content/Levels/Map_Game_Bootstrap.umap\tdate',
            'Engine/Content/Maps/Entry.umap\tdate'])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['title'], 'Orange Forest')
        self.assertTrue(rows[0]['world_path'].endswith('.Level_OraneForest_Main'))

    def test_installed_catalog_covers_cinematic_destinations(self):
        from expedition33.cinematics.original_game_action import profiles
        manifest = ROOT / 'Manifest_UFSFiles_Win64.txt'
        if not manifest.exists():
            self.skipTest('Installed game manifest required; covered by live validation')
        with manifest.open() as stream:
            rows = mod.installed_maps(stream)
        packages = {row['package'] for row in rows}
        self.assertTrue({row['exact_map'] for row in profiles().values()} <= packages)
        self.assertGreater(len(packages), 50)

    def context(self, identity, world='world'):
        return dict(controller=identity, world_path=world)

    def request(self):
        return mod.Travel(Mock(), dict(package='/Game/Levels/Test', world_path='world', title='Test', normal_route={'level_id':'Test'}))

    def poll(self, request):
        request.next_poll = 0
        request.poll()

    def test_travel_dispatches_once_and_arrives_after_one_load(self):
        request = self.request()
        with patch.object(mod, 'controller_context', return_value=self.context(1)) as context, \
             patch.object(mod, 'ReadBatch', side_effect=lambda *a, **k: contextlib.nullcontext()), \
             patch.object(mod, 'travel_to_entrance') as travel, patch.object(mod, 'ready_history'):
            request.start()
            self.poll(request)
            self.assertEqual(request.state, 'traveling')
            context.return_value = self.context(2, 'wrong')
            self.poll(request)
            self.assertEqual(request.state, 'traveling')
            context.return_value = self.context(2)
            self.poll(request)
            self.assertEqual(request.state, 'arrived')
            self.poll(request)
            travel.assert_called_once_with(request.session, request.destination['normal_route'])
            request.session.console.execute.assert_not_called()

    def test_arrival_observation_uses_process_owner_after_mod_scope_retirement(self):
        from types import SimpleNamespace as N
        root=N(pid=7);scope=N(pid=7,_session=root)
        request=mod.Travel(scope,dict(world_path='destination'))
        request.state='traveling';request.deadline=float('inf');request.before={'controller':1}
        with patch.object(mod,'ReadBatch',side_effect=lambda *a,**k:contextlib.nullcontext()), \
             patch.object(mod,'controller_context',return_value=self.context(2,'destination')) as observe, \
             patch.object(mod,'ready_history') as history:
            request.poll()
        self.assertEqual(request.state,'arrived');history.assert_called_once_with(root)
        self.assertTrue(all(call.args==(root,) for call in observe.call_args_list))

    def test_arrival_poll_borrows_host_read_operation_instead_of_nesting_owner(self):
        request=self.request();request.state='traveling';request.deadline=float('inf');request.before={'controller':1}
        with patch.object(mod,'active_reader',return_value=object()), \
             patch.object(mod,'ReadBatch',side_effect=lambda *a,**k:contextlib.nullcontext()) as batches, \
             patch.object(mod,'controller_context',return_value=self.context(1)):
            request.poll()
        self.assertFalse(batches.call_args.kwargs['share']);self.assertEqual(request.state,'traveling')

    def test_loading_descriptor_race_keeps_arrival_pending_without_redispatch(self):
        request=self.request();request.state='traveling';request.deadline=float('inf')
        with patch.object(mod,'ReadBatch',side_effect=lambda *a,**k:contextlib.nullcontext()), \
             patch.object(mod,'controller_context',side_effect=mod.RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')), \
             patch.object(mod,'travel_to_entrance') as dispatch:
            request.poll()
        self.assertEqual(request.state,'traveling');dispatch.assert_not_called()

    def test_unknown_dispatch_is_never_retried(self):
        request = self.request()
        with patch.object(mod, 'controller_context', return_value=self.context(1)), \
             patch.object(mod, 'ReadBatch', side_effect=lambda *a, **k: contextlib.nullcontext()), \
             patch.object(mod, 'travel_to_entrance', side_effect=RuntimeError('unknown dispatch')) as travel:
            with self.assertRaises(RuntimeError):request.start()
            self.poll(request)
            self.assertEqual(request.state, 'unknown')
            with self.assertRaises(mod.ManagementError):request.start()
            travel.assert_called_once()

    def test_missing_route_does_not_dispatch(self):
        request = self.request()
        request.destination['normal_route'] = None
        with patch.object(mod, 'travel_to_entrance') as travel:
            with self.assertRaises(mod.ManagementError):request.start()
            travel.assert_not_called()

    def test_timeout_stops_polling(self):
        request = self.request()
        request.state, request.deadline = 'traveling', 1
        with patch.object(mod, 'controller_context') as context:
            self.poll(request)
            self.assertEqual(request.state, 'failed')
            context.assert_not_called()

    def test_workspace_scroll_and_stale_controls(self):
        from expedition33.mods_workspace_scroll import ScrollWorkspaceView, CONTROL_COUNT
        model = mod.Mod()
        model.maps = [dict(title=f'Map {chr(65+i)}', package=str(i), experimental=False, normal_route={'level_id':'Test'}) for i in range(17)]
        view = mod.MapView(Mock(), model)
        self.assertIsInstance(view, ScrollWorkspaceView)
        frame = view.render()
        self.assertEqual(len(frame.controls), CONTROL_COUNT)
        self.assertEqual(view.total_rows, 17)
        self.assertEqual(frame.pages, 1)
        new_frame = view.render()
        with self.assertRaises(mod.ManagementError):
            view.activate(frame.revision, 0)
        frame = view.activate(new_frame.revision, 12)
        self.assertEqual(view.selected['package'], '12')
        frame = view.activate(frame.revision, 60)
        self.assertTrue(frame.closed)
        self.assertEqual(model.pending_travel, '12')

    def test_continuous_scrolling_never_repaints_or_moves_rows(self):
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu, TEXT_MIN, TEXT_MAX
        model = mod.Mod()
        model.maps = [dict(title=f'Map {chr(65+i)}', package=str(i), experimental=False, normal_route={'level_id':'Test'}) for i in range(17)]
        view = mod.MapView(Mock(), model)
        frame = view.render()
        panel = Mock(state='open', slider_scale=1.35)
        panel.slider_value.return_value = (1.35 - TEXT_MIN) / (TEXT_MAX - TEXT_MIN)
        menu = Mock(panel=panel, view=view, failure=None, _presentation_suspended=False)
        for offset in (0, 50, 160, 300, 336, 200, 0):
            menu._scroll_poll = 0
            panel.scroll_offset.return_value = offset
            ScrollWorkspaceMenu.poll_scroll(menu)
        menu.refresh.assert_not_called()
        menu._revoke.assert_not_called()
        menu._bind.assert_not_called()
        self.assertEqual(view._revision, frame.revision)
        self.assertEqual(view.scroll_start, 0)

    def test_groups_variants_and_search(self):
        model = mod.Mod()
        model.maps = [dict(title=title, package=str(i), experimental=False, normal_route={'level_id':'Test'}) for i, title in
                      enumerate(('Boat Graveyard 1', 'Boat Graveyard 2', 'Orange Forest'))]
        view = mod.MapView(Mock(), model)
        frame = view.render()
        self.assertEqual(view.total_rows, 2)
        self.assertEqual(frame.controls[0].label, 'Boat Graveyard (2)')
        frame = view.activate(frame.revision, 0)
        self.assertEqual(view.total_rows, 2)
        frame = view.activate(frame.revision, 1)
        self.assertEqual(view.selected['package'], '1')
        frame = view.activate(frame.revision, 52, value='Orange')
        self.assertEqual(view.total_rows, 1)
        self.assertIsNone(view.selected)

    def test_full_catalog_keeps_rows_fixed_and_handlers_bounded(self):
        from expedition33.mods_workspace import ModsWorkspaceMenu
        from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu, TEXT_MIN, TEXT_MAX
        model = mod.Mod()
        # Letter suffixes keep every test destination in its own group.
        model.maps = [dict(title=f'Map {chr(65+i//26)}{chr(65+i%26)}', package=str(i), experimental=False, normal_route={'level_id':'Test'})
                      for i in range(66)]
        view = mod.MapView(Mock(), model)
        frame = view.render()
        original = tuple((c.token, c.label) for c in frame.controls)
        panel = Mock(state='open', slider_scale=1.35)
        panel.slider_value.return_value = (1.35-TEXT_MIN)/(TEXT_MAX-TEXT_MIN)
        panel.buttons = list(range(105))
        panel.menu.bind_controls.side_effect = lambda pairs: list(pairs)
        menu = Mock(panel=panel, view=view, frame=frame, failure=None, _presentation_suspended=False)
        menu.actions = []
        menu._retain_scroll_callbacks = False
        for first in (0, 20, 41, 57, 15, 0):
            menu._scroll_poll = 0
            panel.scroll_offset.return_value = first * 84
            ScrollWorkspaceMenu.poll_scroll(menu)
            menu.actions.clear()
            ModsWorkspaceMenu._bind(menu)
            self.assertLessEqual(len(menu.actions), 64)
            registered = {button for button, callback in menu.actions}
            for i in range(first, min(first+8, 66)):
                self.assertIn(view.map_token(i), registered)
            self.assertEqual(tuple((c.token, c.label) for c in frame.controls), original)
        menu.refresh.assert_not_called()
        self.assertEqual(view._revision, frame.revision)

    def test_real_workspace_layout_contract(self):
        from expedition33.mods_workspace_scroll import ScrollWorkspacePanel, ScrollWorkspaceMenu
        model = mod.Mod()
        registry = Mock()
        registry.option.side_effect = lambda owner, key: 'World Builder' if key == 'theme' else 1.35
        view = mod.MapView(registry, model)
        frame = view.render()
        panel = Mock()
        from expedition33._menu_latency import MenuLatency
        panel.latency=MenuLatency()
        panel.layout_mode = 'editor'
        panel.key_row_capacity = 12
        for attr in ('surface_slots', 'panel_title_slots', 'surfaces', 'panel_titles'):
            setattr(panel, attr, [Mock() for _ in range(3)])
        panel.button_slots = [Mock() for _ in range(105)]
        panel.label_slots = [Mock() for _ in range(105)]
        panel.metadata = panel.metadata_labels = []
        panel.row_slots = [Mock() for _ in range(12)]
        panel.key_slots = []
        panel.switches = []
        panel.scroll_marker = None
        # Execute the real layout, including every required presenter attribute.
        ScrollWorkspacePanel.layout(panel, view)
        for i, slot in enumerate(panel.row_slots):
            panel.position.assert_any_call(slot, 0, i*6*84, 1840, 6*84)
            for cell in range(6):
                token = view.map_token(i*6+cell)
                panel.position.assert_any_call(panel.button_slots[token], 0, cell*84+2, 538, 72)
        panel.panel_titles = [Mock(), Mock(), Mock()]
        panel.labels = [Mock() for _ in range(105)]
        panel.buttons = [Mock() for _ in range(105)]
        panel.text_bounds = {}
        panel.appearance = ('World Builder', 1.35)
        menu = Mock(view=view, frame=frame, panel=panel, error=None)
        ScrollWorkspaceMenu._paint_frame(menu)
        panel.set_text.assert_any_call(panel.subtitle, 'Map Travel')

    def test_open_action_defers_until_after_callback(self):
        model = mod.Mod()
        model.native = Mock()
        model.open_menu()
        model.native.open.assert_not_called()
        model.poll()
        model.native.parent.close_menu.assert_called_once()
        model.native.open.assert_called_once()

    def test_unlisted_package_cannot_dispose_menu(self):
        model = mod.Mod()
        model.native = Mock()
        model.native.parent.travel_recovery_pending = False
        with self.assertRaises(mod.ManagementError):
            model.travel('/Game/Unknown;quit')
        model.native.parent.dispose_menu.assert_not_called()

    def panel(self):
        from expedition33.widgets import OwnedMenuPanel
        panel = OwnedMenuPanel.__new__(OwnedMenuPanel)
        panel.state = 'built'
        panel.menu = Mock()
        panel.menu.close.return_value = True
        panel.uncertain = False
        panel.assigned = True
        panel.scope = Mock()
        panel.tree, panel.canvas = Mock(), Mock()
        panel._planner = Mock()
        panel._selected_results = True
        panel.children = [Mock() for _ in range(400)]
        panel._mutate, panel._class = Mock(), Mock()
        panel._root = Mock(return_value=None)
        panel._render_call = Mock()
        panel._text, panel._enabled, panel._visible = {}, {}, {}
        panel._functions, panel._defaults = {}, {}
        return panel

    def test_whole_tree_cleanup_releases_owners_without_400_removals(self):
        panel = self.panel()
        planner = panel._planner
        self.assertTrue(panel.close_owned_tree())
        panel._mutate.assert_called_once()
        panel._root.assert_called_once()
        panel._render_call.assert_not_called()
        planner.close.assert_called_once()
        panel.scope.close.assert_called_once()
        self.assertEqual(panel.children, [])
        self.assertEqual(panel.state, 'closed')

    def test_whole_tree_cleanup_stops_if_input_detach_is_pending(self):
        panel = self.panel()
        panel.menu.close.return_value = False
        self.assertFalse(panel.close_owned_tree())
        panel._mutate.assert_not_called()
        panel.scope.close.assert_not_called()
        self.assertEqual(len(panel.children), 400)

    def test_whole_tree_cleanup_keeps_leases_if_root_readback_fails(self):
        panel = self.panel()
        panel._root.return_value = panel.canvas
        with self.assertRaises(RuntimeError):
            panel.close_owned_tree()
        panel.scope.close.assert_not_called()
        self.assertEqual(len(panel.children), 400)

    def test_normal_panel_close_preserves_individual_removals(self):
        panel = self.panel()
        self.assertTrue(panel.close())
        self.assertEqual(panel._render_call.call_count, 400)


if __name__ == '__main__':
    unittest.main()
