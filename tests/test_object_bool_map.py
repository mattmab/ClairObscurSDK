"""Object-key campaign maps require complete values and reflected key provenance."""
from copy import deepcopy
from dataclasses import replace
from unittest import TestCase
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.values import _map_value,read_values_with_references
from test_catalog import fixture
from test_values import ValueTests


def reference(obj):return dict(index=obj.index,serial=obj.serial,address=hex(obj.address),name=obj.name)


class ObjectBoolMapTests(TestCase):
    def setUp(self):
        objects,classes=fixture();self.catalog=Catalog(123,objects,classes)
        self.a,self.b=objects[4:];self.kind=objects[2]
        self.metadata=dict(map_key_type='ObjectProperty',map_value_type='BoolProperty',
            **{'map_key_property_class_'+k:v for k,v in reference(self.kind).items()})
    def payload(self,pairs):return {'$map':{'length':len(pairs),'items':pairs}}
    def ref(self,obj):return {'$reference':reference(obj)}
    def decode(self,pairs):return _map_value(self.metadata,self.payload(pairs),self.catalog)
    def test_copy_preserves_identity_false_null_and_subclass_keys(self):
        payload=self.payload([[self.ref(self.a),False],[self.ref(self.b),True],[None,False]])
        result=_map_value(self.metadata,payload,self.catalog)
        self.assertEqual(dict(result.items),{self.a:False,self.b:True,None:False})
        self.assertEqual((result.key_type,result.value_type),('ObjectProperty','BoolProperty'))
        payload['$map']['items'][0][1]=True
        self.assertFalse(result.items[self.a])
        with self.assertRaises(TypeError):result.items[self.a]=True
    def test_duplicate_null_and_object_keys_are_rejected(self):
        for key in (None,self.ref(self.a)):
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Duplicate'):
                self.decode([[key,True],[deepcopy(key),False]])
    def test_exact_object_identity_not_just_name_or_index_is_required(self):
        for field,value in (('serial',7),('address','0x1000000'),('name','Renamed')):
            key=self.ref(self.a);key['$reference'][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'reference changed'):
                self.decode([[key,True]])
    def test_reflected_key_class_and_schema_identity_are_required_even_when_empty(self):
        for mode in ('stale_constraint','missing_constraint','nonclass','wrong_class'):
            old=self.metadata.copy()
            if mode=='stale_constraint':self.metadata['map_key_property_class_serial']=9
            elif mode=='missing_constraint':self.metadata.pop('map_key_property_class_index')
            else:
                kind=self.a if mode=='nonclass' else self.catalog.by_index[3]
                self.metadata.update({'map_key_property_class_'+k:v for k,v in reference(kind).items()})
            with self.subTest(mode=mode),self.assertRaises((ValueError,KeyError)):
                self.decode([[self.ref(self.a),False]] if mode=='wrong_class' else [])
            self.metadata=old
    def test_malformed_key_and_value_shapes_fail_closed(self):
        keys=(1,'FlagA',{},True,{'$reference':{}},
              {'$reference':dict(reference(self.a),index=True)},
              {'$reference':dict(reference(self.a),serial=True)},
              {'$reference':dict(reference(self.a),address=hex(self.a.address)[2:])})
        for key in keys:
            with self.subTest(key=key),self.assertRaises(ValueError):self.decode([[key,True]])
        for value in (None,0,1,'true',[]):
            with self.subTest(value=value),self.assertRaises(ValueError):self.decode([[self.ref(self.a),value]])
        with self.assertRaises(ValueError):_map_value(self.metadata,self.payload([]))
    def test_incomplete_and_unbounded_maps_rejected(self):
        for length in (2,4097,True,-1):
            with self.subTest(length=length),self.assertRaises(ValueError):
                _map_value(self.metadata,{'$map':{'length':length,'items':[[self.ref(self.a),True]]}},self.catalog)


class ObjectBoolMapReferenceTests(TestCase):
    def test_missing_key_closure_captured_without_replaying_values(self):
        value=ValueTests();value.setUp()
        objects,classes=fixture();catalog=Catalog(123,objects[:-1],classes)
        kind=objects[2];key=objects[-1]
        value.property('States','MapProperty')
        value.rows[-1].update(map_key_type='ObjectProperty',map_value_type='BoolProperty',
            **{'map_key_property_class_'+k:v for k,v in reference(kind).items()})
        value.value('States',{'$map':dict(length=1,items=[[{'$reference':reference(key)},True]])})
        with (patch('expedition33.values._query',return_value=({'pid':123},value.rows)) as query,
                patch('expedition33.catalog.capture_selected',return_value=value.catalog) as selected):
            result,_=read_values_with_references(catalog,value.obj,fields=('States',))
        self.assertFalse(result.errors);self.assertTrue(result.values[2,'States'].items[key])
        query.assert_called_once();selected.assert_called_once()
        self.assertIn((key.index,key.serial,key.address),selected.call_args.args[1])
    def test_recycled_key_reference_never_becomes_absent_false(self):
        value=ValueTests();value.setUp()
        objects,classes=fixture();catalog=Catalog(123,objects[:-1],classes)
        kind=objects[2];key=objects[-1]
        value.property('States','MapProperty')
        value.rows[-1].update(map_key_type='ObjectProperty',map_value_type='BoolProperty',
            **{'map_key_property_class_'+k:v for k,v in reference(kind).items()})
        value.value('States',{'$map':dict(length=1,items=[[{'$reference':reference(key)},True]])})
        changed=Catalog(123,objects[:-1]+[replace(key,serial=7)],classes)
        with (patch('expedition33.values._query',return_value=({'pid':123},value.rows)) as query,
                patch('expedition33.catalog.capture_selected',return_value=changed)):
            result,_=read_values_with_references(catalog,value.obj,fields=('States',))
        self.assertIn((2,'States'),result.errors)
        self.assertNotIn((2,'States'),result.values)
        query.assert_called_once()
