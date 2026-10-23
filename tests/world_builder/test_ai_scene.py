import copy, importlib, json, math, sys, tempfile, types, unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]/'mods/E33WorldBuilder'
pkg=types.ModuleType('ai_test_package');pkg.__path__=[str(ROOT)];sys.modules[pkg.__name__]=pkg
ai=importlib.import_module(pkg.__name__+'.ai_scene')
scenes=importlib.import_module(pkg.__name__+'.scenes')
bulk=importlib.import_module(pkg.__name__+'.bulk')
ASSET='/Engine/BasicShapes/Cube.Cube';WORLD='/Game/Test.Test'

class AITests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.packet=ai.export_packet(WORLD,[100,200,300],{},[ASSET],[],{},50)
        self.doc=dict(format='e33.ai-scene',version=1,export_id=self.packet['export_id'],world=WORLD,name='AI sample',objects=[dict(asset='a0',position=[10,20,30])])
    def tearDown(self):self.temp.cleanup()
    def compile(self,doc=None,templates=None,capacity=50):
        return ai.compile_scene(doc or self.doc,self.packet,templates or {},WORLD,capacity)[0]
    def test_export_references_and_coverage(self):
        row=dict(asset=ASSET,transform=[0,0,0,1,110,220,330,0,1,1,1,0])
        p=ai.export_packet(WORLD,[100,200,300],{},[ASSET],[row],{},50)
        self.assertEqual(p['objects'][0],['a0',[10,20,30],[0,0,0,1],[1,1,1]])
        self.assertEqual(p['catalog'][0][1],ASSET);self.assertEqual(p['coverage']['catalog_omitted_for_size'],0)
    def test_large_export_does_not_truncate_catalog_or_context(self):
        paths=[f'/Game/Props/M{i}.M{i}' for i in range(7000)]
        rows=[dict(asset=paths[i%7000],transform=[0,0,0,1,i,0,0,0,1,1,1,0]) for i in range(25001)]
        packet=ai.export_packet(WORLD,[0,0,0],{},paths,rows,{},5984)
        self.assertEqual(len(packet['catalog']),7000);self.assertEqual(len(packet['objects']),25001)
        self.assertTrue(all(row[0] in {c[0] for c in packet['catalog']} for row in packet['objects'][:20]))
    def test_export_default_and_optional_region(self):
        for selected in (False,True):
            with self.subTest(selected=selected):
                wf,lib=self.workflow()
                lib.registry_paths=[ASSET];lib.known={}
                selection=types.SimpleNamespace(world=WORLD,points=[[10,20,30],[110,220,330]] if selected else [None,None],angles=[0,0,15],store=types.SimpleNamespace(list=lambda:[]))
                lib.mod.templates=selection;lib.mod.last={'position':[1000,2000,3000]};lib.mod.command=lambda *a:None
                captured={}
                def scan(name,**kwargs):captured.update(kwargs)
                with patch.object(bulk,'prepare',return_value=WORLD),patch.object(wf.scanner,'save',side_effect=scan):wf.export()
                self.assertEqual(captured['all_loaded'],not selected)
                # A far-away object must retain its world transform in default mode.
                row=dict(asset=ASSET,transform=[0,0,0,1,800000,220,330,0,1,1,1,0])
                captured['on_complete']({'objects':[row]})
                packet=ai.read_json(wf.last_export)
                self.assertFalse(packet['coverage']['streamed_out_objects_included'])
                self.assertIn('bytes',lib.message)
                self.assertEqual(packet['region']['mode'],'selected oriented region' if selected else 'all loaded map objects')
                self.assertEqual(len(packet['catalog']),1)
                doc=dict(self.doc,export_id=packet['export_id'],objects=[dict(asset='a0',position=packet['objects'][0][1])])
                scene,_=ai.compile_scene(doc,packet,{},WORLD,50)
                self.assertEqual(scene['objects'][0]['transform'][4:7],[800010,240,360] if selected else [800000,220,330])
    def test_unbounded_scanner_keeps_distant_objects(self):
        wf,lib=self.workflow()
        wf.scanner.job=dict(low=[0,0,0],high=[1,1,1],rows=[],all_loaded=True)
        wf.scanner.add(ASSET,[0,0,0,1,800000,-900000,12000,0,1,1,1,0])
        self.assertEqual(len(wf.scanner.job['rows']),1)
        wf.scanner.job['all_loaded']=False
        wf.scanner.add(ASSET,[0,0,0,1,800000,-900000,12000,0,1,1,1,0])
        self.assertEqual(len(wf.scanner.job['rows']),1)
        wf.scanner.job=None
    def test_distributed_sample_compiles(self):
        packet=ai.read_json(ROOT/'examples/sample-export.json');doc=ai.read_json(ROOT/'examples/sample-scene.json')
        result,_=ai.compile_scene(doc,packet,{},packet['world'],5984)
        self.assertEqual(len(result['objects']),3)
    def test_spawn_defaults_save_reload(self):
        scene=self.compile();self.assertEqual(scene['objects'][0]['transform'],[0,0,0,1,110,220,330,0,1,1,1,0])
        store=scenes.MapStore(self.root);key=store.save(scene);self.assertEqual(store.read(key),scene)
    def test_unreal_rotation_axes(self):
        for angle,expected in [([90,0,0],[0,0,1]),([0,90,0],[0,1,0])]:
            point=ai.rotate_point([1,0,0],[0,0,0],ai.quaternion(angle))
            for a,b in zip(point,expected):self.assertAlmostEqual(a,b)
        self.assertAlmostEqual(ai.quaternion([0,0,90])[0],-math.sqrt(.5))
    def test_invalid_transform_and_operations(self):
        for key,value in [('position',[float('nan'),0,0]),('position',[True,0,0]),('position',[1e9,0,0]),('position',[1,2]),('rotation',[float('inf'),0,0]),('scale',[0,1,1]),('scale',[-1,1,1]),('script','bad')]:
            with self.subTest(key=key,value=value):
                d=copy.deepcopy(self.doc);d['objects'][0][key]=value
                with self.assertRaises(ValueError):self.compile(d)
    def test_unknown_and_context_only_assets(self):
        self.doc['objects'][0]['asset']='invented'
        with self.assertRaises(ValueError):self.compile()
        self.doc['objects'][0]['asset']='a0';self.packet['catalog'][0][4]=False
        with self.assertRaises(ValueError):self.compile()
    def test_wrong_map_export_version(self):
        for key,value in [('world','/Game/Other.Other'),('export_id','bad'),('version',True),('format','script')]:
            d=copy.deepcopy(self.doc);d[key]=value
            with self.assertRaises(ValueError):self.compile(d)
    def test_repetition_capacity(self):
        self.doc['objects'][0]['repeat']={'count':3,'step':[400,0,0]}
        self.assertEqual([r['transform'][4] for r in self.compile()['objects']],[110,510,910])
        with self.assertRaises(ValueError):self.compile(capacity=2)
        for count in (True,0,1.5,1000000):
            self.doc['objects'][0]['repeat']['count']=count
            with self.assertRaises(ValueError):self.compile()
    def test_template_rotation_scale_and_capacity(self):
        template=self.compile();template['objects'][0]['transform'][4:7]=[100,0,0]
        self.packet['templates']={'t0':{'object_count':1}}
        self.doc['objects']=[dict(template='t0',position=[0,0,0],rotation=[0,90,0],scale=[2,2,2],repeat={'count':2,'step':[1000,0,0]})]
        result=self.compile(templates={'t0':template})
        self.assertAlmostEqual(result['objects'][0]['transform'][4],100)
        self.assertAlmostEqual(result['objects'][0]['transform'][5],400)
        self.assertEqual(result['objects'][0]['transform'][8:11],[2,2,2])
        with self.assertRaises(ValueError):self.compile(templates={'t0':template},capacity=1)
        with self.assertRaises(ValueError):self.compile()
        self.doc['objects'][0]['scale']=[1,2,1]
        with self.assertRaises(ValueError):self.compile(templates={'t0':template})
    def test_strict_json(self):
        path=self.root/'test.json'
        for text in ('{"x":NaN}','{"x":1,"x":2}'):
            path.write_text(text)
            with self.assertRaises(ValueError):ai.read_json(path)
        path.write_text('{}')
        with self.assertRaises(ValueError):ai.read_json(path,1)
    def workflow(self):
        lib=types.SimpleNamespace(store=scenes.MapStore(self.root/'maps'),mod=types.SimpleNamespace(),owned={'existing':{'asset':ASSET}},context=lambda:(None,None,None,WORLD),message='',bulk_indices={ASSET:0})
        wf=ai.AIWorkflow(lib);self.addCleanup(wf.close)
        ai.write_json(wf.root/'retained'/(self.packet['export_id']+'.json'),dict(packet=self.packet,templates={}))
        return wf,lib
    def test_partial_spawn_preserves_existing_and_reports(self):
        wf,lib=self.workflow();self.doc['objects'][0]['repeat']={'count':3,'step':[10,0,0]};path=self.root/'scene.json';ai.write_json(path,self.doc)
        def spawn(library,rows,prepared):
            library.owned['new']={'asset':ASSET}
            return [{'id':'new','asset':ASSET},{'asset':ASSET,'error':'Unavailable'}]
        with patch.object(bulk,'prepare',return_value=WORLD):wf.import_file(path)
        with patch.object(bulk,'spawn_batch',side_effect=spawn):wf.poll()
        self.assertIn('existing',lib.owned);self.assertEqual(len(wf.queue),1)
        with patch.object(bulk,'spawn_batch',return_value=[{'asset':ASSET,'error':'Unavailable'}]):wf.poll()
        self.assertEqual(len(wf.report['succeeded']),1);self.assertEqual(len(wf.report['failed']),2)
        self.assertEqual(ai.read_json(wf.report_path)['total'],3)
    def test_world_change_stops_without_spawning(self):
        wf,lib=self.workflow();path=self.root/'scene.json';ai.write_json(path,self.doc)
        with patch.object(bulk,'prepare',return_value=WORLD):wf.import_file(path)
        lib.context=lambda:(None,None,None,'/Game/Other.Other')
        with patch.object(bulk,'spawn_batch') as spawn:wf.poll();spawn.assert_not_called()
        self.assertEqual(len(wf.report['unattempted']),1);self.assertIn('existing',lib.owned)
    def test_uncertain_batch_not_retried(self):
        wf,lib=self.workflow();path=self.root/'scene.json';ai.write_json(path,self.doc)
        with patch.object(bulk,'prepare',return_value=WORLD):wf.import_file(path)
        with patch.object(bulk,'spawn_batch',side_effect=RuntimeError('Unknown acknowledgment')) as spawn:
            wf.poll();wf.poll();self.assertEqual(spawn.call_count,1)
        self.assertTrue(wf.report['uncertain']);self.assertEqual(len(wf.report['uncertain_sources']),1)

if __name__=='__main__':unittest.main()
