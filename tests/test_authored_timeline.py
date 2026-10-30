import copy,json,tempfile,unittest
from unittest.mock import patch
from expedition33.cinematics.authored_timeline import create,retime,edit_key,validate,TimelineStore,channel,channels

ROOT='/Game/Test/Test.Test'
SECTION=ROOT+':MovieScene.TransformTrack.TransformSection'
def fixture():
    frame=lambda n:dict(struct='/Script/CoreUObject.FrameNumber',fields=dict(Value=n),errors={},complete=True)
    value=lambda n:dict(struct='/Script/MovieScene.MovieSceneDoubleValue',fields=dict(Value=n,Tangent=dict(original='preserved'),InterpMode=2),errors={},complete=True)
    curve=dict(struct='/Script/MovieScene.MovieSceneDoubleChannel',fields=dict(
        Times=dict(array=[frame(0),frame(24000)],length=2,complete=True),
        Values=dict(array=[value(10.),value(20.)],length=2,complete=True)),errors={},complete=True)
    source=dict(sequence=ROOT,nodes={ROOT:dict(class_name='LevelSequence',fields={},errors={},truncated=[]),
        SECTION:dict(class_name='MovieScene3DTransformSection',fields=dict(
            SectionRange=dict(frame_range=dict(lower=dict(kind='inclusive',value=0),upper=dict(kind='exclusive',value=48000))),
            Translation=dict(static_array=[curve])),errors={},truncated=[])},pending=[],editable=False)
    return create(source,'Test authored timeline')

class AuthoredTimelineTests(unittest.TestCase):
    def test_scene_yaw_is_optional_bounded_and_does_not_mutate_source(self):
        from expedition33.cinematics.authored_timeline import rotate_scene,validate
        original=fixture();source=copy.deepcopy(original['source']);placed=rotate_scene(original,90)
        self.assertNotIn('scene_yaw',original);self.assertEqual(placed['scene_yaw'],90.)
        self.assertEqual(validate(placed)['source'],source)
        for value in (True,181,-181,float('nan'),float('inf')):
            with self.assertRaises(ValueError):rotate_scene(original,value)
        malformed=copy.deepcopy(placed);malformed['scene_yaw']=float('nan')
        with self.assertRaises(ValueError):validate(malformed)
    def test_scene_and_npc_edits_validate_once_and_keep_independent_documents(self):
        from expedition33.cinematics.authored_timeline import place_scene,set_npc
        import expedition33.cinematics.authored_timeline as timeline
        original=fixture();before=copy.deepcopy(original)
        position=[12.,34.,56.]
        with patch.object(timeline,'validate',wraps=timeline.validate) as checked:
            placed=place_scene(original,position)
            self.assertEqual(checked.call_count,1)
        position[0]=99.
        self.assertEqual(placed['scene_position'],[12.,34.,56.])
        placed['source']['nodes'][ROOT]['fields']['independent']=True
        self.assertEqual(original,before)
        with self.assertRaisesRegex(ValueError,'finite world coordinates'):
            place_scene(original,[0.,float('nan'),0.])
        with self.assertRaisesRegex(ValueError,'snapshot'):
            place_scene(placed,[0.,0.,0.])
        offset=[1.,2.,3.]
        with patch.object(timeline,'validate',wraps=timeline.validate) as checked:
            edited=set_npc(original,'a'*32,name='Verso',profile='verso',start=0,end=30,offset=offset,yaw=0.)
            self.assertEqual(checked.call_count,1)
        offset[0]=99.
        self.assertEqual(edited['npc_tracks'][0]['placement']['offset'],[1.,2.,3.])
        self.assertEqual(validate(edited),edited)
        with self.assertRaisesRegex(ValueError,'end must follow'):
            set_npc(original,'a'*32,name='Verso',profile='verso',start=10,end=10,offset=[0.,0.,0.],yaw=0.)
        self.assertEqual(original,before)
    def test_validation_returns_independent_snapshot_and_never_mutates_input(self):
        original=edit_key(fixture(),SECTION,['Translation',0],0,at=500,value=12.5)
        before=copy.deepcopy(original)
        validated=validate(original)
        self.assertEqual(original,before)
        validated['source']['nodes'][SECTION]['fields']['Translation']['static_array'][0]['fields']['Times']['array'][0]['fields']['Value']=42
        validated['key_edits'][0]['value']=99.
        self.assertEqual(original,before)
        invalid=copy.deepcopy(original);invalid['key_edits'][0]['at']=24000
        invalid_before=copy.deepcopy(invalid)
        with self.assertRaises(ValueError):validate(invalid)
        self.assertEqual(invalid,invalid_before)
    def test_validation_preserves_shared_aliases_and_non_json_source_types(self):
        from expedition33.cinematics.authored_timeline import digest,_unshared_json_tree
        original=fixture();shared=[1.,2.,3.]
        original['source']['nodes'][ROOT]['fields']['position']=shared
        original['scene_position']=shared
        original['source_sha256']=digest(original['source'])
        self.assertFalse(_unshared_json_tree(original))
        result=validate(original)
        fields=result['source']['nodes'][ROOT]['fields']
        self.assertIs(fields['position'],result['scene_position'])
        self.assertIsNot(fields['position'],shared)
        original=fixture()
        original['source']['nodes'][ROOT]['fields']['tuple']=(1,2)
        original['source_sha256']=digest(original['source'])
        self.assertFalse(_unshared_json_tree(original))
        fields=validate(original)['source']['nodes'][ROOT]['fields']
        self.assertIsInstance(fields['tuple'],tuple)
        self.assertEqual(fields['tuple'],(1,2))
    def test_validation_fast_path_preserves_independence(self):
        from expedition33.cinematics.authored_timeline import _unshared_json_tree
        original=fixture()
        self.assertTrue(_unshared_json_tree(original))
        result=validate(original)
        self.assertEqual(result,original)
        result['source']['nodes'][ROOT]['fields']['changed']=True
        self.assertNotIn('changed',original['source']['nodes'][ROOT]['fields'])
    def test_reset_key_preserves_other_edits_and_rejects_crossing_a_moved_neighbor(self):
        from expedition33.cinematics.authored_timeline import reset_key
        original=fixture();path=['Translation',0]
        edited=edit_key(original,SECTION,path,0,at=-200,value=12.)
        edited=edit_key(edited,SECTION,path,1,at=-100,value=22.)
        before=copy.deepcopy(edited)
        with self.assertRaisesRegex(ValueError,'neighbor'):reset_key(edited,SECTION,path,0)
        self.assertEqual(edited,before)
        restored=reset_key(edited,SECTION,path,1)
        self.assertEqual(len(restored['key_edits']),1)
        self.assertEqual(reset_key(restored,SECTION,path,0),original)
        with self.assertRaises(ValueError):reset_key(original,SECTION,path,True)
    def test_channel_browser_uses_exact_paths_and_effective_edits(self):
        original=fixture();edited=edit_key(original,SECTION,['Translation',0],0,at=500,value=12.5)
        curves=channels(edited,SECTION)
        self.assertEqual(len(curves),1);self.assertEqual(curves[0]['path'],['Translation',0])
        self.assertEqual(curves[0]['keys'][0],dict(index=0,at=500,value=12.5))
        self.assertEqual(channel(edited,SECTION,['Translation',0])[1][0]['at'],0)
        partial=fixture();partial['source']['nodes'][SECTION]['fields']['Translation']['static_array'][0]['fields']['Times']['complete']=False
        self.assertEqual(channels(partial,SECTION),())
    def test_section_and_key_edits_roundtrip_without_changing_source_or_interpolation(self):
        original=fixture();source=copy.deepcopy(original['source'])
        edited=retime(original,SECTION,1000,47000)
        edited=edit_key(edited,SECTION,['Translation',0],0,at=500,value=12.5)
        self.assertEqual(edited['source'],source);self.assertEqual(original,fixture())
        self.assertEqual(edited['key_edits'][0]['value'],12.5)
        self.assertEqual(channel(edited,SECTION,['Translation',0])[1][0]['value'],10.)
        self.assertEqual(validate(edited),edited)
        with tempfile.TemporaryDirectory() as directory:
            store=TimelineStore(directory);key=store.save(edited)
            loaded=store.read(key);self.assertEqual(loaded,edited)
            self.assertNotIn('address',json.dumps(loaded))
            self.assertEqual(store.save(retime(loaded,SECTION,2000,46000),key),key)
    def test_store_compacts_large_graphs_and_enforces_byte_limit_on_save_and_read(self):
        document=fixture();document['name']='Café 演奏'
        compact=(json.dumps(document,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')
        pretty=(json.dumps(document,indent=2,allow_nan=False)+'\n').encode('utf8')
        self.assertLess(len(compact),len(pretty))
        with tempfile.TemporaryDirectory() as directory:
            store=TimelineStore(directory)
            with patch('expedition33.cinematics.authored_timeline.MAX_TIMELINE_BYTES',len(compact)):
                key=store.save(document)
                self.assertEqual(store.file(key).read_bytes(),compact)
                self.assertEqual(store.read(key),document)
                with patch('expedition33.cinematics.authored_timeline.MAX_TIMELINE_BYTES',len(compact)-1):
                    with self.assertRaisesRegex(ValueError,'size limit'):store.save(document,key)
                    with self.assertRaisesRegex(ValueError,'Invalid authored timeline file'):store.read(key)
                self.assertEqual(store.file(key).read_bytes(),compact)
            # Files written by earlier releases used pretty-printed JSON.
            store.file(key).write_bytes(pretty)
            self.assertEqual(store.read(key),document)
    def test_invalid_or_partial_channel_never_accepts_key_edits(self):
        document=fixture()
        for index,at,value in ((0,24000,1.),(1,-1,1.),(True,1,1.),(2,1,1.),(0,1,float('nan'))):
            with self.assertRaises(ValueError):edit_key(document,SECTION,['Translation',0],index,at=at,value=value)
        partial=copy.deepcopy(document);partial['source']['nodes'][SECTION]['fields']['Translation']['static_array'][0]['fields']['Times']['complete']=False
        with self.assertRaisesRegex(ValueError,'Complete matching'):edit_key(partial,SECTION,['Translation',0],0,at=1,value=1.)
        with self.assertRaises(ValueError):retime(document,SECTION,10,10)
        with self.assertRaises(ValueError):retime(document,ROOT,0,10)
    def test_snapshot_integrity_duplicate_edits_and_reordered_keys_are_checked(self):
        document=edit_key(fixture(),SECTION,['Translation',0],0,at=100,value=12.)
        changed=copy.deepcopy(document);changed['source']['nodes'][ROOT]['fields']['changed']=True
        with self.assertRaisesRegex(ValueError,'snapshot'):validate(changed)
        bad=copy.deepcopy(document);bad['key_edits']*=2
        with self.assertRaisesRegex(ValueError,'duplicate'):validate(bad)
        # Joint edits may move both keys together, preserving their source ordinals.
        document['key_edits']=[dict(section=SECTION,path=['Translation',0],index=0,at=30000,value=12.),
                               dict(section=SECTION,path=['Translation',0],index=1,at=40000,value=22.)]
        self.assertEqual(validate(document),document)
        document['key_edits'][1]['at']=20000
        with self.assertRaisesRegex(ValueError,'neighboring'):validate(document)
