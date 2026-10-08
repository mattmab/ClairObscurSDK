"""Stored-value response identity and partial-field failure checks."""
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.values import read_values
from test_catalog import fixture


class ValueTests(unittest.TestCase):
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


if __name__ == '__main__': unittest.main()
