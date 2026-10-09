import unittest
from dataclasses import asdict, replace
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import capture_selected
from test_catalog import fixture


class SelectedCatalogTests(unittest.TestCase):
    def setUp(self):
        objects, classes = fixture()
        objects = [replace(obj, address=obj.address + 0x10000) for obj in objects]
        self.identity = (objects[-1].index, objects[-1].serial, objects[-1].address)
        self.rows = []
        for obj in objects:
            row = asdict(obj); row.pop('pid')
            for field in ('address', 'object_flags', 'item_flags'): row[field] = hex(row[field])
            self.rows.append(dict(event='object', **row))
        self.rows += [dict(event='class_relation', **asdict(cls)) for cls in classes]

    def test_selected_closure_preserves_inheritance_and_outer_validation(self):
        with patch('expedition33.catalog._query', return_value=({'pid':123}, self.rows)) as query:
            catalog = capture_selected(123, [self.identity])
        self.assertEqual([o.index for o in catalog.outer_chain(catalog.by_index[5])], [4, 5])
        self.assertEqual(catalog.ancestors(3), (3, 2, 0))
        query.assert_called_once_with(['--catalog-select', '123', '5:1:11500'])

    def test_invalid_inputs_never_start_native_query(self):
        with patch('expedition33.catalog._query') as query:
            for pid, identities in [(True, [self.identity]), (0, [self.identity]),
                    (123, []), (123, [self.identity]*2), (123, [(True,1,0x10000)]),
                    (123, [(5,1,1)]), (123, [(5,2**32,0x10000)]), (123, [self.identity]*1025)]:
                with self.assertRaises(ValueError): capture_selected(pid, identities)
            query.assert_not_called()

    def test_wrong_process_and_changed_selector_are_rejected(self):
        with patch('expedition33.catalog._query', return_value=({'pid':124}, self.rows)):
            with self.assertRaisesRegex(RuntimeQueryError, 'process changed'):
                capture_selected(123, [self.identity])
        with patch('expedition33.catalog._query', return_value=({'pid':123}, self.rows)):
            with self.assertRaisesRegex(RuntimeQueryError, 'missing or changed'):
                capture_selected(123, [(5, 2, self.identity[2])])

    def test_incomplete_dependencies_rejected_without_full_scan_fallback(self):
        rows = [row for row in self.rows if not (row['event'] == 'object' and row['index'] == 4)]
        with patch('expedition33.catalog._query', return_value=({'pid':123}, rows)) as query:
            with self.assertRaisesRegex(RuntimeQueryError, 'outer missing'):
                capture_selected(123, [self.identity])
            self.assertEqual(query.call_count, 1)


if __name__ == '__main__': unittest.main()
