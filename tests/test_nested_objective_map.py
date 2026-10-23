import unittest
from expedition33.values import _struct_value
from test_struct_values import StructValueTests
class NestedMapTests(unittest.TestCase):
 def payload(self,value):
  f=StructValueTests();f.setUp()
  row={'name':'ObjectivesStatus','type':'MapProperty','map_key_type':'NameProperty','map_value_type':'ByteProperty','value':{'$map':{'length':1,'items':[['DefeatMime',value]]}}}
  return f,row
 def test_exact_objective_state_is_copied(self):
  f,row=self.payload(3);result=_struct_value(f.base.catalog,f.struct([row]))
  self.assertEqual(result.fields['ObjectivesStatus'].items['DefeatMime'],3)
 def test_rejects_bool_overflow_and_missing_schema(self):
  for value in (True,-1,256):
   f,row=self.payload(value)
   with self.assertRaises(ValueError):_struct_value(f.base.catalog,f.struct([row]))
  f,row=self.payload(1);del row['map_key_type']
  with self.assertRaises(ValueError):_struct_value(f.base.catalog,f.struct([row]))
 def test_unsupported_nested_map_does_not_guess(self):
  f,row=self.payload(1);row['map_value_type']='BoolProperty'
  with self.assertRaises(ValueError):_struct_value(f.base.catalog,f.struct([row]))
