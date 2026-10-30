"""Reject metadata references recycled since catalog capture."""
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.reflection import describe
from test_catalog import fixture


class DescriptorTests(unittest.TestCase):
    def test_reference_identity_checks(self):
        catalog = Catalog(123, *fixture())
        obj, reference = catalog.by_index[2], catalog.by_index[3]
        for prefix in ('struct', 'enum', 'property_class', 'meta_class', 'signature_function',
                       'inner_struct', 'inner_enum', 'inner_property_class', 'inner_meta_class',
                       'map_key_struct', 'map_value_struct'):
            prop = dict(event='property_metadata', name='Reference', flags='0x0')
            prop.update({prefix + '_index': reference.index, prefix + '_serial': reference.serial,
                         prefix + '_name': reference.name, prefix + '_address': hex(reference.address)})
            rows = [dict(event='object', index=obj.index, serial=obj.serial, address=hex(obj.address),
                         name=obj.name, class_index=obj.class_index),
                    dict(event='struct_metadata', index=obj.index, serial=obj.serial,
                         address=hex(obj.address), name=obj.name), prop]
            with patch('expedition33.reflection._query', return_value=({'pid': 123}, rows)):
                self.assertEqual(describe(catalog, (obj,))[obj.index].properties[0][prefix + '_index'], reference.index)
                for suffix, stale in (('_serial', 999), ('_name', 'Recycled'), ('_address', '0x123')):
                    key, original = prefix + suffix, prop[prefix + suffix]
                    prop[key] = stale
                    with self.assertRaises(RuntimeQueryError):
                        describe(catalog, (obj,))
                    prop[key] = original


if __name__ == '__main__':
    unittest.main()
