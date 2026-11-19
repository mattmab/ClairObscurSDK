"""Layout arguments must satisfy the production invocation codec, not a loose UI mock."""
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import patch
import unittest

from expedition33 import save_story_ui as ui
from expedition33.catalog import Catalog,CatalogObject,ClassRelation
from expedition33.enums import EnumDescriptor,EnumMember,EnumValue
from expedition33.invocation import PARM,prepare_call
import test_invocation


class LayoutEnumFixture:
    def __init__(self,path,kind='EnumProperty'):
        self.path=path;self.argument,self.enum_name,self.member_name=ui.LAYOUT_ENUMS[path]
        base=test_invocation.InvocationTests();base.setUp()
        enum_class=CatalogObject(123,8,1,0x8000,'Enum','Class','Class',1,-1,0,0,0)
        self.enum=CatalogObject(123,9,1,0x9000,self.enum_name,'Enum','Class',8,-1,0,0,0)
        self.catalog=Catalog(123,(*base.catalog.objects,enum_class,self.enum),
                             (*base.catalog.classes.values(),ClassRelation(8,1,'Enum',0,160)))
        self.target,self.function=base.target,base.function
        self.field=base.field(self.argument,kind,0,1,PARM,enum_index=9,enum_serial=1,
            enum_name=self.enum_name,enum_address=hex(self.enum.address),inner_type='ByteProperty',inner_element_size=1)
        self.function_descriptor=N(owners=({'index':7,'size':1},),properties=(self.field,),
            function=dict(params_size=1,return_offset=65535,flags=0x400,entry_rva='0x1234'))
        # Deliberately use a non-default value: the UI must copy the member,
        # not reintroduce guessed 0/1/3 ordinals.
        self.enum_descriptor=EnumDescriptor(self.enum,(EnumMember(self.enum_name+'::'+self.member_name,7),))

    def arguments(self):
        with patch.dict(ui.LAYOUT_ENUMS,{self.path:ui.LAYOUT_ENUMS[self.path]},clear=True),\
             patch.object(self.catalog,'find_path',return_value=self.function),\
             patch.object(ui,'describe_enums',return_value={9:self.enum_descriptor}):
            return ui.layout_enum_arguments(self.catalog,{7:self.function_descriptor})[self.path]

    def plan(self,arguments):
        with patch('expedition33.invocation.describe',return_value={7:self.function_descriptor}),\
             patch('expedition33.invocation.describe_enums',return_value={9:self.enum_descriptor}):
            return prepare_call(self.catalog,self.target,self.function,arguments,enum_values=True)


class SaveLayoutEnumTests(unittest.TestCase):
    def test_all_layout_choices_satisfy_actual_planner_for_typed_and_legacy_enums(self):
        for path in ui.LAYOUT_ENUMS:
            for kind in ('EnumProperty','ByteProperty'):
                with self.subTest(path=path,kind=kind):
                    fixture=LayoutEnumFixture(path,kind);arguments=fixture.arguments()
                    self.assertEqual(fixture.plan(arguments).data,b'\x07')
                    value=arguments[fixture.argument]
                    self.assertIsInstance(value,EnumValue if kind=='EnumProperty' else int)
                    if kind=='EnumProperty':
                        with self.assertRaisesRegex(ValueError,'exact observed enum identity'):
                            fixture.plan({fixture.argument:7})

    def test_missing_stale_wrong_enum_or_storage_rejects_before_native_mutation(self):
        path='/Script/UMG.Widget:SetVisibility'
        for change in ('serial','address','name','reference','width','type','dimension','flags','member'):
            with self.subTest(change=change):
                fixture=LayoutEnumFixture(path)
                if change=='serial':fixture.field['enum_serial']=99
                elif change=='address':fixture.field['enum_address']='0x9999'
                elif change=='name':fixture.field['enum_name']='OtherEnum'
                elif change=='reference':fixture.field.pop('enum_index')
                elif change=='width':fixture.field['element_size']=4
                elif change=='type':fixture.field['type']='IntProperty'
                elif change=='dimension':fixture.field['dimension']=2
                elif change=='flags':fixture.field['flags']=0
                else:fixture.enum_descriptor=replace(fixture.enum_descriptor,members=(EnumMember('Other',7),))
                with self.assertRaises(RuntimeError):fixture.arguments()

    def test_changed_enum_descriptor_identity_rejects(self):
        fixture=LayoutEnumFixture('/Script/UMG.Widget:SetClipping')
        fixture.enum_descriptor=replace(fixture.enum_descriptor,object=replace(fixture.enum,serial=99))
        with self.assertRaises(RuntimeError):fixture.arguments()


if __name__=='__main__':unittest.main()
