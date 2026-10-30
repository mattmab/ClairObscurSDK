import json,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from expedition33.cinematics.authored_source import copied
from expedition33.values import StoredArray,StoredStruct
from test_catalog import fixture
from expedition33.catalog import Catalog
from dataclasses import replace
from expedition33.cinematics.authored_source import _inspect_graph,_inspect_graph_steps
from expedition33.values import StoredMapEntries

class AuthoredSourceCopyTests(unittest.TestCase):
    def setUp(self):
        objects,classes=fixture();self.objects=objects
        real=Catalog(123,objects,classes)
        self.catalog=NS(objects=objects,resolve=real.resolve,
                        path_name=Mock(side_effect=lambda o:'/Game/Test.'+o.name))
    def test_object_paths_do_not_persist_runtime_identity(self):
        obj=self.catalog.objects[-1];data=copied(obj,self.catalog)
        self.assertEqual(set(data),{'object_path','class'})
        json.dumps(data,allow_nan=False)
    def test_partial_arrays_and_structs_never_look_complete(self):
        data=copied(StoredArray((1,),2),self.catalog)
        self.assertFalse(data['complete']);self.assertEqual(data['length'],2)
        obj=self.catalog.objects[0]
        data=copied(StoredStruct(obj,{'Guid':1},{'Track':'unavailable'},{},True),self.catalog)
        self.assertFalse(data['complete']);self.assertEqual(data['errors'],{'Track':'unavailable'})
    def test_unsupported_nonfinite_and_excessive_graphs_rejected(self):
        for value in (float('nan'),object(),NS(address=123)):
            with self.assertRaises(ValueError):copied(value,self.catalog)
        with self.assertRaises(ValueError):copied(StoredArray(tuple(range(5)),5),self.catalog,budget=[2])
    def test_struct_map_keys_are_copied_without_hashing(self):
        key=StoredStruct(self.objects[0],{'A':1},{},{},False)
        data=copied(StoredMapEntries(((key,2),)),self.catalog)
        self.assertEqual(data['map'][0][0]['fields'],{'A':1})
    def test_static_channels_remain_distinct_from_dynamic_arrays(self):
        result=copied((StoredStruct(self.objects[0],{'DefaultValue':1.},{},{},False),),self.catalog)
        self.assertEqual(result['static_array'][0]['fields']['DefaultValue'],1.)


class AuthoredGraphTests(unittest.TestCase):
    def test_batched_graph_matches_single_reads_and_keeps_gameplay_actors_out(self):
        expected=_inspect_graph(self.catalog,self.objects[0],self.read)
        def batch(catalog,objects):
            return {o.index:self.read(catalog,o)[0] for o in objects},catalog
        steps=_inspect_graph_steps(self.catalog,self.objects[0],self.read,read_many=batch)
        while True:
            try:next(steps)
            except StopIteration as done:actual=done.value;break
        self.assertEqual(actual,expected)
        self.assertNotIn(self.objects[-1].index,self.reads)
    def test_incremental_graph_yields_after_each_read_and_can_be_cancelled(self):
        steps=_inspect_graph_steps(self.catalog,self.objects[0],self.read)
        self.assertEqual(self.reads,[])
        self.assertEqual(next(steps),1);self.assertEqual(len(self.reads),1)
        self.assertEqual(next(steps),2);self.assertEqual(len(self.reads),2)
        steps.close();self.assertEqual(len(self.reads),2)
        with self.assertRaises(StopIteration):next(steps)

    def test_import_metrics_measure_batches_without_changing_the_graph(self):
        expected=_inspect_graph(self.catalog,self.objects[0],self.read)
        def batch(catalog,objects):
            return {o.index:self.read(catalog,o)[0] for o in objects},catalog
        metrics={}
        steps=_inspect_graph_steps(self.catalog,self.objects[0],self.read,read_many=batch,metrics=metrics)
        while True:
            try:next(steps)
            except StopIteration as done:actual=done.value;break
        self.assertEqual(actual,expected)
        self.assertGreater(metrics['read_batches'],0)
        self.assertLessEqual(metrics['read_batches'],len(actual['nodes']))
        for key in ('read_ms','copy_ms','follow_ms'):
            self.assertGreaterEqual(metrics[key],0.)

    def test_broad_graph_batches_are_bounded_and_preserve_limits(self):
        root=self.objects[0]
        tracks=[replace(self.objects[2],index=100+i,name=str(i)) for i in range(600)]
        self.paths.update({o.index:'/Game/Root.Root:MovieScene.Track'+str(i) for i,o in enumerate(tracks)})
        self.values={root.index:{'Tracks':StoredArray(tuple(tracks),len(tracks))}}
        self.values.update({o.index:{} for o in tracks})
        expected=_inspect_graph(self.catalog,root,self.read,max_nodes=300)
        batches=[]
        def batch(catalog,objects):
            batches.append(tuple(o.index for o in objects))
            return {o.index:self.read(catalog,o)[0] for o in objects},catalog
        steps=_inspect_graph_steps(self.catalog,root,self.read,max_nodes=300,read_many=batch)
        while True:
            try:next(steps)
            except StopIteration as done:actual=done.value;break
        self.assertEqual(actual,expected)
        self.assertEqual([len(batch) for batch in batches],[1,256,43])
        self.assertEqual(len(actual['pending']),301)
        self.assertEqual(len({index for batch in batches for index in batch}),300)
        batches.clear()
        steps=_inspect_graph_steps(self.catalog,root,self.read,read_many=batch)
        while True:
            try:next(steps)
            except StopIteration as done:actual=done.value;break
        self.assertEqual([len(batch) for batch in batches],[1,256,256,88])
        self.assertEqual(len(actual['nodes']),601)
        self.assertEqual(actual['pending'],[])
        batches.clear()
        steps=_inspect_graph_steps(self.catalog,root,self.read,read_many=batch)
        next(steps);next(steps);steps.close()
        self.assertEqual([len(batch) for batch in batches],[1,256])

    def setUp(self):
        base=fixture()[0][-1]
        paths=('/Game/Root.Root','/Game/Root.Root:MovieScene',
               '/Game/Root.Root:MovieScene.ShotTrack','/Game/Child.Child',
               '/Game/Child.Child:MovieScene','/Game/Map.Map:Enemy')
        classes=('LevelSequence','MovieScene','MovieSceneCinematicShotTrack',
                 'LevelSequence','MovieScene','BP_Enemy_C')
        self.objects=[replace(base,index=i+10,name=str(i),class_name=cls)
                      for i,cls in enumerate(classes)]
        self.paths={obj.index:path for obj,path in zip(self.objects,paths)}
        self.catalog=NS(resolve=lambda obj:obj,path_name=lambda obj:self.paths[obj.index],
                        classes={},ancestors=lambda index:())
        root,scene,track,child,child_scene,enemy=self.objects
        self.values={root.index:{'MovieScene':scene},scene.index:{'Tracks':StoredArray((track,),1)},
                     track.index:{'Sequence':child,'GameplayActor':enemy},
                     child.index:{'MovieScene':child_scene},
                     child_scene.index:{'Cycle':root,'OpaqueChannel':object()}}
        self.reads=[]
    def read(self,catalog,obj):
        self.reads.append(obj.index)
        return NS(values={(obj.index,name):value for name,value in self.values[obj.index].items()},
                  errors={},truncated=frozenset()),catalog
    def test_nested_sequence_cycles_and_gameplay_references(self):
        result=_inspect_graph(self.catalog,self.objects[0],self.read)
        self.assertEqual(len(result['nodes']),5)
        self.assertEqual(len(self.reads),len(set(self.reads)))
        self.assertNotIn(self.objects[-1].index,self.reads)
        self.assertEqual(result['pending'],[])
        child=result['nodes']['/Game/Child.Child:MovieScene']
        self.assertIn('OpaqueChannel',child['errors'])
        self.assertFalse(result['editable'])
        encoded=json.dumps(result,allow_nan=False)
        self.assertNotIn('address',encoded)
    def test_graph_limit_reports_remaining_nodes(self):
        result=_inspect_graph(self.catalog,self.objects[0],self.read,max_nodes=2)
        self.assertEqual(len(self.reads),2)
        self.assertEqual(result['pending'],['/Game/Root.Root:MovieScene.ShotTrack'])
        for limit in (True,0,8193):
            with self.assertRaises(ValueError):_inspect_graph(self.catalog,self.objects[0],self.read,max_nodes=limit)
    def test_default_import_and_document_keep_large_battle_sequences_complete(self):
        root=self.objects[0]
        tracks=[replace(self.objects[2],index=100+i,name=str(i)) for i in range(5000)]
        self.paths.update({o.index:'/Game/Root.Root:MovieScene.Track'+str(i) for i,o in enumerate(tracks)})
        self.values={root.index:{'Tracks':StoredArray(tuple(tracks),len(tracks))}}
        self.values.update({o.index:{} for o in tracks})
        result=_inspect_graph(self.catalog,root,self.read)
        self.assertEqual(len(result['nodes']),5001)
        self.assertEqual(result['pending'],[])
        self.assertEqual(len(self.reads),5001)
        from expedition33.cinematics.authored_timeline import create,validate
        self.assertEqual(len(validate(create(result,'Large battle scene'))['source']['nodes']),5001)

    def test_track_subclasses_are_imported_by_ancestry_not_name_prefix(self):
        track=self.objects[2]
        self.objects[2]=replace(track,class_name='TemplateSequenceTrack',class_index=999)
        self.values[self.objects[1].index]['Tracks']=StoredArray((self.objects[2],),1)
        self.catalog.classes={999:NS(name='MovieSceneTrack')}
        self.catalog.ancestors=lambda index:(999,) if index==999 else ()
        result=_inspect_graph(self.catalog,self.objects[0],self.read)
        self.assertEqual(result['nodes'][self.paths[track.index]]['class_name'],'TemplateSequenceTrack')

    def test_private_subobject_sequence_tracks_use_subobject_separator(self):
        root,scene,track,child,child_scene,_=self.objects
        self.paths[root.index]='/Game/QA.Map:Private.Sequence'
        self.paths[scene.index]=self.paths[root.index]+'.MovieScene'
        self.paths[track.index]=self.paths[scene.index]+'.ShotTrack'
        self.paths[child.index]=self.paths[root.index]+'.Child'
        self.paths[child_scene.index]=self.paths[child.index]+'.MovieScene'
        result=_inspect_graph(self.catalog,root,self.read)
        self.assertEqual(len(result['nodes']),5)
        self.assertIn(self.paths[child_scene.index],result['nodes'])
