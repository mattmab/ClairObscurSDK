import importlib.util
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[1]
package=types.ModuleType('camera_test_builder');package.__path__=[str(ROOT/'mods/E33WorldBuilder')]
sys.modules[package.__name__]=package
sys.path.insert(0,'S:/SteamLibrary/steamapps/common/Expedition 33/SDK/src')
from camera_test_builder.camera_settings import CameraSettings, DEFAULTS, validate, selected_owned
from camera_test_builder.mod import Mod
from camera_test_builder.catalog_menu import CatalogMenu
from camera_test_builder.browser import Browser

class CameraTests(unittest.TestCase):
    def test_save_reload_and_corrupt_fallback(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as root:
            settings=CameraSettings(root)
            self.assertEqual(settings.values,DEFAULTS)
            values=dict(sensitivity=.7,fly_speed=3200.,highlight=False)
            settings.save(values)
            self.assertEqual(CameraSettings(root).values,validate(values))
            settings.path.write_text('{broken')
            self.assertEqual(CameraSettings(root).values,DEFAULTS)

    def test_invalid_values_do_not_replace_saved_preferences(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as root:
            settings=CameraSettings(root);settings.save(DEFAULTS)
            for key,value in [('sensitivity',float('nan')),('sensitivity',0),('fly_speed',10001),('fly_speed',True),('highlight',1)]:
                with self.assertRaises(ValueError):settings.save(dict(DEFAULTS,**{key:value}))
            self.assertEqual(CameraSettings(root).values,DEFAULTS)

    def test_runtime_rejection_does_not_save(self):
        mod=Mod();mod.active=True;mod.camera_settings=Mock(values=dict(DEFAULTS));mod.command=Mock(side_effect=RuntimeError('rejected'))
        with self.assertRaises(RuntimeError):mod.save_camera_settings(1.,2400.,False)
        mod.camera_settings.save.assert_not_called()

    def test_selection_identity_and_preview_exclusion(self):
        row=dict(id='prop',component=[10,20,30],asset='/Game/Props/Rock.Rock')
        mod=Mod();mod.library=types.SimpleNamespace(owned={'prop':row},preview_key=None,selected=None)
        mod.selected_identity=(10,21,30);mod.sync_catalog_selection()
        self.assertIsNone(mod.pending_catalog_asset)
        mod.selected_identity=(10,20,30);mod.sync_catalog_selection()
        self.assertEqual(mod.pending_catalog_asset,row['asset'])
        mod.pending_catalog_asset=None;mod.sync_catalog_selection()
        self.assertIsNone(mod.pending_catalog_asset)
        mod._catalog_selection=None;mod.library.preview_key='prop';mod.sync_catalog_selection()
        self.assertIsNone(mod.pending_catalog_asset)

    def test_focus_reveals_selected_prop_and_favorite(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as root:
            rows=[dict(path=f'/Game/Props/R{i:02d}.R{i:02d}',name=f'R{i:02d}',kind='mesh') for i in range(40)]
            menu=object.__new__(CatalogMenu);menu.browser=Browser(root)
            menu.library=types.SimpleNamespace(rows=rows,known={r['path']:r for r in rows},registry_complete=True)
            menu.query='unrelated';menu.favorites=True;menu.search=object();menu._render_call=Mock()
            menu.focus_asset(rows[30]['path'])
            self.assertEqual(menu.offset,18);self.assertEqual(menu.selected,rows[30]);self.assertEqual(menu.workspace,'Build')
            menu.browser.favorite(menu.asset())
            self.assertIn(rows[30]['path'],Browser(root).favorites)

    def test_camera_captions_use_owned_text_rendering(self):
        menu=object.__new__(CatalogMenu)
        label=types.SimpleNamespace(index=101)
        menu.breadcrumb=object();menu.footer=object();menu.camera_labels=[label]
        menu._text={};menu._render_call=Mock()
        menu.set_text(label,'Mouse sensitivity')
        menu.set_text(label,'Mouse sensitivity')
        menu._render_call.assert_called_once_with(label,'TextBlock','SetText',InText='Mouse sensitivity')

    def test_camera_page_focus_and_failed_open_restores_flight(self):
        from unittest.mock import patch
        from expedition33.widgets import OwnedMenuPanel
        menu=object.__new__(CatalogMenu);menu.workspace='Camera'
        menu.buttons=list(range(53));menu.mod=Mock();menu.widget=object();menu.menu=None;menu.uncertain=False
        def rejected(panel):
            self.assertEqual(panel.buttons[0],52)
            raise RuntimeError('focus rejected after cleanup')
        with patch.object(OwnedMenuPanel,'open',rejected):
            with self.assertRaises(RuntimeError):menu.open()
        self.assertEqual(menu.buttons[0],0)
        self.assertEqual([c.args for c in menu.mod.automatic.call_args_list],[(False,),(True,)])

    def test_click_highlight_persists_and_uses_native_mode_two(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as root:
            settings=CameraSettings(root)
            values=dict(DEFAULTS,highlight='click');settings.save(values)
            self.assertEqual(CameraSettings(root).values,validate(values))
            mod=Mod();mod.active=True;mod.command=Mock()
            mod.apply_camera_settings(values)
            self.assertEqual(mod.command.call_args.kwargs['values'][2],2)
            with self.assertRaises(ValueError):validate(dict(DEFAULTS,highlight='invalid'))

    def test_duplicate_rejects_unowned_and_existing_carry(self):
        mod=Mod();mod.session=types.SimpleNamespace(pid=1);mod.active=True;mod.command=Mock();mod.selected_identity=(1,2,3)
        mod.library=types.SimpleNamespace(owned={},preview_key=None)
        with self.assertRaisesRegex(ValueError,'spawned scene'):mod.duplicate_to_hand()
        mod.last={'carrying':True}
        with self.assertRaisesRegex(ValueError,'place the current'):mod.duplicate_to_hand()

    def test_duplicate_tracks_new_identity_without_changing_source(self):
        import struct
        from unittest.mock import patch
        source=dict(id='source',kind='mesh',asset='/Game/Cube.Cube',component=(1,2,3),actor=(4,5,6),world='world')
        mod=Mod();mod.session=types.SimpleNamespace(pid=1);mod.active=True;mod.command=Mock();mod.selected_identity=(1,2,3)
        mod.library=types.SimpleNamespace(owned={'source':dict(source)},preview_key=None,world='world',message='')
        raw=bytearray(20984);struct.pack_into('<iiQ',raw,3568,10,11,12);struct.pack_into('<iiQ',raw,3584,13,14,15)
        mod.scene_command=Mock(return_value=raw)
        with patch('expedition33.catalog.capture_selected',return_value=types.SimpleNamespace(by_index={1:object()})):
            result=mod.duplicate_to_hand()
        self.assertTrue(result['carrying']);self.assertEqual(len(mod.library.owned),2)
        self.assertEqual(mod.library.owned['source'],source)
        self.assertEqual(mod.library.owned[result['id']]['component'],(13,14,15))

    def test_copy_mode_migrates_and_persists(self):
        self.assertFalse(validate(dict(sensitivity=2,fly_speed=1600,highlight=False))['duplicate_click'])
        with tempfile.TemporaryDirectory(dir=ROOT/'build') as root:
            settings=CameraSettings(root);settings.save(dict(DEFAULTS,duplicate_click=True))
            self.assertTrue(CameraSettings(root).values['duplicate_click'])
            with self.assertRaises(ValueError):settings.save(dict(DEFAULTS,duplicate_click=1))

    def test_click_request_is_acknowledged_after_failure(self):
        mod=Mod();mod.last={'duplicate_requested':True};mod.library=types.SimpleNamespace(message='')
        mod.duplicate_to_hand=Mock(side_effect=ValueError('stale source'));mod.command=Mock()
        mod.process_duplicate_click()
        mod.command.assert_called_once_with(59)
        self.assertIn('stale source',mod.library.message)

    def test_no_request_does_not_duplicate(self):
        mod=Mod();mod.duplicate_to_hand=Mock();mod.command=Mock()
        mod.process_duplicate_click();mod.duplicate_to_hand.assert_not_called();mod.command.assert_not_called()

    def test_native_click_request_response_validation(self):
        import struct
        from contextlib import nullcontext
        def response(kind, packet):
            raw=bytearray(packet)
            struct.pack_into('<I',raw,3384,1)
            return {'mesh_packet':raw.hex()}
        mod=Mod();mod.session=types.SimpleNamespace(_lease_context=nullcontext,_session=types.SimpleNamespace(_transport=types.SimpleNamespace(command=response)))
        self.assertTrue(mod.command(26)['duplicate_requested'])

    def test_duplicate_undo_prunes_only_full_actor_identity(self):
        import struct
        source=dict(actor=(10,20,30));copy=dict(actor=(11,21,31));recycled=dict(actor=(11,22,31))
        mod=Mod();mod.last={'undo_revision':1}
        mod.library=types.SimpleNamespace(owned={'source':source,'copy':copy,'recycled':recycled},selected='copy')
        mod.catalog_menu=types.SimpleNamespace(selected={'id':'copy'},signature='old')
        raw=bytearray(20984);struct.pack_into('<I',raw,3560,1);struct.pack_into('<QiiQ',raw,4096,1,*copy['actor'])
        mod.last_raw=raw;mod.command=Mock()
        mod.sync_undone_copies()
        self.assertEqual(mod.library.owned,{'source':source,'recycled':recycled})
        self.assertIsNone(mod.library.selected);self.assertIsNone(mod.catalog_menu.selected)
        mod.sync_undone_copies();mod.command.assert_called_once_with(60)

    def test_duplicate_undo_rejects_malformed_history(self):
        import struct
        mod=Mod();mod.last={'undo_revision':1};mod.command=Mock()
        mod.last_raw=bytearray(20984);struct.pack_into('<I',mod.last_raw,3560,65)
        with self.assertRaisesRegex(RuntimeError,'Invalid duplicate'):mod.sync_undone_copies()
        self.assertFalse(hasattr(mod,'_undo_revision'))

    def test_redo_restores_same_map_id_with_new_identity(self):
        import struct
        source=dict(id='source',actor=(10,20,30),component=(40,50,60),asset='cube')
        copy=dict(id='copy',actor=(11,21,31),component=(41,51,61),asset='cube')
        mod=Mod();mod.last={'undo_revision':2};mod.library=types.SimpleNamespace(owned={'source':source,'copy':copy},selected='copy');mod.command=Mock()
        raw=bytearray(20984);struct.pack_into('<I',raw,3560,2)
        struct.pack_into('<QiiQ',raw,4096,1,*copy['actor'])
        struct.pack_into('<QiiQiiQiiQ',raw,4152,2,*copy['actor'],12,22,32,42,52,62)
        mod.last_raw=raw;mod.sync_undone_copies()
        self.assertEqual(mod.library.owned['source'],source)
        self.assertEqual(mod.library.owned['copy']['actor'],(12,22,32))
        self.assertEqual(mod.library.owned['copy']['component'],(42,52,62))
        self.assertEqual(mod.library.owned['copy']['id'],'copy')
        mod.sync_undone_copies();mod.command.assert_called_once_with(60)

    def test_undo_redo_undo_events_stay_removed(self):
        import struct
        copy=dict(id='copy',actor=(11,21,31),component=(41,51,61),asset='cube')
        mod=Mod();mod.last={'undo_revision':3};mod.library=types.SimpleNamespace(owned={'copy':copy},selected='copy');mod.command=Mock()
        raw=bytearray(20984);struct.pack_into('<I',raw,3560,3)
        struct.pack_into('<QiiQ',raw,4096,1,*copy['actor'])
        struct.pack_into('<QiiQiiQiiQ',raw,4152,2,*copy['actor'],12,22,32,42,52,62)
        struct.pack_into('<QiiQ',raw,4208,3,12,22,32)
        mod.last_raw=raw;mod.sync_undone_copies()
        self.assertEqual(mod.library.owned,{})
        self.assertEqual(mod._undone_records[(12,22,32)]['id'],'copy')
