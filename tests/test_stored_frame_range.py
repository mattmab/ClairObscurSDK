import copy,unittest
from dataclasses import replace,FrozenInstanceError
from types import SimpleNamespace
import test_struct_values
from expedition33.values import StoredFrameRange,_struct_value

class StoredFrameRangeTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_struct_values.StructValueTests();self.fixture.setUp()
        source=self.fixture.base.catalog
        by_index=dict(source.by_index);index=self.fixture.reference['index']
        by_index[index]=replace(by_index[index],class_name='ScriptStruct')
        self.catalog=SimpleNamespace(by_index=by_index,classes=source.classes,
                                    path_name=lambda o:'/Script/MovieScene.MovieSceneFrameRange')
    def raw(self):
        data=self.fixture.struct([])
        data['$struct']['native']={'frame_range':dict(lower=dict(kind='inclusive',value=-24000),upper=dict(kind='exclusive',value=48000))}
        return data
    def test_typed_pointer_free_bounds_and_half_open_conversion(self):
        result=_struct_value(self.catalog,self.raw()).native
        self.assertEqual((result.start,result.end),(-24000,48000))
        self.assertEqual(StoredFrameRange('exclusive',0,'inclusive',10).start,1)
        self.assertEqual(StoredFrameRange('exclusive',0,'inclusive',10).end,11)
        self.assertIsNone(StoredFrameRange('open',None,'open',None).start)
        with self.assertRaises(FrozenInstanceError):result.lower=10
    def test_invalid_bounds_and_malformed_or_wrong_struct_native_data_reject(self):
        for kind,value in (('unknown',0),('open',0),('inclusive',None),('inclusive',True),('exclusive',1<<31)):
            with self.assertRaises(ValueError):StoredFrameRange(kind,value,'open',None)
        bad=self.raw();bad['$struct']['native']['frame_range']['lower']['address']=123
        with self.assertRaises(ValueError):_struct_value(self.catalog,bad)
        bad=self.raw();bad['$struct']['fields']=[dict(name='Unexpected',type='IntProperty',value=1)]
        with self.assertRaises(ValueError):_struct_value(self.catalog,bad)
        self.catalog.path_name=lambda o:'/Script/Other.MovieSceneFrameRange'
        with self.assertRaises(ValueError):_struct_value(self.catalog,self.raw())
