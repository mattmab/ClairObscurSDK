"""Validate new typed-map decoding against adversarial wire responses."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests')]
from expedition33.values import _map_value, StoredMapEntries
from test_values import ValueTests


class MapExtensionTests(unittest.TestCase):
    def setUp(self):
        fixture = ValueTests(); fixture.setUp()
        self.catalog = fixture.catalog
        self.obj = self.catalog.by_index[3]
        self.ref = dict(index=self.obj.index, serial=self.obj.serial, address=hex(self.obj.address), name=self.obj.name)
        self.key = {'$struct': dict(type=dict(self.ref), fields=[dict(name='Slot', type='IntProperty', value=2)], truncated=False)}
        self.meta = dict(map_key_type='StructProperty', map_value_type='ObjectProperty',
                         **{'map_key_struct_' + k: v for k, v in self.ref.items()})

    def decode(self, items, meta=None):
        return _map_value(meta or self.meta, {'$map': dict(length=len(items), items=items)}, self.catalog)

    def test_struct_key_object_and_null(self):
        result = self.decode([[self.key, {'$reference': dict(self.ref)}]])
        self.assertIsInstance(result, StoredMapEntries)
        self.assertEqual(result.entries[0][0].fields['Slot'], 2)
        self.assertEqual(result.entries[0][1], self.obj)
        self.assertIsNone(self.decode([[self.key, None]]).entries[0][1])

    def test_changed_object_identity_rejected(self):
        for field, value in [('serial', self.obj.serial+1), ('address', hex(self.obj.address+8)), ('name', 'Other')]:
            ref = dict(self.ref); ref[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'reference changed'):
                self.decode([[self.key, {'$reference': ref}]])

    def test_duplicate_struct_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.decode([[self.key, None], [self.key, None]])

    def test_partial_or_wrong_struct_key_rejected(self):
        self.key['$struct']['truncated'] = True
        with self.assertRaises(ValueError):
            self.decode([[self.key, None]])
        self.key['$struct']['truncated'] = False
        self.meta['map_key_struct_serial'] += 1
        with self.assertRaises(ValueError):
            self.decode([[self.key, None]])

    def test_name_struct(self):
        meta = dict(map_key_type='NameProperty', map_value_type='StructProperty',
                    **{'map_value_struct_' + k: v for k, v in self.ref.items()})
        self.assertEqual(self.decode([['Effect', self.key]], meta).items['Effect'].fields['Slot'], 2)
        with self.assertRaises(ValueError):
            self.decode([[4, self.key]], meta)

    def test_byte_double_and_invalid_bool(self):
        meta = dict(map_key_type='ByteProperty', map_value_type='DoubleProperty')
        self.assertEqual(self.decode([[2, 1.25]], meta).items[2], 1.25)
        for pair in ([True, 1.], [256, 1.], [0, True], [0, '1.2']):
            with self.subTest(pair=pair), self.assertRaises(ValueError):
                self.decode([pair], meta)


if __name__ == '__main__':
    unittest.main()
