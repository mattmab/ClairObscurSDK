import copy,json,tempfile,unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33.cinematics.authored_timeline import create,replace_cast,place_cast,validate,TimelineStore
from expedition33.cinematics.authored_replacement import guid_fields
from test_authored_cast import fixture


class AuthoredReplacementTests(unittest.TestCase):
    def test_cast_timing_records_resolution_spawn_and_binding_and_preserves_failure(self):
        from expedition33.cinematics.authored_replacement import _apply_snapshot
        from expedition33._menu_latency import MenuLatency
        from unittest.mock import Mock
        path='/Game/Shot.Shot'
        document=dict(source={},cast_edits=[dict(sequence=path,guid=f'{1:032x}',profile='sciel')])
        sequence=N(scope=N(_session=N(_transport=object())),_asset=object())
        latency=MenuLatency();actor=Mock();owners=[]
        with patch('expedition33.cinematics.authored_replacement.sources_for',return_value={path:object()}), \
             patch('expedition33._timeline_actor_channel.validate_count'), \
             patch('expedition33.cinematics.blueprint_actor.BlueprintActor',return_value=actor), \
             patch('expedition33.cinematics.binding_overrides.bind_actor',side_effect=RuntimeError('bind failed')):
            with self.assertRaisesRegex(RuntimeError,'bind failed'):
                _apply_snapshot(sequence,document,(0,0,0),owners=owners,latency=latency)
        rows=latency.snapshot()['timings']
        self.assertEqual({k:rows[k]['failed'] for k in rows},
                         {'timeline.cast.sources':0,'timeline.cast.actor':0,'timeline.cast.binding':1})
        self.assertEqual(owners,[actor])

    def test_partial_replacement_failure_keeps_each_owner_for_retirement(self):
        from expedition33.cinematics.authored_replacement import _apply_snapshot
        from unittest.mock import Mock
        sequence=N(scope=N(_session=N(_transport=object())),_asset=object())
        path='/Game/Shot.Shot'
        edits=[dict(sequence=path,guid=f'{i:032x}',profile='sciel') for i in (1,2)]
        document=dict(source={},cast_edits=edits)
        source=object()
        first,second=Mock(),Mock()
        second.prepare.side_effect=RuntimeError('second spawn failed')
        owners=[]
        with patch('expedition33.cinematics.authored_replacement.sources_for',return_value={path:source}), \
             patch('expedition33._timeline_actor_channel.validate_count'), \
             patch('expedition33.cinematics.blueprint_actor.BlueprintActor',side_effect=(first,second)), \
             patch('expedition33.cinematics.binding_overrides.bind_actor') as bind:
            with self.assertRaisesRegex(RuntimeError,'second spawn failed'):
                _apply_snapshot(sequence,document,(0,0,0),owners=owners)
            self.assertEqual(owners,[first,second])
            bind.assert_called_once()
        # A failure in the binding itself must retain the newly spawned actor too.
        actor=Mock();owners=[]
        with patch('expedition33.cinematics.authored_replacement.sources_for',return_value={path:source}), \
             patch('expedition33._timeline_actor_channel.validate_count'), \
             patch('expedition33.cinematics.blueprint_actor.BlueprintActor',return_value=actor), \
             patch('expedition33.cinematics.binding_overrides.bind_actor',side_effect=RuntimeError('bind failed')):
            with self.assertRaisesRegex(RuntimeError,'bind failed'):
                _apply_snapshot(sequence,document,(0,0,0),owners=owners)
            self.assertEqual(owners,[actor])
        with self.assertRaisesRegex(ValueError,'owner journal'):
            _apply_snapshot(sequence,document,(0,0,0),owners=[actor])

    def test_public_apply_failure_is_retained_by_sequence_owner(self):
        from expedition33.cinematics.authored_replacement import apply
        from unittest.mock import Mock
        document=self.document();path=document['source']['sequence']
        document=replace_cast(document,path,'00000001000000000000000000000000','sciel')
        sequence=N(scope=N(_session=N(_transport=object())),_asset=object())
        actor=Mock();actor.prepare.side_effect=RuntimeError('construction failed')
        with patch('expedition33.cinematics.authored_replacement.sources_for',return_value={path:object()}), \
             patch('expedition33._timeline_actor_channel.validate_count'), \
             patch('expedition33.cinematics.blueprint_actor.BlueprintActor',return_value=actor):
            with self.assertRaisesRegex(RuntimeError,'construction failed'):
                apply(sequence,document,(0,0,0))
        self.assertEqual(sequence._authored_actor_journals,[[actor]])

    def test_sequence_actor_cleanup_is_retryable_in_normal_and_retired_worlds(self):
        from expedition33.sequences import OwnedLevelSequence,SequenceCleanupDeferred
        from unittest.mock import Mock
        for retiring in (False,True):
            with self.subTest(retiring=retiring):
                sequence=object.__new__(OwnedLevelSequence);sequence.state='ready';sequence._endpoint=None
                sequence.owner=Mock();sequence.owner._retiring=False
                sequence.owner.close.return_value=True;sequence.owner.retire_world.return_value=True
                sequence.scope=Mock();sequence.planner=None
                first,second=Mock(),Mock();sequence._authored_actor_journals=[[first,second]]
                method='retire_world' if retiring else 'close'
                getattr(first,method).return_value=True
                getattr(second,method).side_effect=(False,True)
                with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):
                    if retiring:self.assertFalse(sequence.retire_world())
                    else:
                        with self.assertRaises(SequenceCleanupDeferred):sequence.close()
                    self.assertEqual(sequence._authored_actor_journals,[[first,second]])
                    sequence.scope.close.assert_not_called()
                    if retiring:self.assertTrue(sequence.retire_world())
                    else:sequence.close()
                self.assertEqual(sequence.state,'closed');self.assertEqual(sequence._authored_actor_journals,[])
                self.assertEqual(getattr(first,method).call_count,2)
                self.assertEqual(getattr(second,method).call_count,2)

    def test_public_apply_validates_and_isolates_the_callers_document(self):
        from expedition33.cinematics.authored_replacement import apply
        document=self.document()
        with patch('expedition33.cinematics.authored_replacement._apply_snapshot',return_value=()) as apply_snapshot:
            self.assertEqual(apply(N(),document,(0,0,0)),())
            snapshot=apply_snapshot.call_args.args[1]
            self.assertEqual(snapshot,document)
            self.assertIsNot(snapshot,document)
            self.assertIsNot(snapshot['source'],document['source'])
            document['source']['nodes'].clear()
            self.assertTrue(snapshot['source']['nodes'])
            with self.assertRaises(ValueError):apply(N(),document,(0,0,0))
            self.assertEqual(apply_snapshot.call_count,1)

    def test_owned_snapshot_still_requires_fresh_source_membership_before_spawning(self):
        from expedition33.cinematics.authored_replacement import _apply_snapshot
        document=self.document();seq=document['source']['sequence']
        document=replace_cast(document,seq,'00000001000000000000000000000000','sciel')
        scope=N(_session=N(_transport=N()))
        with patch('expedition33._timeline_actor_channel.validate_count'), \
             patch('expedition33.cinematics.authored_replacement.sources_for',side_effect=ValueError('membership changed')) as sources, \
             patch('expedition33.cinematics.blueprint_actor.BlueprintActor') as actor:
            with self.assertRaisesRegex(ValueError,'membership changed'):
                _apply_snapshot(N(scope=scope,_asset=N()),document,(0,0,0))
            sources.assert_called_once()
            actor.assert_not_called()

    def test_multiple_cast_sources_share_one_fresh_hierarchy_without_caching(self):
        from expedition33.cinematics.authored_replacement import sources_for
        paths=('/Game/A.A','/Game/B.B')
        originals=tuple(N(index=i,serial=1,address=i*256) for i in (1,2))
        private=tuple(N(index=i,serial=2,address=i*256) for i in (3,4))
        root=N(index=5,serial=1,address=1280)
        sigs=((1,2,3,4),(5,6,7,8))
        nodes={}
        for path,sig in zip(paths,sigs):
            scene=path+':MovieScene'
            nodes[path]=dict(class_name='LevelSequence',fields=dict(MovieScene=dict(object_path=scene)))
            nodes[scene]=dict(fields=dict(Signature=dict(struct='/Script/CoreUObject.Guid',
                complete=True,errors={},fields=dict(zip('ABCD',sig)))))
        prefix='expedition33.cinematics.authored_replacement.'
        def signatures(scope,objects):
            return tuple(sigs[(o.index-1)%2] if o.index!=5 else (9,9,9,9) for o in objects)
        with patch(prefix+'load_asset',side_effect=lambda scope,path:N(return_value=originals[paths.index(path)])),\
             patch(prefix+'_sequence_signatures',side_effect=signatures) as reads,\
             patch(prefix+'reachable_sequences',return_value=(root,*private)) as membership:
            for _ in range(2):
                self.assertEqual(sources_for(N(pid=42),root,dict(nodes=nodes),(*paths,paths[0])),dict(zip(paths,private)))
            self.assertEqual(membership.call_count,2) # Each apply revalidates membership.
            self.assertEqual(reads.call_count,2) # One shared signature batch per apply.
            membership.return_value=(root,private[0])
            with self.assertRaisesRegex(ValueError,'absent'):
                sources_for(N(pid=42),root,dict(nodes=nodes),paths)
    def test_combined_signature_observation_is_bounded_and_rejects_changed_sources(self):
        from expedition33.cinematics.authored_replacement import sources_for
        paths=tuple('/Game/S'+str(i)+'.S'+str(i) for i in range(128))
        originals=tuple(N(index=i,serial=1,address=i*256) for i in range(1,129))
        copies=tuple(N(index=i+128,serial=2,address=(i+128)*256) for i in range(1,129))
        nodes={}
        for i,path in enumerate(paths,1):
            scene=path+':MovieScene'
            nodes[path]=dict(class_name='LevelSequence',fields=dict(MovieScene=dict(object_path=scene)))
            nodes[scene]=dict(fields=dict(Signature=dict(struct='/Script/CoreUObject.Guid',
                complete=True,errors={},fields=dict(A=i,B=0,C=0,D=0))))
        prefix='expedition33.cinematics.authored_replacement.'
        def signatures(scope,objects):
            self.assertLessEqual(len(objects),128)
            return tuple(((o.index-1)%128+1,0,0,0) for o in objects)
        with patch(prefix+'load_asset',side_effect=lambda scope,path:N(return_value=originals[paths.index(path)])), \
             patch(prefix+'reachable_sequences',return_value=copies), \
             patch(prefix+'_sequence_signatures',side_effect=signatures) as reads:
            result=sources_for(N(pid=42),copies[0],dict(nodes=nodes),paths)
            self.assertEqual(result,dict(zip(paths,copies)))
            self.assertEqual(reads.call_count,2)
        # When original and playback source are identical, observe it just once.
        with patch(prefix+'load_asset',return_value=N(return_value=originals[0])), \
             patch(prefix+'reachable_sequences',return_value=(originals[0],)), \
             patch(prefix+'_sequence_signatures',return_value=((1,0,0,0),)) as reads:
            self.assertIs(sources_for(N(pid=42),originals[0],dict(nodes=nodes),paths[:1])[paths[0]],originals[0])
            self.assertEqual(reads.call_args.args[1],(originals[0],))

    def test_signature_batch_keeps_ownership_and_complete_projection_checks(self):
        from expedition33.cinematics.authored_replacement import _sequence_signatures
        sequences=(N(index=1,serial=2,address=0x10000),N(index=3,serial=4,address=0x20000))
        scenes=(N(index=11,serial=12,address=0x30000,class_name='MovieScene',outer_index=1,outer_serial=2),
                N(index=13,serial=14,address=0x40000,class_name='MovieScene',outer_index=3,outer_serial=4))
        def row(name,value):return N(errors={},truncated=False,values={(0,name):value})
        first={o.index:row('MovieScene',scene) for o,scene in zip(sequences,scenes)}
        sig=dict(struct='/Script/CoreUObject.Guid',complete=True,errors={},fields=dict(A=1,B=2,C=3,D=4))
        second={o.index:row('Signature',sig) for o in scenes}
        prefix='expedition33.cinematics.authored_replacement.'
        with patch(prefix+'capture_selected_values',side_effect=((N(),first),(N(),second))) as read,\
             patch(prefix+'copied',side_effect=lambda value,catalog:value):
            self.assertEqual(_sequence_signatures(N(pid=42),sequences),((1,2,3,4),(1,2,3,4)))
            self.assertEqual(read.call_count,2)
            self.assertTrue(all(c.kwargs['references'] for c in read.call_args_list))
        with patch(prefix+'capture_selected_values',side_effect=((N(),first),(N(),{11:second[11]}))),\
             self.assertRaisesRegex(ValueError,'Incomplete'):
            _sequence_signatures(N(pid=42),sequences)
        scenes[1].outer_serial=99
        with patch(prefix+'capture_selected_values',return_value=(N(),first)) as read,\
             self.assertRaisesRegex(ValueError,'ownership changed'):
            _sequence_signatures(N(pid=42),sequences)
        read.assert_called_once()
    def document(self):return create(fixture(),'Character replacement')
    def test_saved_blueprint_placement_roundtrips_and_survives_profile_change(self):
        from expedition33.cinematics.authored_replacement import placement_pose
        original=self.document();seq=original['source']['sequence'];guid='00000001000000000000000000000000'
        with self.assertRaisesRegex(ValueError,'before placing'):place_cast(original,seq,guid,[0,0,0],0)
        edited=place_cast(replace_cast(original,seq,guid,'lune'),seq,guid,[120.,-50.,25.],90.)
        with tempfile.TemporaryDirectory() as directory:
            store=TimelineStore(directory);edited=store.read(store.save(edited))
        edit=edited['cast_edits'][0];pose=placement_pose(edit,(100,200,300),0)
        self.assertEqual(pose[4:7],(220.,150.,325.));self.assertAlmostEqual(pose[2],2**-.5)
        self.assertAlmostEqual(pose[3],2**-.5)
        self.assertEqual(replace_cast(edited,seq,guid,'sciel')['cast_edits'][0]['placement'],edit['placement'])
        self.assertEqual(original['cast_edits'],[])
        for offset,yaw in (([0,0,float('nan')],0),([True,0,0],0),([100001,0,0],0),([0,0,0],181),([0,0,0],True)):
            with self.assertRaises(ValueError):place_cast(edited,seq,guid,offset,yaw)
    def test_saved_binding_uses_sequence_local_guid_without_runtime_handles(self):
        original=self.document();before=copy.deepcopy(original)
        sequence=original['source']['sequence'];guid='00000001000000000000000000000000'
        edited=replace_cast(original,sequence,guid,'sciel')
        self.assertEqual(original,before);self.assertEqual(edited['source'],before['source'])
        with tempfile.TemporaryDirectory() as directory:
            store=TimelineStore(directory);self.assertEqual(store.read(store.save(edited)),edited)
        self.assertNotIn('address',json.dumps(edited))
        changed=replace_cast(edited,sequence,guid,'verso');self.assertEqual(len(changed['cast_edits']),1)
        self.assertEqual(changed['cast_edits'][0]['profile'],'verso')
        self.assertEqual(replace_cast(changed,sequence,guid,None),original)
    def test_legacy_document_is_normalized_without_changing_source_digest(self):
        document=self.document();document.pop('cast_edits');expected=copy.deepcopy(document)
        normalized=validate(document)
        self.assertEqual(document,expected);self.assertEqual(normalized['cast_edits'],[])
        self.assertEqual(normalized['source_sha256'],document['source_sha256'])
    def test_unknown_binding_component_profile_and_duplicate_rejected(self):
        original=self.document();seq=original['source']['sequence'];guid='00000001000000000000000000000000'
        for path,key,profile in ((seq,guid,'unknown'),('/Game/Other.Other',guid,'sciel'),
                                 (seq,'00000002000000000000000000000000','sciel')):
            with self.assertRaises(ValueError):replace_cast(original,path,key,profile)
        edited=replace_cast(original,seq,guid,'lune');edited['cast_edits']*=2
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate(edited)
        edited=replace_cast(original,seq,guid,'lune');edited['cast_edits'][0]['address']=123
        with self.assertRaises(ValueError):validate(edited)
    def test_guid_conversion_preserves_signed_engine_words(self):
        self.assertEqual(guid_fields('80000000ffffffff000000017fffffff'),dict(A=-(1<<31),B=-1,C=1,D=(1<<31)-1))
        for value in (None,'0'*32,'f'*31,'G'*32,'F'*32):
            with self.assertRaises(ValueError):guid_fields(value)
    def test_private_source_selection_requires_live_membership_and_unique_signature(self):
        from expedition33.cinematics.authored_replacement import source_for
        from contextlib import ExitStack
        path='/Game/Shot.Shot';scene_path=path+':MovieScene'
        sig=dict(struct='/Script/CoreUObject.Guid',complete=True,errors={},fields=dict(A=1,B=2,C=3,D=4))
        graph=dict(nodes={path:dict(class_name='LevelSequence',fields=dict(MovieScene=dict(object_path=scene_path))),
                          scene_path:dict(fields=dict(Signature=sig))})
        original=N(index=1,serial=2,address=256);private=N(index=3,serial=4,address=512)
        root=N(index=5,serial=6,address=768);scope=N(pid=123)
        signatures={1:sig,3:sig,5:dict(sig,fields=dict(A=2,B=2,C=3,D=4))}
        with ExitStack() as stack:
            prefix='expedition33.cinematics.authored_replacement.'
            stack.enter_context(patch(prefix+'load_asset',lambda *a:N(return_value=original)))
            stack.enter_context(patch(prefix+'_sequence_signatures',side_effect=lambda scope,objects:tuple(tuple(signatures[o.index]['fields'][k] for k in 'ABCD') for o in objects)))
            with patch(prefix+'reachable_sequences',return_value=(root,private)):
                self.assertIs(source_for(scope,root,graph,path),private)
            with patch(prefix+'reachable_sequences',return_value=(root,original,private)),self.assertRaisesRegex(ValueError,'ambiguous'):
                source_for(scope,root,graph,path)
            with patch(prefix+'reachable_sequences',return_value=(root,)),self.assertRaisesRegex(ValueError,'absent'):
                source_for(scope,root,graph,path)
            signatures[1]=signatures[5]
            with patch(prefix+'reachable_sequences',return_value=(root,private)) as membership,self.assertRaisesRegex(ValueError,'changed since import'):
                source_for(scope,root,graph,path)
            membership.assert_called_once()
