from dataclasses import FrozenInstanceError
from pathlib import Path
import subprocess
import unittest

from expedition33.values import StoredSoftObjectPath, _struct_value
import test_struct_values


class StoredSoftPathTests(unittest.TestCase):
    def setUp(self):
        self.fixture=test_struct_values.StructValueTests();self.fixture.setUp()

    def decode(self,payload):
        value=self.fixture.struct([dict(name='SequenceToPlay',type='SoftObjectProperty',value=payload)])
        return _struct_value(self.fixture.base.catalog,value).fields['SequenceToPlay']

    def tag(self,package='/Game/Original/Sequence',asset='Sequence',subpath=''):
        return {'$soft_object_path':dict(package=package,asset=asset,subpath=subpath)}

    def test_copied_path_is_frozen_and_has_no_weak_pointer_or_resolution(self):
        value=self.decode(self.tag(subpath='PersistentLevel.Actor🎮'))
        self.assertEqual(value.path,'/Game/Original/Sequence.Sequence:PersistentLevel.Actor🎮')
        with self.assertRaises(FrozenInstanceError):value.package='/Other'
        self.assertFalse(hasattr(value,'resolve'))
        self.assertFalse(hasattr(value,'cache'))
        self.assertFalse(hasattr(value,'load'))

    def test_null_is_exact_none_pair_and_empty_subpath(self):
        value=self.decode(self.tag(None,None))
        self.assertIsNone(value.path)
        for package,asset,subpath in ((None,'Sequence',''),('/Game/Original',None,''),(None,None,'Child')):
            with self.assertRaises(ValueError):self.decode(self.tag(package,asset,subpath))

    def test_nested_struct_preserves_typed_soft_path(self):
        child=self.fixture.struct([dict(name='BPCineExitPoint',type='SoftObjectProperty',value=self.tag(subpath='Exit'))])
        root=self.fixture.struct([dict(name='PostCinematicParameters',type='StructProperty',value=child)])
        value=_struct_value(self.fixture.base.catalog,root)
        self.assertEqual(value.fields['PostCinematicParameters'].fields['BPCineExitPoint'].subpath,'Exit')

    def test_bad_tags_fields_and_types_reject(self):
        for raw in (None,'/Game/A.A',{}, {'$soft_object_path':{}},
                    {'$soft_object_path':dict(package='/Game/A',asset='A',subpath='',cache=42)},
                    self.tag(1,'A'),self.tag('/Game/A',False),self.tag('/Game/A','A',[])):
            with self.subTest(raw=raw),self.assertRaises(ValueError):self.decode(raw)

    def test_bad_path_grammar_and_bounds_reject(self):
        for package,asset in (('Game/A','A'),('/Game//A','A'),('/Game/A/','A'),('/Game/A','A/B'),
                              ('/Game/A.A','A'),('/Game/A',''),('/Game/'+'A'*1024,'A')):
            with self.assertRaises(ValueError):self.decode(self.tag(package,asset))
        for subpath in ('A\0B','\ud800','\udfff','A'*4097,'🎮'*2049):
            with self.assertRaises(ValueError):self.decode(self.tag(subpath=subpath))
        self.assertEqual(len(self.decode(self.tag(subpath='🎮'*2048)).subpath),2048)

    def test_unsupported_soft_class_still_rejects(self):
        value=self.fixture.struct([dict(name='Class',type='SoftClassProperty',value=self.tag())])
        with self.assertRaises(ValueError):_struct_value(self.fixture.base.catalog,value)

    def test_native_soft_path_fixture(self):
        executable=Path(__file__).resolve().parents[1]/'build/stored-soft-path/stored_soft_path_fixture.exe'
        if not executable.exists():self.skipTest('Build stored soft path fixture first')
        result=subprocess.run([str(executable)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('UTF16 and bounds PASS',result.stdout)
