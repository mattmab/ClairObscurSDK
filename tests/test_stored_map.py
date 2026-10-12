from unittest import TestCase
from expedition33.values import _map_value
import test_values


class StoredMapTests(TestCase):
    metadata = {'map_key_type': 'NameProperty', 'map_value_type': 'BoolProperty'}

    def test_preserves_false_and_immutable_copy(self):
        source = {'$map': {'length': 2, 'items': [['Seen', True], ['Unseen', False]]}}
        value = _map_value(self.metadata, source)
        source['$map']['items'][0][1] = False
        self.assertEqual(dict(value.items), {'Seen': True, 'Unseen': False})
        with self.assertRaises(TypeError):
            value.items['Unseen'] = True

    def test_rejects_partial_duplicate_and_non_boolean(self):
        for payload in ({'length': 2, 'items': [['x', True]]},
                        {'length': 2, 'items': [['x', True], ['x', False]]},
                        {'length': 1, 'items': [['x', 1]]},
                        {'length': 4097, 'items': []}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                _map_value(self.metadata, {'$map': payload})

    def test_struct_map_validates_keys_type_and_object_identity(self):
        fixture = test_values.ValueTests(); fixture.setUp()
        obj = fixture.catalog.by_index[3]
        reference = dict(index=obj.index, serial=obj.serial, address=hex(obj.address), name=obj.name)
        metadata = dict(map_key_type='ByteProperty', map_value_type='StructProperty',
                        **{'map_value_struct_' + key: value for key, value in reference.items()})
        value = {'$struct': dict(type=reference, fields=[dict(name='Audio', type='ObjectProperty',
                                 value={'$reference':dict(reference)})], truncated=False)}
        payload = {'$map': dict(length=1, items=[[1,value]])}
        result = _map_value(metadata, payload, fixture.catalog)
        self.assertEqual(result.items[1].fields['Audio'], obj)
        for key in (True, -1, 256, '1'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                _map_value(metadata, {'$map':dict(length=1,items=[[key,value]])}, fixture.catalog)
        value['$struct']['fields'][0]['value']['$reference']['serial'] += 1
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            _map_value(metadata, payload, fixture.catalog)

    def test_struct_map_rejects_duplicate_and_wrong_schema(self):
        fixture = test_values.ValueTests(); fixture.setUp()
        obj = fixture.catalog.by_index[3]
        reference = dict(index=obj.index, serial=obj.serial, address=hex(obj.address), name=obj.name)
        metadata = dict(map_key_type='ByteProperty', map_value_type='StructProperty',
                        **{'map_value_struct_' + key: value for key, value in reference.items()})
        value = {'$struct':dict(type=reference,fields=[],truncated=False)}
        with self.assertRaises(ValueError):
            _map_value(metadata, {'$map':dict(length=2,items=[[1,value],[1,value]])}, fixture.catalog)
        metadata['map_value_struct_serial'] += 1
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            _map_value(metadata, {'$map':dict(length=1,items=[[1,value]])}, fixture.catalog)
