import unittest
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.map_loading_overlay import MapLoadingOverlay, loading_art_path
from expedition33.widgets import widget_definition_names


class MapLoadingOverlayOwnershipTests(unittest.TestCase):
    def cover(self):
        cover = object.__new__(MapLoadingOverlay)
        cover.state = 'built'
        cover.uncertain = False
        cover.native_owned = False
        cover.widget = object()
        cover._function = Mock(side_effect=lambda owner, name: (owner, name))
        return cover

    def test_native_gate_receives_exact_noninteractive_calls(self):
        cover = self.cover()
        values = cover.adopt_native()
        self.assertIs(values[0], cover.widget)
        self.assertEqual(values[1:], (('Widget', 'SetVisibility'),
            ('UserWidget', 'AddToViewport'), ('Widget', 'IsInViewport'),
            ('Widget', 'RemoveFromParent')))
        self.assertTrue(cover.native_owned)

    def test_native_owner_prevents_widget_teardown(self):
        cover = self.cover()
        cover.adopt_native()
        cover._render_call = Mock()
        with self.assertRaisesRegex(RuntimeError, 'Native loading presentation'):
            cover.close()
        cover._render_call.assert_not_called()

    def test_native_ack_allows_detach_before_tree_cleanup(self):
        cover = self.cover()
        cover.adopt_native()
        cover.release_native()
        calls = []
        cover._render_call = lambda *args: calls.append(('detach', args))
        cover.close_owned_tree = lambda: calls.append(('tree', ())) or True
        self.assertTrue(cover.close())
        self.assertEqual([row[0] for row in calls], ['detach', 'tree'])

    def test_incomplete_or_uncertain_tree_cannot_be_adopted(self):
        for state, uncertain in (('building', False), ('built', True), ('closed', False)):
            cover = self.cover()
            cover.state, cover.uncertain = state, uncertain
            with self.assertRaises(RuntimeError):
                cover.adopt_native()
            self.assertFalse(cover.native_owned)

    def test_closed_cover_close_is_idempotent(self):
        cover = self.cover()
        cover.state = 'closed'
        self.assertTrue(cover.close())

    def test_create_metadata_closure_includes_nullable_controller_constraint(self):
        # Model the bounded reader's class closure: selecting a function does
        # not automatically select classes referenced by its FProperties. The
        # live regression was KeyError1695 before Create could be dispatched.
        from expedition33.reflection import describe
        function = SimpleNamespace(index=7, serial=12, address=0x7000,
            name='Create', class_index=16)
        controller = SimpleNamespace(index=1695, serial=22, address=0x9000,
            name='PlayerController')
        names = widget_definition_names(MapLoadingOverlay.NAMES)
        selected = {7: function}
        if 'Default__PlayerController' in names:
            selected[1695] = controller
        catalog = SimpleNamespace(pid=123, resolve=lambda obj: obj, by_index=selected)
        rows = [dict(event='object', index=7, serial=12, address='0x7000',
                     name='Create', class_index=16),
                dict(event='struct_metadata', index=7, serial=12,
                     address='0x7000', name='Create', size=32),
                dict(event='property_metadata', name='OwningPlayer',
                     type='ObjectProperty', offset=16, element_size=8,
                     dimension=1, flags='0x18001000000080',
                     property_class_index=1695, property_class_serial=22,
                     property_class_name='PlayerController', property_class_address='0x9000'),
                dict(event='function_metadata', flags='0x402240b', params_size=32,
                     return_offset=24, entry_rva='0x31361b0')]
        with patch('expedition33.reflection._query', return_value=({'pid':123}, rows)):
            result = describe(catalog, (function,))
        self.assertEqual(result[7].properties[0]['property_class_index'], 1695)


class MapLoadingArtworkTests(unittest.TestCase):
    def cover(self):
        cover = object.__new__(MapLoadingOverlay)
        cover.uncertain = False
        cover.timings = {}
        cover.art_available = False
        cover.art_image = cover.art_texture = None
        cover.invisible, cover.collapsed = 3, 1
        cover._default = lambda name: name
        cover._function = lambda owner, name: (owner, name)
        cover._spawn = Mock(return_value='owned-image')
        cover._place = Mock(return_value='owned-slot')
        cover._call = Mock()
        return cover

    def test_only_bounded_bundled_png_is_admitted(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'map-loading.png'
            with patch('expedition33.map_loading_overlay.ART_PATH', path):
                self.assertIsNone(loading_art_path())
                path.write_bytes(b'invalid image')
                self.assertIsNone(loading_art_path())
                path.write_bytes(b'\x89PNG\r\n\x1a\nfixture')
                self.assertEqual(loading_art_path(), path)
                with patch('expedition33.map_loading_overlay.MAX_ART_BYTES', 8):
                    self.assertIsNone(loading_art_path())

    def test_imported_texture_is_retained_and_image_hidden_until_brush_ready(self):
        cover = self.cover()
        texture = object()
        cover._construction_call = Mock(return_value=SimpleNamespace(return_value=texture))
        with patch('expedition33.map_loading_overlay.loading_art_path', return_value=Path('fixture.png')):
            cover._prepare_art('game-instance')
        self.assertIs(cover.art_texture, texture)
        self.assertTrue(cover.art_available)
        self.assertEqual(cover._construction_call.call_args.kwargs,
            dict(WorldContextObject='game-instance', Filename='fixture.png'))
        calls = cover._call.call_args_list
        self.assertEqual(calls[0].args, ('owned-image', 'Widget', 'SetVisibility'))
        self.assertEqual(calls[0].kwargs, {'InVisibility':1})
        self.assertEqual(calls[-2].args, ('owned-image', 'Image', 'SetBrushResourceObject'))
        self.assertEqual(calls[-1].kwargs, {'InVisibility':3})

    def test_missing_or_null_art_preserves_plain_cover(self):
        for imported in (False, True):
            cover = self.cover()
            cover._construction_call = Mock(return_value=SimpleNamespace(return_value=None))
            with patch('expedition33.map_loading_overlay.loading_art_path',
                       return_value=Path('fixture.png') if imported else None):
                with self.assertLogs('expedition33.map_loading_overlay', level='WARNING'):
                    cover._prepare_art('game-instance')
            cover._spawn.assert_not_called()
            self.assertFalse(cover.art_available)

    def test_uncertain_import_is_retained_as_failure_not_optional_fallback(self):
        cover = self.cover()
        def failed(*args, **kwargs):
            cover.uncertain = True
            raise RuntimeError('uncertain import')
        cover._construction_call = failed
        with patch('expedition33.map_loading_overlay.loading_art_path', return_value=Path('fixture.png')):
            with self.assertRaisesRegex(RuntimeError, 'uncertain import'):
                cover._prepare_art('game-instance')
        self.assertFalse(cover.art_available)


if __name__ == '__main__':
    unittest.main()
