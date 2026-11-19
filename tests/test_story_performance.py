import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from contextlib import contextmanager
from expedition33.story_performance import DialogueBodyPerformance,BASE

class BodyPerformanceTests(unittest.TestCase):
    def test_new_instance_lease_observes_every_clip_in_one_owned_capture(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance);owner.scope=object();owner.instance=None
        instance=N(index=1,serial=0,address=100);stable=N(index=1,serial=10,address=100)
        clips=(N(index=2,serial=3,address=200),N(index=4,serial=5,address=400))
        state=N(values={(20,'AnimationMode'):0,(20,'AnimScriptInstance'):instance},types={(20,'AnimationMode'):'ByteProperty',(20,'AnimScriptInstance'):'ObjectProperty'},errors={})
        catalog=object()
        with patch('expedition33._stable_lease.acquire_stable',return_value=(N(object=stable),catalog)) as retain,patch('expedition33.catalog.capture_selected') as read:
            self.assertIs(owner._body_call_observation(state,clips),catalog)
        retain.assert_called_once_with(owner.scope,instance,selectors=((2,3,200),(4,5,400)))
        read.assert_not_called();self.assertIs(owner.instance,stable)
    def test_existing_body_batch_cannot_rebind_an_instance_silently(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance);owner.scope=N(pid=7)
        owner.instance=N(index=1,serial=10,address=100)
        state=N(values={(20,'AnimationMode'):0,(20,'AnimScriptInstance'):N(index=1,serial=11,address=100)},types={(20,'AnimationMode'):'ByteProperty',(20,'AnimScriptInstance'):'ObjectProperty'},errors={})
        with patch('expedition33.catalog.capture_selected') as read:
            with self.assertRaisesRegex(RuntimeError,'instance changed'):owner._body_call_observation(state,())
        read.assert_not_called()
    def test_batch_prepares_every_loop_plan_from_one_fresh_body_observation(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance)
        owner.closed=owner.unknown=False;owner.current=owner.montage=None;owner.actor=(1,2,3);owner.player=True
        body=object();state=object();first=object();second=object()
        owner.media=N(preflight_reads=False,prepare_many=Mock(return_value=(body,state,((body,first,2.),(body,second,3.)))))
        observed=object();owner._body_call_observation=Mock(return_value=observed)
        owner._prepare_observed=Mock()
        owner.preflight_many((('a',1),('b',1),('a',10000)))
        owner.media.prepare_many.assert_called_once_with(owner.actor,({'asset':'a'},{'asset':'b'},{'asset':'a'}),player=True)
        from unittest.mock import call
        self.assertEqual(owner._prepare_observed.call_args_list,[call(body,first,state,1,observed=observed),call(body,second,state,1,observed=observed),call(body,first,state,10000,observed=observed)])
        owner._body_call_observation.assert_called_once_with(state,(first,second))
        self.assertFalse(owner.media.preflight_reads)
    def test_failed_batch_retains_plan_owner_and_restores_read_only_marker(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance)
        owner.closed=owner.unknown=False;owner.current=owner.montage=None;owner.actor=(1,2,3);owner.player=True
        owner.media=N(preflight_reads=False,prepare_many=Mock(side_effect=RuntimeError('read failed')))
        owner._prepare_observed=Mock()
        with self.assertRaisesRegex(RuntimeError,'read failed'):owner.preflight_many((('a',1),))
        self.assertFalse(owner.media.preflight_reads);owner._prepare_observed.assert_not_called()
        owner.current='active'
        with self.assertRaisesRegex(RuntimeError,'active body'):owner.preflight_many((('a',1),))
        self.assertEqual(owner.media.prepare_many.call_count,1)
    def test_warmed_body_rejects_changed_mesh_or_animation_instance(self):
        def obj(index):return N(index=index,serial=1,address=0x10000+16*index)
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance);owner.scope=N(pid=10);owner.actor=(1,1,0x10010)
        body=obj(2);mesh=obj(3);instance=obj(4)
        def identity(value):return value.index,value.serial,value.address
        owner.preflight_signature=(identity(body),identity(mesh),identity(instance),0)
        def values(**kw):return N(types={(1,k):'ObjectProperty' for k in kw},values={(1,k):v for k,v in kw.items()},errors={})
        with patch('expedition33.story_animation.body',return_value=body),patch('expedition33.values.capture_selected_values') as capture:
            capture.return_value=(None,{2:values(SkeletalMesh=mesh,AnimScriptInstance=instance,AnimationMode=0)})
            self.assertTrue(owner.matches_current())
            capture.return_value=(None,{2:values(SkeletalMesh=mesh,AnimScriptInstance=obj(5),AnimationMode=0)})
            self.assertFalse(owner.matches_current())
            capture.return_value=(None,{2:values(SkeletalMesh=obj(6),AnimScriptInstance=instance,AnimationMode=0)})
            self.assertFalse(owner.matches_current())

    def test_stop_targets_only_the_owned_montage(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance)
        owner.montage=object();montage=owner.montage;calls=[]
        @contextmanager
        def invoke(name,**kwargs):calls.append((name,kwargs));yield
        owner._invoke=invoke
        owner._stop()
        self.assertEqual(calls,[('Montage_Stop',dict(InBlendOutTime=.4,Montage=montage))])
        self.assertIsNone(owner.montage);self.assertFalse(owner.unknown)
    def test_brief_gesture_returns_to_source_idle_after_2_5_seconds(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance)
        owner.deadline=12.5;owner.play=Mock()
        with patch('expedition33.story_performance.time.monotonic',return_value=12.4):owner.poll()
        owner.play.assert_not_called()
        with patch('expedition33.story_performance.time.monotonic',return_value=12.5):owner.poll()
        owner.play.assert_called_once_with(BASE,10000)
    def test_unknown_playback_cannot_be_reported_closed(self):
        owner=DialogueBodyPerformance.__new__(DialogueBodyPerformance)
        owner.closed=False;owner.unknown=True
        self.assertFalse(owner.close());self.assertFalse(owner._closed)
