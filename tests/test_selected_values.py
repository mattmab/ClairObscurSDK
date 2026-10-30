"""Combined selected snapshots retain identity and value-decoder checks."""
from dataclasses import asdict,replace
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.values import capture_selected_values
from test_catalog import fixture

class CombinedValueTests(unittest.TestCase):
    def setUp(self):
        objects,classes=fixture()
        objects=[replace(o,address=o.address+0x10000) for o in objects]
        self.catalog=Catalog(123,objects,classes)
        self.identities=tuple((o.index,o.serial,o.address) for o in objects[4:])
        self.rows=[]
        for o in objects:
            row=asdict(o);row.pop('pid');row.update(event='object',address=hex(o.address),object_flags=hex(o.object_flags),item_flags=hex(o.item_flags))
            self.rows.append(row)
            if o.index>=4:
                self.rows.extend([dict(event='property_metadata',owner_index=2,name='Speed',type='FloatProperty',dimension=1),dict(event='stored_value',owner_index=2,name='Speed',element=0,value=o.index*2.)])
        self.rows += [dict(event='class_relation',**asdict(c)) for c in classes]
    def read(self):
        with patch('expedition33._reader.active_reader',return_value=N(supports_catalog_values=True)),patch('expedition33.values._query',return_value=({'pid':123},self.rows)) as query:
            result=capture_selected_values(123,self.identities,fields=('Speed',))
            query.assert_called_once_with(['--catalog-values','123','4:1:11400,5:1:11500;Speed'])
            return result
    def test_one_request_decodes_catalog_and_each_projected_target(self):
        catalog,values=self.read()
        self.assertEqual(catalog.objects,self.catalog.objects)
        self.assertEqual(values[4].values[2,'Speed'],8.)
        self.assertEqual(values[5].values[2,'Speed'],10.)
    def test_changed_missing_and_duplicate_target_rejected(self):
        original=list(self.rows)
        for mode in ('changed','missing','duplicate'):
            self.rows=[dict(r) for r in original]
            target=next(r for r in self.rows if r['event']=='object' and r['index']==5)
            if mode=='changed':target['serial']=99
            elif mode=='missing':self.rows.remove(target)
            else:self.rows.append(dict(target))
            with self.subTest(mode=mode),self.assertRaises(RuntimeQueryError):self.read()
    def test_malformed_values_are_not_accepted_as_ready(self):
        self.rows.append(dict(event='stored_value',owner_index=2,name='Speed',element=0,value=7.))
        with self.assertRaises(RuntimeQueryError):self.read()
    def test_legacy_worker_uses_existing_two_query_path(self):
        with patch('expedition33._reader.active_reader',return_value=N(supports_catalog_values=False)),patch('expedition33.catalog.capture_selected',return_value=self.catalog) as selected,patch('expedition33.values.read_values_many',return_value='values') as values,patch('expedition33.values._query') as combined:
            self.assertEqual(capture_selected_values(123,self.identities,fields=('Speed',)),(self.catalog,'values'))
            selected.assert_called_once_with(123,self.identities)
            self.assertEqual(values.call_args.kwargs,{'fields':('Speed',)})
            combined.assert_not_called()

    def test_missing_projected_reference_is_selected_and_decoded_again_without_value_replay(self):
        rows=[];include=True
        for row in self.rows:
            if row['event']=='object':include=row['index']!=5
            if include or row['event']=='class_relation':rows.append(row)
        at=next(i for i,row in enumerate(rows) if row['event']=='object' and row['index']==4)+1
        target=self.catalog.by_index[5]
        rows[at:at]=[dict(event='property_metadata',owner_index=2,name='Target',type='ObjectProperty',dimension=1),
            dict(event='stored_value',owner_index=2,name='Target',element=0,value={'$reference':dict(index=5,serial=target.serial,address=hex(target.address),name=target.name)})]
        with patch('expedition33._reader.active_reader',return_value=N(supports_catalog_values=True)), \
                patch('expedition33.values._query',return_value=({'pid':123},rows)) as query, \
                patch('expedition33.catalog.capture_selected',return_value=self.catalog) as selected:
            catalog,values=capture_selected_values(123,(self.identities[0],),fields=('Target',),references=True)
        query.assert_called_once();selected.assert_called_once_with(123,self.identities)
        self.assertEqual(values[4].values[2,'Target'],target)
