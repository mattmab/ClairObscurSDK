import sys,types,struct,unittest
from pathlib import Path
from contextlib import nullcontext
from unittest.mock import Mock

package=types.ModuleType('shortcut_test_builder')
package.__path__=[str(Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
from shortcut_test_builder.mod import Mod

class MenuShortcuts(unittest.TestCase):
    def make_mod(self,workspace,state='open',escape=False):
        mod=Mod();mod.active=True;mod.started=True;mod.booth_pending=False
        mod.command=Mock();mod.last_raw=bytearray(20984)
        struct.pack_into('<I',mod.last_raw,3560,int(escape))
        mod.refresh_menu_owner=Mock();mod.sync_catalog_selection=Mock();mod.menu_reads=nullcontext
        mod.directional=Mock();mod.pending_catalog_asset=None
        menu=Mock(state=state,workspace=workspace)
        menu.click.side_effect=lambda _:setattr(menu,'workspace','Build')
        menu.open.side_effect=lambda:setattr(menu,'state','open')
        menu.hide.side_effect=lambda:setattr(menu,'state','built')
        mod.catalog_menu=menu
        return mod,menu

    def test_f7_from_duplicate_switches_to_props_without_closing(self):
        mod,menu=self.make_mod('Duplicate');mod.open_catalog()
        menu.click.assert_called_once_with(24);menu.hide.assert_not_called();menu.open.assert_not_called()
        mod.directional.cancel.assert_called_once()

    def test_f7_reopening_duplicate_opens_props(self):
        mod,menu=self.make_mod('Duplicate','built');mod.open_catalog()
        self.assertEqual(menu.workspace,'Build');menu.open.assert_called_once()

    def test_f7_in_props_still_closes(self):
        mod,menu=self.make_mod('Build');mod.open_catalog();menu.hide.assert_called_once()

    def test_escape_closes_duplicate(self):
        mod,menu=self.make_mod('Duplicate',escape=True);mod.open_catalog()
        menu.hide.assert_called_once();menu.click.assert_not_called()
