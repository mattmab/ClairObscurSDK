import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
spec = importlib.util.spec_from_file_location('builder_mod', ROOT/'mods/E33WorldBuilder/mod.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Controls(unittest.TestCase):
    def test_catalog_prewarm_waits_for_management_menu_to_close(self):
        builder=mod.Mod();builder.prewarm_at=0;builder.templates=Mock()
        builder.session=SimpleNamespace(_session=SimpleNamespace(_menus=[SimpleNamespace(active=True)],console=SimpleNamespace(dispatcher=SimpleNamespace(namespace={}))))
        builder.poll()
        self.assertIsNone(builder.catalog_menu)
        self.assertEqual(builder.prewarm_at,0)

    def test_catalog_prewarm_yields_to_initial_overlay(self):
        builder=mod.Mod();builder.prewarm_at=0;builder.templates=Mock()
        overlay=SimpleNamespace(startup_pending=lambda:True)
        builder.session=SimpleNamespace(_session=SimpleNamespace(_menus=[],console=SimpleNamespace(dispatcher=SimpleNamespace(namespace={'map_overlays':overlay}))))
        builder.poll()
        self.assertIsNone(builder.catalog_menu)
        self.assertEqual(builder.prewarm_at,0)

    def test_camera_exit_survives_thumbnail_cleanup_failure(self):
        builder=mod.Mod();builder.started=True;builder.active=True
        builder.catalog_menu=SimpleNamespace(state='built',clear_images=Mock(side_effect=RuntimeError('image failed')))
        builder.command=Mock()
        with self.assertRaisesRegex(RuntimeError,'image failed'):builder.stop()
        builder.command.assert_called_once_with(22)

    def test_camera_exit_releases_open_menu_before_stopping(self):
        builder=mod.Mod();builder.started=True;builder.active=True
        events=[]
        builder.catalog_menu=SimpleNamespace(state='open',hide=lambda:events.append('hide'),clear_images=lambda **kw:events.append('images'))
        builder.command=lambda op:events.append(op)
        builder.stop()
        self.assertEqual(events,['hide','images',22])
        self.assertFalse(builder.active)

    def test_menu_rebuilt_only_when_controller_identity_changes(self):
        from unittest.mock import patch
        builder=mod.Mod();old=SimpleNamespace(index=10,serial=1,address=100)
        fresh=SimpleNamespace(index=10,serial=2,address=200,object_flags=0)
        menu=SimpleNamespace(player=old,close=Mock(return_value=True));builder.catalog_menu=menu
        builder.session=SimpleNamespace(pid=1);builder.library=SimpleNamespace(owned={'old':{}},rows=[1],known={'old':1});builder.last={'edits':0}
        with patch.object(mod,'ReadBatch'),patch.object(mod,'capture_matching',return_value=SimpleNamespace(select=lambda _: [fresh])):
            builder.refresh_menu_owner()
        menu.close.assert_called_once();self.assertIsNone(builder.catalog_menu);self.assertFalse(builder.library.owned)
    def test_same_controller_keeps_warm_menu(self):
        from unittest.mock import patch
        builder=mod.Mod();player=SimpleNamespace(index=10,serial=1,address=100,object_flags=0)
        menu=SimpleNamespace(player=player,close=Mock());builder.catalog_menu=menu;builder.session=SimpleNamespace(pid=1)
        with patch.object(mod,'ReadBatch'),patch.object(mod,'capture_matching',return_value=SimpleNamespace(select=lambda _: [player])):
            builder.refresh_menu_owner()
        menu.close.assert_not_called();self.assertIs(builder.catalog_menu,menu)

    def test_play_requires_active_camera_and_no_preview(self):
        builder=mod.Mod();builder.command=Mock()
        with self.assertRaisesRegex(ValueError,'Start the builder'):builder.play_from_camera()
        builder.active=True;builder.booth_pending=True
        with self.assertRaisesRegex(ValueError,'Exit the asset preview'):builder.play_from_camera()
        builder.command.assert_not_called()

    def test_play_closes_menu_then_teleports_and_releases_drag(self):
        builder=mod.Mod();builder.active=True;builder.held={1};builder.dragging=True
        events=[];builder.catalog_menu=SimpleNamespace(state='open',hide=lambda:events.append('hide'))
        builder.library=SimpleNamespace(message='');builder.status=Mock(return_value={})
        builder.command=lambda op:events.append(op)
        builder.play_from_camera()
        self.assertEqual(events,['hide',55]);self.assertFalse(builder.held);self.assertFalse(builder.dragging)

    def test_blocked_play_preserves_active_camera(self):
        builder=mod.Mod();builder.active=True;builder.last={'native_error':1959}
        builder.command=Mock(side_effect=RuntimeError('native'))
        with self.assertRaisesRegex(ValueError,'cannot fit'):builder.play_from_camera()
        self.assertTrue(builder.active)

    def test_space_ctrl_vertical_aliases(self):
        self.assertEqual(mod.input_motion({32}, .05),mod.input_motion({69}, .05))
        self.assertEqual(mod.input_motion({17}, .05),mod.input_motion({81}, .05))
        self.assertEqual(mod.input_motion({32,17}, .05),[0.]*8)
        self.assertEqual(mod.input_motion({32,69}, .05),mod.input_motion({32}, .05))

    def test_undo_chord_suppresses_movement(self):
        self.assertEqual(mod.input_motion({18,90,87,32,104,1}, .05),[0.]*8)

    def test_diagonal_speed_is_bounded(self):
        values = mod.input_motion({87,68,69}, .1)
        self.assertAlmostEqual(sum(v*v for v in values[:3])**.5, 160.)

    def test_hitch_does_not_teleport(self):
        self.assertEqual(mod.input_motion({87}, 10), mod.input_motion({87}, .1))

    def test_opposing_inputs_cancel(self):
        self.assertEqual(mod.input_motion({87,83,65,68,69,81,104,98,102,100,105,99,103,97}, .1), [0.]*8)

    def test_alt_is_ten_times_finer(self):
        normal = mod.input_motion({104,102,105,103}, .1)
        fine = mod.input_motion({104,102,105,103,18}, .1)
        for a,b in zip(normal[4:],fine[4:]): self.assertAlmostEqual(a, b*10)

if __name__ == '__main__': unittest.main()
