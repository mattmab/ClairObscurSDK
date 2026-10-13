import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from expedition33.picto_catalog import NativeCatalog, CatalogView


class CatalogBuildTests(unittest.TestCase):
    def test_each_step_restores_canvas_and_never_hides_stock(self):
        serial = iter(range(1000))
        def obj():
            return SimpleNamespace(index=next(serial))
        original, stock = obj(), SimpleNamespace(class_name='WBP_PictosList_C')
        catalog = SimpleNamespace(objects=[SimpleNamespace(name='Default__WidgetBlueprintLibrary')],
                                  find_path=Mock(return_value=SimpleNamespace(index=1)))
        e = SimpleNamespace(canvas=original, pid=1, panel=obj(), host=obj(),
            planner=SimpleNamespace(_catalog=catalog, adopt_observations=Mock()),
            ui_planner=Mock(), buttons=[], button_slots={}, reference=Mock(return_value=stock),
            spawn=Mock(side_effect=lambda name: obj()), call=Mock(), create=Mock(side_effect=lambda *a, **k: obj()),
            place=Mock(), flush_layout=Mock(), one=lambda rows: next(iter(rows)))
        e.make_label = Mock(side_effect=lambda *args: obj())
        def button(*args):
            b, text = obj(), obj()
            e.buttons.append(b)
            e.button_slots[b.index] = obj()
            return b, text
        e.make_button = Mock(side_effect=button)
        n = NativeCatalog(e)
        n.metadata = object()
        descriptor = SimpleNamespace(value=lambda name: name)
        with patch('expedition33.enums.describe_enums', return_value={1: descriptor}):
            n.begin_build()
            e.spawn.assert_not_called()
            for _ in range(120):
                count = e.make_button.call_count
                ready = n.build_step()
                self.assertIs(e.canvas, original)
                self.assertLessEqual(e.make_button.call_count - count, 1)
                self.assertFalse(n.visible)
                if ready:
                    break
        self.assertTrue(n.build_ready)
        self.assertEqual(len(n.rows), CatalogView.POOL_SIZE)
        row_labels = {label.index for _, label, _ in n.rows}
        wrapping = [call for call in e.call.call_args_list if call.args[2] == 'SetWrapTextWidth'
                    and call.args[0].index in row_labels]
        self.assertEqual(len(wrapping), CatalogView.POOL_SIZE)
        self.assertTrue(all(call.kwargs['InWrapTextAt'] == 270 for call in wrapping))
        self.assertFalse(any(call.args[0] is stock for call in e.call.call_args_list))

    def test_canvas_restores_when_creation_raises(self):
        original = object()
        e = SimpleNamespace(canvas=original)
        n = NativeCatalog(e)
        with self.assertRaisesRegex(RuntimeError, 'failed'):
            n._on_canvas(object(), Mock(side_effect=RuntimeError('failed')))
        self.assertIs(e.canvas, original)

    def test_cheap_steps_group_until_button_boundary(self):
        e = SimpleNamespace(flush_layout=Mock(), ui_planner=Mock(), planner=SimpleNamespace(_catalog=object()))
        n = NativeCatalog(e)
        n.metadata = object()
        n._build_iterator = iter((None, None, 'button', None))
        with patch('expedition33.picto_catalog.time.perf_counter', return_value=0):
            self.assertFalse(n.build_step())
            self.assertEqual(e.flush_layout.call_count, 3)
            self.assertTrue(n.build_step())
        self.assertEqual(e.flush_layout.call_count, 4)

    def test_structural_work_stops_when_budget_elapsed(self):
        e = SimpleNamespace(flush_layout=Mock(), ui_planner=Mock(), planner=SimpleNamespace(_catalog=object()))
        n = NativeCatalog(e)
        n.metadata = object()
        n._build_iterator = iter((None, None))
        with patch('expedition33.picto_catalog.time.perf_counter', side_effect=(0, .081)):
            self.assertFalse(n.build_step(max_ms=80))
        self.assertEqual(e.flush_layout.call_count, 1)

    def test_filter_fallback_scrolls_new_selection_into_view(self):
        rows = {f'p{i:03}': {'name': f'Picto {i:03}', 'normal': True} for i in range(60)}
        e = SimpleNamespace(catalog_selection='p050', call=Mock(return_value=0))
        n = NativeCatalog(e)
        n.view = CatalogView(rows, {f'p{i:03}': object() for i in range(20, 60)})
        n.previous_ids = tuple(n.view.ids)
        n.view.filter = 'locked'
        n.filter_key = (False, 'all', '')
        n.visible = True
        n.extent, n.scroll = object(), object()
        n.poll = Mock()
        n.reset()
        self.assertEqual(e.catalog_selection, 'p019')
        scroll = [call.kwargs['NewScrollOffset'] for call in e.call.call_args_list
                  if call.args[2] == 'SetScrollOffset']
        self.assertEqual(scroll, [10 * CatalogView.ROW_HEIGHT - 840.])

    def test_filter_retained_selection_does_not_force_scroll(self):
        rows = {f'p{i:03}': {'name': f'Picto {i:03}', 'normal': True} for i in range(60)}
        e = SimpleNamespace(catalog_selection='p050', call=Mock(return_value=0))
        n = NativeCatalog(e)
        n.view = CatalogView(rows, {})
        n.previous_ids = tuple(n.view.ids)
        n.view.filter = 'locked'
        n.filter_key = (False, 'all', '')
        n.visible = True
        n.extent, n.scroll = object(), object()
        n.poll = Mock()
        n.reset()
        self.assertEqual(e.catalog_selection, 'p050')
        self.assertFalse(any(call.args[2] == 'SetScrollOffset' for call in e.call.call_args_list))
