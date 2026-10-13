import unittest
from dataclasses import replace
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.values import read_table_rows
from test_catalog import fixture


class TableValues(unittest.TestCase):
    def setUp(self):
        objects,classes=fixture()
        classes[2]=replace(classes[2],name='DataTable')
        objects=[replace(o,name='DataTable' if o.index==2 else o.name,
            class_name='DataTable' if o.class_index==2 else o.class_name) for o in objects]
        self.catalog=Catalog(123,objects,classes);self.obj=self.catalog.by_index[4]
        self.target=dict(event='object',index=4,serial=1,address=hex(self.obj.address),class_index=2,name=self.obj.name)
        self.row=[dict(event='table_row',name='Level_33'),
            dict(event='property_metadata',owner_index=2,name='Level',type='IntProperty',dimension=1),
            dict(event='stored_value',owner_index=2,name='Level',element=0,value=33)]

    def read(self,rows):
        with patch('expedition33.values._query',return_value=({'pid':123},rows)):
            return read_table_rows(self.catalog,self.obj)

    def test_rows_use_existing_value_decoder(self):
        result=self.read([self.target,*self.row])
        self.assertEqual(result['Level_33'].values[2,'Level'],33)

    def test_empty_table_still_checks_identity(self):
        self.assertEqual(self.read([self.target]),{})
        with self.assertRaises(RuntimeQueryError):self.read([dict(self.target,serial=2)])

    def test_duplicate_row_and_malformed_value_rejected(self):
        with self.assertRaises(RuntimeQueryError):self.read([self.target,*self.row,*self.row])
        with self.assertRaises(RuntimeQueryError):self.read([self.target,self.row[0],self.row[2]])
