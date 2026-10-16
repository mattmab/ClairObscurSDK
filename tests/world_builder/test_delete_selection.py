import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock

package=types.ModuleType('delete_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from delete_test_builder.mod import Mod


class DeleteSelectionTests(unittest.TestCase):
    def make_mod(self):
        mod=Mod();mod.active=True;mod.booth_pending=False
        row=dict(id='copy',component=(10,20,30),actor=(1,2,3))
        mod.library=types.SimpleNamespace(owned={'copy':row,'original':dict(id='original',component=(11,21,31),actor=(4,5,6))},
            selected='copy',preview_key=None,delete=Mock())
        mod.selected_identity=(10,20,30);mod.command=Mock();mod.sync_undone_copies=Mock()
        mod.catalog_menu=None;mod.directional=types.SimpleNamespace(source=None)
        return mod

    def test_deletes_only_exact_selection_and_clears_display(self):
        mod=self.make_mod()
        self.assertEqual(mod.delete_selection(),{'deleted':'copy'})
        self.assertEqual(mod.command.call_args.kwargs['ids'][0].address,3)
        mod.sync_undone_copies.assert_called_once()
        self.assertIsNone(mod.library.selected)
        self.assertEqual(mod.current_selection,'None')

    def test_stale_identity_never_falls_back_to_library_selection(self):
        mod=self.make_mod();mod.selected_identity=(10,99,30)
        with self.assertRaises(ValueError):mod.delete_selection()
        mod.library.delete.assert_not_called()

    def test_refreshes_native_selection_before_deleting(self):
        mod=self.make_mod()
        mod.command.side_effect=lambda *args,**kwargs:setattr(mod,'selected_identity',(11,21,31))
        mod.delete_selection()
        self.assertEqual(mod.command.call_args.kwargs['ids'][0].address,6)

    def test_preview_and_inactive_camera_are_rejected(self):
        for mode in ('inactive','booth','preview','draft'):
            mod=self.make_mod()
            if mode=='inactive':mod.active=False
            if mode=='booth':mod.booth_pending=True
            if mode=='preview':mod.library.preview_key='copy'
            if mode=='draft':mod.library.owned['copy']['duplication_preview']=True
            with self.assertRaises(ValueError):mod.delete_selection()
            mod.library.delete.assert_not_called()

    def test_failure_preserves_selection(self):
        mod=self.make_mod();mod.command.side_effect=RuntimeError('failed')
        with self.assertRaises(RuntimeError):mod.delete_selection()
        self.assertEqual(mod.library.selected,'copy')

    def test_source_deletion_cancels_pending_draft(self):
        mod=self.make_mod();mod.directional=types.SimpleNamespace(source={'id':'copy'},cancel=Mock())
        mod.delete_selection();mod.directional.cancel.assert_called_once_with()
