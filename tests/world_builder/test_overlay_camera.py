import importlib.util
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
from unittest import TestCase, main
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('overlay_loader_test',ROOT/'mods/E33WorldBuilder/overlays.py')
loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(loader)

class OverlayCameraTests(TestCase):
    def setup_mod(self, active):
        ctx=dict(world='/Game/A.A',visit=[1,2,3],ready=True)
        library=SimpleNamespace(store=SimpleNamespace(read=Mock(return_value={'world':ctx['world']})),owned={},load=Mock(return_value={'objects':1800}))
        mod=SimpleNamespace(active=active,started=True,library=library,last={'edits':0},session=SimpleNamespace(pid=1),menu_reads=nullcontext)
        def command(op,**kwargs):
            if op==62:mod.active=True
            if op==22:mod.active=False
        mod.command=Mock(side_effect=command)
        return mod,ctx,Mock(return_value=[None]*49)

    def test_active_camera_reused_without_discovery_or_shutdown(self):
        mod,ctx,discover=self.setup_mod(True)
        with patch.object(loader,'context',return_value=ctx):
            self.assertEqual(loader.load(mod,'map',ctx,discover),{'objects':1800})
        self.assertTrue(mod.active)
        self.assertEqual([c.args[0] for c in mod.command.call_args_list],[26])
        discover.assert_not_called()
        mod.library.load.assert_called_once_with('map')

    def test_active_camera_preflight_failure_does_not_stop_camera(self):
        mod,ctx,discover=self.setup_mod(True)
        mod.library.load.side_effect=ValueError('asset unavailable')
        with patch.object(loader,'context',return_value=ctx),self.assertRaises(ValueError):loader.load(mod,'map',ctx,discover)
        self.assertTrue(mod.active)
        self.assertEqual([c.args[0] for c in mod.command.call_args_list],[26])

    def test_inactive_camera_uses_headless_owner_then_releases_it(self):
        mod,ctx,discover=self.setup_mod(False)
        with patch.object(loader,'context',return_value=ctx):loader.load(mod,'map',ctx,discover)
        self.assertFalse(mod.active)
        self.assertEqual([c.args[0] for c in mod.command.call_args_list],[26,62,22])

    def test_existing_edits_still_protected_in_both_modes(self):
        for active in (False,True):
            mod,ctx,discover=self.setup_mod(active);mod.library.owned={'existing':{}}
            with patch.object(loader,'context',return_value=ctx),self.assertRaises(RuntimeError):loader.load(mod,'map',ctx,discover)
            mod.library.load.assert_not_called()
            self.assertEqual(mod.active,active)

if __name__=='__main__':main()
