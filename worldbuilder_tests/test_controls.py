import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, 'S:/SteamLibrary/steamapps/common/Expedition 33/SDK/src')
spec = importlib.util.spec_from_file_location('builder_mod', ROOT/'mods/E33WorldBuilder/mod.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class Controls(unittest.TestCase):
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
