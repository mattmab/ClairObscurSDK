from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest
from expedition33 import save_story_ui as ui
from expedition33.values import StoredArray
from test_save_story_ui_enums import LayoutEnumFixture


def row(fields):return N(values={(i,k):v for i,(k,v) in enumerate(fields.items())},errors={},truncated=False)


class SaveImageCellTests(unittest.TestCase):
    def setUp(self):
        def obj(i,name,cls,outer):return N(index=i,serial=1,address=i*100,name=name,class_index=cls,outer_index=outer,outer_serial=1)
        self.tree=obj(1,'WidgetTree',11,0);self.grid=obj(2,'SlotGrid',12,1)
        self.grid_slot=obj(3,'GridSlot_0',13,2);self.box=obj(4,'SizeBox_0',14,1)
        self.box_slot=obj(5,'SizeBoxSlot_0',15,4);self.image=obj(6,'LevelImageRetainer',16,1)
        self.objects={o.index:o for o in (self.tree,self.grid,self.grid_slot,self.box,self.box_slot,self.image)}
        paths={13:'/Script/UMG.GridSlot',14:'/Script/UMG.SizeBox',15:'/Script/UMG.SizeBoxSlot',16:'/Script/UMG.RetainerBox'}
        self.objects.update({i:N(index=i,path=path) for i,path in paths.items()})
        self.catalog=N(by_index=self.objects,path_name=lambda o:o.path)
        # Installed Default__GridSlot has zero spans. The cooked image slot
        # serializes RowSpan=5 but inherits the implicit one-column value0.
        self.cell=dict(Parent=self.grid,Content=self.box,Row=0,Column=0,RowSpan=5,ColumnSpan=0,Layer=0)
        self.fields={2:dict(Slots=StoredArray((self.grid_slot,),1)),
                     4:dict(Slots=StoredArray((self.box_slot,),1)),5:dict(Parent=self.box,Content=self.image)}
        self.read=self.enterContext(patch.object(ui,'read_values_with_references',side_effect=lambda c,o,fields:
            (row({k:self.fields[o.index][k] for k in fields}),c)))
        self.batch=self.enterContext(patch.object(ui,'read_values_many_with_references',side_effect=lambda c,objects,fields:
            ({3:row(self.cell)},c)))

    def test_cell_is_existing_five_row_image_span(self):
        cell,c=ui.image_cell(self.catalog,self.tree,self.grid)
        self.assertEqual(cell,dict(Row=0,Column=0,RowSpan=5,ColumnSpan=1,Layer=0))
        self.assertIs(c,self.catalog);self.assertEqual(self.read.call_count,3)
        self.assertEqual(self.cell['ColumnSpan'],0)  # Original observed slot stays unchanged.

    def test_explicit_one_column_span_is_equivalent_to_native_default(self):
        self.cell['ColumnSpan']=1
        cell,_=ui.image_cell(self.catalog,self.tree,self.grid)
        self.assertEqual((cell['RowSpan'],cell['ColumnSpan']),(5,1))

    def test_unknown_negative_or_multiple_column_spans_cannot_resize_the_grid(self):
        for span in (-1,2,True):
            with self.subTest(span=span):
                self.cell['ColumnSpan']=span
                with self.assertRaisesRegex(RuntimeError,'Original save image cell differs'):
                    ui.image_cell(self.catalog,self.tree,self.grid)

    def test_new_rows_changed_parent_incomplete_slots_and_other_content_fail_closed(self):
        for change in ('newrow','span','parent','slots','image','outer'):
            with self.subTest(change=change):
                self.setUp()
                if change=='newrow':self.cell['Row']=5
                elif change=='span':self.cell['RowSpan']=6
                elif change=='parent':self.cell['Parent']=None
                elif change=='slots':self.fields[2]['Slots']=StoredArray((self.grid_slot,),2)
                elif change=='image':self.image.name='OriginalText'
                else:self.box.outer_serial=99
                with self.assertRaises(RuntimeError):ui.image_cell(self.catalog,self.tree,self.grid)


class LabelLayoutTests(unittest.TestCase):
    def test_zero_desired_size_hit_transparency_and_clip_precede_attachment(self):
        tree=N(index=1,serial=1,address=100);grid=N(index=2,serial=1,address=200)
        label=N(index=3,serial=1,address=300);frame=N(index=4,serial=1,address=400)
        content_slot=N(index=5,serial=1,address=500);grid_slot=N(index=6,serial=1,address=600)
        style=N(index=7,serial=1,address=700,name='CTS_B1_SmallLine_Outline_C')
        functions={};calls=[]
        def path(name):
            if name not in functions:functions[name]=N(index=100+len(functions),serial=1,address=10000+len(functions)*100,path=name)
            return functions[name]
        catalog=N(by_index={30:N(index=30,name='CommonTextBlock'),31:N(index=31,name='SizeBox')},objects=[style])
        catalog.find_path=path;catalog.find_class=lambda name:N(index=30 if name=='CommonTextBlock' else 31)
        catalog.with_observations=lambda other:catalog
        created=iter((label,frame))
        enum_fixtures={p:LayoutEnumFixture(p) for p in ui.LAYOUT_ENUMS}
        enum_arguments={p:f.arguments() for p,f in enum_fixtures.items()}
        def prepare(target,function,**arguments):
            if function.path in enum_fixtures:
                # The production planner rejects raw ordinal values for
                # EnumProperty before any mock native call can succeed.
                enum_fixtures[function.path].plan(arguments)
            def invoke():
                calls.append((target,function.path,arguments))
                result=(next(created) if function.path.endswith(':SpawnObject') else
                        content_slot if function.path.endswith(':SetContent') else
                        grid_slot if function.path.endswith(':AddChildToGrid') else None)
                return nullcontext(N(return_value=result))
            return N(invoke=invoke)
        planner=N(prepare=prepare,adopt_observations=Mock())
        scope=N(pid=1,invocation_planner=Mock(return_value=planner))
        with patch.object(ui,'SessionScope',return_value=scope),\
             patch.object(ui,'read_values_with_references',return_value=(row(dict(WidgetTree=tree,SlotGrid=grid)),catalog)),\
             patch.object(ui,'image_cell',return_value=(dict(Row=0,Column=0,RowSpan=5,ColumnSpan=1,Layer=0),catalog)),\
             patch.object(ui,'capture_matching',return_value=catalog),patch.object(ui,'capture_selected',return_value=catalog),\
             patch('expedition33.reflection.describe_selected',return_value=N(catalog=catalog,descriptors={})),\
             patch.object(ui,'layout_enum_arguments',return_value=enum_arguments),\
             patch('expedition33._stable_lease.acquire_stable',side_effect=lambda s,o:(N(object=o),None)):
            owner=ui.Label(object());self.assertTrue(owner.build(object(),catalog,'Named story',still_bound=lambda:True))
        index=next(i for i,(_,p,_) in enumerate(calls) if p.endswith(':AddChildToGrid'))
        before=calls[:index]
        for name,args in (('SetWidthOverride',dict(InWidthOverride=0.)),('SetHeightOverride',dict(InHeightOverride=0.)),
                          ('SetVisibility',enum_arguments['/Script/UMG.Widget:SetVisibility']),
                          ('SetClipping',enum_arguments['/Script/UMG.Widget:SetClipping'])):
            self.assertIn((frame,'/Script/UMG.'+('SizeBox:' if 'Override' in name else 'Widget:')+name,args),before)
        self.assertEqual(calls[index][2],dict(Content=frame,InRow=0,InColumn=0))
        self.assertTrue(all(target not in (grid,tree) for target,_,_ in before if not hasattr(target,'path')))
        self.assertIn((content_slot,'/Script/UMG.SizeBoxSlot:SetVerticalAlignment',
                       enum_arguments['/Script/UMG.SizeBoxSlot:SetVerticalAlignment']),before)
        self.assertTrue(owner.verified);self.assertIs(owner.frame,frame)


if __name__=='__main__':unittest.main()
