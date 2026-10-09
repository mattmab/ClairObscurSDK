"""Stored-value response identity and partial-field failure checks."""
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.values import read_values, read_object_reference, StoredArray
from test_catalog import fixture


class ValueTests(unittest.TestCase):
    def test_direct_reference_adopts_fresh_closure_without_full_scan(self):
        objects, classes = fixture()
        initial = Catalog(123, objects[:-1], classes)
        child = objects[-1]
        self.property('Child', 'ObjectProperty')
        self.value('Child', {'$reference': dict(index=child.index, serial=child.serial,
            address=hex(child.address), name=child.name)})
        with patch('expedition33.values._query', return_value=({'pid':123}, self.rows)) as query, \
                patch('expedition33.catalog.capture', side_effect=AssertionError('no full scan')), \
                patch('expedition33.catalog.capture_selected', return_value=self.catalog) as selected:
            value, combined = read_object_reference(initial, self.obj, objects[2], 'Child')
        self.assertEqual(value, child)
        self.assertIn(child.index, combined.by_index)
        self.assertNotIn(child.index, initial.by_index)
        query.assert_called_once()
        selected.assert_called_once_with(123, ((self.obj.index, self.obj.serial, self.obj.address),
                                               (child.index, child.serial, child.address)))

    def test_direct_reference_failure_does_not_retry_or_fall_back(self):
        child = self.catalog.by_index[5]
        self.property('Child', 'ObjectProperty')
        self.value('Child', {'$reference': dict(index=child.index, serial=child.serial,
            address=hex(child.address), name=child.name)})
        with patch('expedition33.values._query', return_value=({'pid':123}, self.rows)) as query, \
                patch('expedition33.catalog.capture_selected', side_effect=RuntimeQueryError('recycled')) as selected:
            with self.assertRaisesRegex(RuntimeQueryError, 'recycled'):
                read_object_reference(self.catalog, self.obj, self.catalog.by_index[2], 'Child')
        query.assert_called_once()
        selected.assert_called_once()

    def test_direct_reference_null_and_wrong_property_type(self):
        self.property('Child', 'ObjectProperty'); self.value('Child', None)
        with patch('expedition33.values._query', return_value=({'pid':123}, self.rows)), \
                patch('expedition33.catalog.capture_selected', side_effect=AssertionError('no selector')):
            value, catalog = read_object_reference(self.catalog, self.obj, self.catalog.by_index[2], 'Child')
            self.assertIsNone(value)
            self.assertIs(catalog, self.catalog)
            self.rows[1]['type'] = 'IntProperty'
            with self.assertRaisesRegex(RuntimeQueryError, 'scalar object'):
                read_object_reference(self.catalog, self.obj, self.catalog.by_index[2], 'Child')

    def setUp(self):
        self.catalog = Catalog(123, *fixture())
        self.obj = self.catalog.by_index[4]
        self.rows = [dict(event='object', index=4, serial=1, address=hex(self.obj.address),
                          class_index=2, name=self.obj.name)]

    def property(self, name, kind, dimension=1):
        self.rows.append(dict(event='property_metadata', owner_index=2, name=name, type=kind, dimension=dimension))

    def value(self, name, value, element=0):
        self.rows.append(dict(event='stored_value', owner_index=2, name=name, element=element, value=value))

    def read(self):
        with patch('expedition33.values._query', return_value=({'pid': 123}, self.rows)):
            return read_values(self.catalog, self.obj)

    def test_float_and_static_array_and_unsupported(self):
        self.property('Speed', 'FloatProperty'); self.value('Speed', 20)
        self.property('Fixed', 'IntProperty', 2); self.value('Fixed', -1); self.value('Fixed', 9, 1)
        self.property('Container', 'ArrayProperty')
        result = self.read()
        self.assertIs(type(result.values[2, 'Speed']), float)
        self.assertEqual(result.values[2, 'Fixed'], (-1, 9))
        self.assertIn((2, 'Container'), result.errors)

    def test_stale_reference_is_field_error(self):
        self.property('Player', 'ObjectProperty')
        self.value('Player', {'$reference': dict(index=5, serial=99, address='0x1', name='gone')})
        result = self.read()
        self.assertIn((2, 'Player'), result.errors)
        self.assertNotIn((2, 'Player'), result.values)

    def test_partial_array_error_discards_entire_property(self):
        self.property('Values', 'IntProperty', 2); self.value('Values', 5)
        self.rows.append(dict(event='stored_value_error', owner_index=2, name='Values', error='changed'))
        self.assertNotIn((2, 'Values'), self.read().values)

    def test_duplicate_element_and_target_identity_fail(self):
        self.property('Value', 'IntProperty'); self.value('Value', 1); self.value('Value', 2)
        with self.assertRaises(RuntimeQueryError): self.read()
        self.rows = self.rows[:1]; self.rows[0]['serial'] = 2
        with self.assertRaises(RuntimeQueryError): self.read()

    def test_string_truncation_and_double_type(self):
        self.property('Text', 'StrProperty'); self.value('Text', 'prefix')
        self.rows[-1]['truncated'] = True
        self.property('Precision', 'DoubleProperty'); self.value('Precision', 1)
        result = self.read()
        self.assertIn((2, 'Text'), result.truncated)
        self.assertIs(type(result.values[2, 'Precision']), float)

    def array(self, kind, length, items):
        self.property('Dynamic', 'ArrayProperty')
        self.rows[-1]['inner_type'] = kind
        self.value('Dynamic', {'$array': {'length': length, 'items': items}})
        self.rows[-1]['truncated'] = length > 64

    def test_bounded_array_preserves_length_and_original_core_output(self):
        from expedition33.introspection import _Backend, Explorer
        self.array('IntProperty', 100, list(range(64)))
        result = self.read()
        array = result.values[2, 'Dynamic']
        self.assertIsInstance(array, StoredArray)
        self.assertEqual(len(array), 100)
        self.assertEqual(tuple(array), tuple(range(64)))
        with self.assertRaises(IndexError): array[64]
        encoded = Explorer(_Backend()).encode(array)
        self.assertEqual(encoded, {'items': list(range(64)), 'length': 100, 'truncated': True})
        self.assertIn((2, 'Dynamic'), result.truncated)

    def test_array_reference_identity_and_whole_field_failure(self):
        reference = self.catalog.by_index[5]
        self.array('ObjectProperty', 2, [None, {'$reference': dict(index=reference.index,
            serial=reference.serial, address=hex(reference.address), name=reference.name)}])
        result = self.read()
        self.assertEqual(result.values[2, 'Dynamic'].items, (None, reference))
        self.rows[-1]['value']['$array']['items'][1]['$reference']['serial'] += 1
        result = self.read()
        self.assertNotIn((2, 'Dynamic'), result.values)
        self.assertIn('reference changed', result.errors[2, 'Dynamic'])

    def test_array_invalid_extent_type_and_truncation_rejected(self):
        self.array('ByteProperty', 1, [True])
        with self.assertRaises(RuntimeQueryError): self.read()
        self.rows[-1]['value']['$array']['items'] = [255]
        self.assertEqual(self.read().values[2, 'Dynamic'].items, (255,))
        self.rows[-1]['value']['$array']['length'] = 2
        with self.assertRaises(RuntimeQueryError): self.read()
        self.rows[-1]['value']['$array']['length'] = 1
        self.rows[-1]['truncated'] = True
        with self.assertRaises(RuntimeQueryError): self.read()

    def test_array_nonfinite_floats_and_unsupported_empty_type(self):
        import math
        self.array('DoubleProperty', 3, [1, {'$float': 'nan'}, {'$float': '-inf'}])
        values = self.read().values[2, 'Dynamic'].items
        self.assertIs(type(values[0]), float)
        self.assertTrue(math.isnan(values[1]))
        self.assertEqual(values[2], float('-inf'))
        self.rows[-2]['inner_type'] = 'StructProperty'
        self.rows[-1]['value']['$array'] = {'length': 0, 'items': []}
        with self.assertRaises(RuntimeQueryError): self.read()


if __name__ == '__main__': unittest.main()
