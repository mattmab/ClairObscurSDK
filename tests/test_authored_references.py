import unittest
from dataclasses import replace
from types import SimpleNamespace as N
from expedition33.cinematics.authored_references import _reachable_sections,_complete
from expedition33.values import StoredArray,StoredStruct
from test_catalog import fixture


class AuthoredReferenceTests(unittest.TestCase):
    def setUp(self):
        names=('Object','MovieSceneTrack','MovieSceneSubTrack','MovieSceneSection',
               'MovieSceneSubSection','LevelSequence','MovieScene','MovieSceneSequence','CameraAnimationSequence')
        parents=(-1,0,1,0,3,7,0,0,7);base=fixture()[0][-1]
        def obj(index,kind,outer=None):
            return replace(base,index=index,name=str(index),address=0x10000+index*0x100,
                class_name=names[kind],class_index=kind,outer_index=-1 if outer is None else outer.index,
                outer_serial=0 if outer is None else outer.serial)
        root=obj(10,5);scene=obj(11,6,root);subtrack=obj(12,2,scene);shot=obj(13,4,subtrack)
        child=obj(14,5);child_scene=obj(15,6,child);track=obj(16,1,child_scene);target=obj(17,3,track)
        unused=obj(18,5);unused_scene=obj(19,6,unused);unused_track=obj(20,1,unused_scene);duplicate=obj(21,3,unused_track)
        noise=obj(22,1,scene)
        self.objects={o.index:o for o in (root,scene,subtrack,shot,child,child_scene,track,target,unused,unused_scene,unused_track,duplicate,noise)}
        def ancestors(i):return (i,)+(() if parents[i]<0 else ancestors(parents[i]))
        def chain(obj):return (() if obj.outer_index<0 else chain(self.objects[obj.outer_index]))+(obj,)
        self.catalog=N(classes={i:N(name=name) for i,name in enumerate(names)},ancestors=ancestors,outer_chain=chain)
        self.root=root;self.target=target;self.duplicate=duplicate;self.reads=[]
        self.values={10:dict(MovieScene=scene),11:dict(Tracks=StoredArray((subtrack,noise),2),ObjectBindings=StoredArray((),0),CameraCutTrack=None),
            12:dict(Sections=StoredArray((shot,),1)),13:dict(SubSequence=child),14:dict(MovieScene=child_scene),
            15:dict(Tracks=StoredArray((track,),1),ObjectBindings=StoredArray((),0),CameraCutTrack=None),16:dict(Sections=StoredArray((target,),1))}
    def read(self,catalog,obj,*,fields):
        self.reads.append((obj.index,fields))
        # Property keys identify the DECLARING CLASS, not the object being read.
        return N(errors={},truncated=(),values={(obj.class_index,k):self.values[obj.index][k] for k in fields}),catalog
    def test_only_referenced_copy_selected_without_reading_curve_or_unrelated_track(self):
        self.assertEqual(_reachable_sections(self.catalog,self.root,(self.target,self.duplicate),self.read),{17})
        self.assertEqual(len(self.reads),7)
        self.assertNotIn(22,[i for i,fields in self.reads])
        self.assertNotIn(17,[i for i,fields in self.reads])
        self.assertNotIn(18,[i for i,fields in self.reads])
    def test_incomplete_nested_binding_array_is_rejected(self):
        self.values[11]['ObjectBindings']=StoredArray((),1)
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):_reachable_sections(self.catalog,self.root,(self.target,),self.read)
    def test_track_and_subsequence_reads_are_batched_and_complete(self):
        extra=replace(self.objects[22],class_index=2,class_name='MovieSceneSubTrack')
        shot=replace(self.objects[13],index=23,outer_index=22,address=0x23000)
        self.objects[22]=extra;self.objects[23]=shot
        self.values[11]['Tracks']=StoredArray((self.objects[12],extra),2)
        self.values[22]=dict(Sections=StoredArray((shot,),1));self.values[23]=dict(SubSequence=self.objects[14])
        batches=[]
        def many(catalog,objects,*,fields):
            batches.append((tuple(o.index for o in objects),fields))
            return {o.index:self.read(catalog,o,fields=fields)[0] for o in objects},catalog
        self.assertEqual(_reachable_sections(self.catalog,self.root,(self.target,),self.read,read_many=many),{17})
        self.assertIn(((12,22),('Sections',)),batches)
        self.assertIn(((13,23),('SubSequence',)),batches)
        def incomplete(catalog,objects,*,fields):return {},catalog
        with self.assertRaisesRegex(RuntimeError,'Incomplete sequence reference batch'):
            _reachable_sections(self.catalog,self.root,(self.target,),self.read,read_many=incomplete)
    def test_camera_animation_subsequence_is_traversed_as_a_sequence(self):
        child=replace(self.objects[14],class_index=8,class_name='CameraAnimationSequence')
        self.objects[14]=child;self.values[13]['SubSequence']=child
        self.assertEqual(_reachable_sections(self.catalog,self.root,(self.target,),self.read),{17})
    def test_direct_links_validate_parent_without_reading_child_contents(self):
        edges=[]
        self.values[14]={} # An unrelated child's contents must not be read.
        found=_reachable_sections(self.catalog,self.root,(),self.read,follow_subsequences=False,
            on_section_reference=lambda parent,section,child:edges.append((parent.index,section.index,child.index)))
        self.assertEqual(found,set());self.assertEqual(edges,[(10,13,14)])
        self.assertEqual(len(self.reads),4)
        self.assertNotIn(14,[i for i,fields in self.reads])
        self.values[12]['Sections']=StoredArray((self.objects[13],),2)
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            _reachable_sections(self.catalog,self.root,(),self.read,follow_subsequences=False)
    def test_sibling_sequences_share_fresh_projection_batches_without_losing_parent_edges(self):
        shot=replace(self.objects[13],index=23,address=0x23000)
        self.objects[23]=shot
        self.values[12]['Sections']=StoredArray((self.objects[13],shot),2)
        self.values[23]=dict(SubSequence=self.objects[18])
        self.values[18]=dict(MovieScene=self.objects[19])
        self.values[19]=dict(Tracks=StoredArray((self.objects[20],),1),ObjectBindings=StoredArray((),0),CameraCutTrack=None)
        self.values[20]=dict(Sections=StoredArray((self.duplicate,),1))
        batches=[];edges=[]
        def many(catalog,objects,*,fields):
            batches.append((tuple(o.index for o in objects),fields))
            return {o.index:self.read(catalog,o,fields=fields)[0] for o in objects},catalog
        found=_reachable_sections(self.catalog,self.root,(self.target,self.duplicate),self.read,read_many=many,
            on_reference=lambda parent,child:edges.append((parent.index,child.index)))
        self.assertEqual(found,{17,21});self.assertEqual(edges,[(10,14),(10,18)])
        self.assertIn(((14,18),('MovieScene',)),batches)
        self.assertIn(((15,19),('Tracks','ObjectBindings','CameraCutTrack')),batches)
        self.assertIn(((16,20),('Sections',)),batches)
    def test_foreign_track_and_section_ownership_are_rejected(self):
        self.values[16]['Sections']=StoredArray((replace(self.target,outer_index=12),),1)
        with self.assertRaisesRegex(RuntimeError,'section ownership'):_reachable_sections(self.catalog,self.root,(self.target,),self.read)
        self.values[16]['Sections']=StoredArray((self.target,),1)
        self.values[15]['Tracks']=StoredArray((replace(self.objects[16],outer_index=11),),1)
        with self.assertRaisesRegex(RuntimeError,'track ownership'):_reachable_sections(self.catalog,self.root,(self.target,),self.read)
    def test_incomplete_struct_and_deep_reference_values_are_rejected(self):
        with self.assertRaises(RuntimeError):_complete(StoredStruct(self.root,{},dict(x='opaque'),{},False))
        value=1
        for i in range(26):value=(value,)
        with self.assertRaises(RuntimeError):_complete(value)
