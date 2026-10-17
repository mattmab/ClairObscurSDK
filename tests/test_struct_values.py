"""Struct observation bounds, stale identities and original Explorer encoding."""
import unittest

from expedition33.values import StoredStruct
from expedition33.introspection import _Backend, _Explorer, _adapt
import test_values


class StructValueTests(unittest.TestCase):
    def setUp(self):
        self.base = test_values.ValueTests()
        self.base.setUp()
        ref = self.base.catalog.by_index[3]
        self.reference = dict(index=ref.index, serial=ref.serial, address=hex(ref.address), name=ref.name)

    def struct(self, fields, truncated=False):
        return {'$struct': {'type': dict(self.reference), 'fields': fields, 'truncated': truncated}}

    def observe(self, value):
        self.base.property('Data', 'StructProperty')
        self.base.rows[-1]['struct_index'] = self.reference['index']
        self.base.rows[-1]['struct_serial'] = self.reference['serial']
        self.base.rows[-1]['struct_name'] = self.reference['name']
        self.base.value('Data', value)
        return self.base.read()

    def test_nested_values_errors_and_truncation_survive_core_encoding(self):
        value = self.struct([
            {'name':'Key', 'type':'StructProperty', 'value':self.struct([
                {'name':'KeyName', 'type':'NameProperty', 'value':'Tilde'}])},
            {'name':'Enabled', 'type':'BoolProperty', 'value':True},
            {'name':'Opaque', 'type':'MapProperty', 'error':'STRUCT_MEMBER_TYPE_UNSUPPORTED'}], True)
        stored = self.observe(value).values[2, 'Data']
        self.assertIsInstance(stored.fields['Key'], StoredStruct)
        with self.assertRaises(TypeError): stored.fields['Enabled'] = False
        encoded = _Explorer(_Backend()).encode(_adapt(_Backend(), stored), depth=3)
        self.assertTrue(encoded['truncated'])
        self.assertEqual(encoded['fields']['Key']['fields'], {'KeyName':'Tilde'})
        self.assertTrue(encoded['fields']['Enabled'])
        self.assertIn('$error', encoded['fields']['Opaque'])

    def test_recycled_nested_type_rejects_entire_property(self):
        nested = self.struct([])
        nested['$struct']['type']['serial'] += 1
        result = self.observe(self.struct([{'name':'Nested','type':'StructProperty','value':nested}]))
        self.assertNotIn((2, 'Data'), result.values)
        self.assertIn('reference changed', result.errors[2, 'Data'])

    def test_autocomplete_strings_and_full_185_entry_encoding(self):
        from expedition33.values import StoredArray
        value = self.struct([
            {'name': 'Command', 'type': 'StrProperty', 'value': 'show Fog'},
            {'name': 'Desc', 'type': 'StrProperty', 'value': 'Brouillard — 日本語 🎮'},
            {'name': 'Empty', 'type': 'StrProperty', 'value': ''}])
        stored = self.observe(value).values[2, 'Data']
        backend = _Backend()
        encoded = _Explorer(backend).encode(_adapt(backend, StoredArray((stored,) * 185, 185)),
                                            depth=3, budget=[2000])
        self.assertEqual(len(encoded['items']), 185)
        self.assertFalse(encoded['truncated'])
        self.assertEqual(encoded['items'][-1]['fields'],
                         {'Command': 'show Fog', 'Desc': 'Brouillard — 日本語 🎮', 'Empty': ''})

    def test_struct_string_rejects_nonstring_and_oversize(self):
        from expedition33.values import _struct_value
        for value in (None, 42, {}, 'x' * 4097):
            with self.subTest(value_type=type(value)), self.assertRaisesRegex(ValueError, 'Invalid struct string'):
                _struct_value(self.base.catalog, self.struct([
                    {'name': 'Desc', 'type': 'StrProperty', 'value': value}]))

    def test_array_encoding_remains_bounded(self):
        encoded = _Explorer(_Backend()).encode(list(range(300)), depth=2, budget=[2000])
        self.assertEqual(len(encoded['items']), 256)
        self.assertEqual(encoded['length'], 300)
        self.assertTrue(encoded['truncated'])

    def test_native_185_entry_struct_array_decodes_without_truncation(self):
        value = self.struct([{'name': 'Command', 'type': 'StrProperty', 'value': 'show Fog'},
                             {'name': 'Desc', 'type': 'StrProperty', 'value': ''}])
        self.base.array('StructProperty', 185, [value] * 185)
        self.base.rows[-1]['truncated'] = False
        self.base.rows[-2].update(inner_struct_index=self.reference['index'],
            inner_struct_serial=self.reference['serial'], inner_struct_name=self.reference['name'])
        result = self.base.read()
        self.assertEqual(len(result.values[2, 'Dynamic'].items), 185)
        self.assertNotIn((2, 'Dynamic'), result.truncated)

    def test_class_members_accept_null_and_verified_class_identity(self):
        cls = self.base.catalog.by_index[next(iter(self.base.catalog.classes))]
        ref = dict(index=cls.index, serial=cls.serial, address=hex(cls.address), name=cls.name)
        fields = [{'name':'CameraShake','type':'ClassProperty','value':{'$reference':ref}},
                  {'name':'CameraModifier','type':'ClassProperty','value':None}]
        stored = self.observe(self.struct(fields)).values[2, 'Data']
        self.assertEqual(stored.fields['CameraShake'], cls)
        self.assertIsNone(stored.fields['CameraModifier'])

    def test_class_member_rejects_recycled_and_nonclass_references(self):
        from expedition33.values import _struct_value
        cls = self.base.catalog.by_index[next(iter(self.base.catalog.classes))]
        ref = dict(index=cls.index, serial=cls.serial+1, address=hex(cls.address), name=cls.name)
        field = {'name':'CameraShake','type':'ClassProperty','value':{'$reference':ref}}
        with self.assertRaisesRegex(ValueError, 'reference changed'):
            _struct_value(self.base.catalog, self.struct([field]))
        obj = next(o for o in self.base.catalog.objects if o.index not in self.base.catalog.classes)
        field['value']['$reference'] = dict(index=obj.index, serial=obj.serial, address=hex(obj.address), name=obj.name)
        with self.assertRaisesRegex(ValueError, 'not a reflected class'):
            _struct_value(self.base.catalog, self.struct([field]))

    def test_duplicate_fields_invalid_scalar_and_depth_rejected(self):
        from expedition33.values import _struct_value
        row = {'name':'Number', 'type':'ByteProperty', 'value':4}
        for fields in ([row, row], [dict(row, value=256)], [dict(row, value=True)]):
            with self.assertRaises(ValueError): _struct_value(self.base.catalog, self.struct(fields))
        value = self.struct([])
        for _ in range(4): value = self.struct([{'name':'Nested','type':'StructProperty','value':value}])
        with self.assertRaises(ValueError): _struct_value(self.base.catalog, value)

    def test_struct_array_type_mismatch_and_stale_member(self):
        value = self.struct([{'name':'KeyName','type':'NameProperty','value':'Tilde'}])
        self.base.array('StructProperty', 1, [value])
        self.base.rows[-2]['inner_struct_index'] = self.reference['index']
        self.base.rows[-2]['inner_struct_serial'] = self.reference['serial']
        self.base.rows[-2]['inner_struct_name'] = self.reference['name']
        self.assertEqual(self.base.read().values[2,'Dynamic'].items[0].fields['KeyName'], 'Tilde')
        self.base.rows[-2]['inner_struct_index'] += 1
        self.assertNotIn((2,'Dynamic'), self.base.read().values)
        self.base.rows[-2]['inner_struct_index'] = self.reference['index']
        value['$struct']['type']['serial'] += 1
        self.assertNotIn((2,'Dynamic'), self.base.read().values)

    def test_empty_struct_array_still_checks_type_identity(self):
        self.base.array('StructProperty', 0, [])
        self.base.rows[-2].update(inner_struct_index=self.reference['index'],
            inner_struct_serial=self.reference['serial'], inner_struct_name=self.reference['name'])
        self.assertEqual(self.base.read().values[2,'Dynamic'].items, ())
        self.base.rows[-2]['inner_struct_serial'] += 1
        self.assertIn((2,'Dynamic'), self.base.read().errors)


if __name__ == '__main__': unittest.main()
