import math
import struct
import unittest
from types import SimpleNamespace
from expedition33._pod_values import VECTOR, COLOR, MARGIN, ANCHORS, PROFILES, encode, decode, validate_profile


class PodValueTests(unittest.TestCase):
    def test_vector3_uses_three_doubles_and_rejects_bad_shape(self):
        from expedition33._pod_values import VECTOR3
        value = {'X': 10.25, 'Y': -100.5, 'Z': 4096.125}
        self.assertEqual(encode(VECTOR3, value), struct.pack('<ddd', *value.values()))
        self.assertEqual(dict(decode(VECTOR3, encode(VECTOR3, value))), value)
        for bad in ({'X': 1, 'Y': 2}, dict(value, Z=math.inf), dict(value, Z=True)):
            with self.assertRaises(ValueError): encode(VECTOR3, bad)
        with self.assertRaises(ValueError): decode(VECTOR3, bytes(16))

    def test_actual_double_vector_and_nested_anchor_encoding(self):
        vector = {'X': 160.25, 'Y': -32.5}
        self.assertEqual(encode(VECTOR, vector), struct.pack('<dd', 160.25, -32.5))
        anchors = {'Minimum': vector, 'Maximum': {'X': 1, 'Y': 1}}
        result = decode(ANCHORS, encode(ANCHORS, anchors))
        self.assertEqual(result, anchors)
        with self.assertRaises(TypeError): result['Minimum']['X'] = 9

    def test_float_fields_and_invalid_numbers(self):
        for path in (COLOR, MARGIN):
            fields = {name: float(i) / 4 for i, (name, _, _) in enumerate(PROFILES[path].fields)}
            self.assertEqual(dict(decode(path, encode(path, fields))), fields)
        for bad in (True, '1', float('inf'), float('nan'), 10**1000, 1e100, -1e100):
            with self.assertRaises(ValueError): encode(VECTOR, {'X': bad, 'Y': 0})
        for fields in ({'X': 1}, {'X': 1, 'Y': 2, 'Z': 3}, [1, 2]):
            with self.assertRaises(ValueError): encode(VECTOR, fields)
        with self.assertRaises(ValueError): decode(VECTOR, struct.pack('<dd', math.nan, 0))
        with self.assertRaises(ValueError): decode(VECTOR, bytes(8))
        with self.assertRaises(KeyError): encode('/Script/InputCore.Key', {'KeyName': 'F6'})

    def fixture(self):
        obj = SimpleNamespace(index=1, class_name='ScriptStruct')
        catalog = SimpleNamespace(resolve=lambda _: obj, path_name=lambda _: VECTOR)
        rows = [dict(owner_index=1, name=name, offset=offset, element_size=8, dimension=1, type=kind)
                for name, offset, kind in PROFILES[VECTOR].fields]
        descriptor = SimpleNamespace(object=obj, owners=[dict(index=1,size=16,super='0x0')],properties=rows)
        return catalog, descriptor

    def test_profile_rejects_hidden_owned_fields_and_changed_layout(self):
        catalog, descriptor = self.fixture()
        self.assertEqual(validate_profile(catalog, descriptor, {}), PROFILES[VECTOR])
        for key, bad in (('type','ObjectProperty'),('offset',4),('dimension',2),('element_size',4),('owner_index',2)):
            catalog, descriptor = self.fixture()
            descriptor.properties[0][key] = bad
            with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {})
        catalog, descriptor = self.fixture()
        descriptor.properties.append(dict(descriptor.properties[0],name='Hidden'))
        with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {})
        catalog, descriptor = self.fixture()
        descriptor.owners[0]['size'] = 24
        with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {})
        catalog, descriptor = self.fixture()
        descriptor.object.class_name = 'Class'
        with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {})

    def test_nested_profile_uses_actual_index_serial_metadata_and_rejects_substitution(self):
        _, vector = self.fixture()
        vector.object.name, vector.object.serial = 'Vector2D', 1420
        anchor = SimpleNamespace(index=2, class_name='ScriptStruct', name='Anchors', serial=2987)
        objects = {1:vector.object, 2:anchor}
        catalog = SimpleNamespace(resolve=lambda obj: objects[obj.index], by_index=objects,
                                  path_name=lambda obj: VECTOR if obj.index==1 else ANCHORS)
        descriptor = SimpleNamespace(object=anchor, owners=[dict(index=2,size=32,super='0x0')],
            properties=[dict(owner_index=2,name=name,offset=offset,element_size=16,dimension=1,
                type='StructProperty',struct_index=1,struct_serial=1420,struct_name='Vector2D')
                for name,offset,_ in PROFILES[ANCHORS].fields])
        self.assertEqual(validate_profile(catalog, descriptor, {1:vector}), PROFILES[ANCHORS])
        descriptor.properties[0]['struct_serial'] = 1421
        with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {1:vector})
        descriptor.properties[0]['struct_serial'] = 1420
        with self.assertRaises(ValueError): validate_profile(catalog, descriptor, {1:descriptor})
