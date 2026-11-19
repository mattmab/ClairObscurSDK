import copy,importlib,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import test_story_authoring as authoring
import test_story_packs
from test_story_native_flow import Driver,NativeFlow
import test_story_runtime as fixtures
from test_story_view import StoryView
from expedition33.story_audio import DialogueAudio
snippet=dict(asset='/Game/Audio/Test.Test',volume=.75,start=2.,duration=3.)

class AudioAuthoringTests(unittest.TestCase):
    setUp=authoring.StoryAuthoringTests.setUp
    def test_speech_and_response_audio_are_independent_and_roundtrip(self):
        key=self.draft.document['dialogues']['first-meeting']['nodes']['welcome']['choices'][0]['id']
        self.draft.audio('first-meeting','welcome',None,snippet)
        self.draft.audio('first-meeting','welcome',key,dict(snippet,start=1.))
        saved=self.editor.open(self.draft.document['id']).document['dialogues']['first-meeting']['nodes']['welcome']
        self.assertEqual(saved['audio'],snippet);self.assertEqual(saved['choices'][0]['audio']['start'],1.)
        self.draft.audio('first-meeting','welcome',None,None)
        row=self.draft.document['dialogues']['first-meeting']['nodes']['welcome']
        self.assertNotIn('audio',row);self.assertIn('audio',row['choices'][0])
    def test_invalid_snippet_never_writes(self):
        before=self.draft.path.read_bytes()
        for change in ({'volume':float('nan')},{'duration':0},{'duration':301},{'start':-1},{'asset':'invalid'},{'volume':True}):
            with self.assertRaises(ValueError):self.draft.audio('first-meeting','welcome',None,dict(snippet,**change))
            self.assertEqual(before,self.draft.path.read_bytes())

class AudioFlowTests(unittest.TestCase):
    setUp=fixtures.StoryRuntimeTests.setUp
    def test_original_text_dispatches_before_media_and_response_never_waits(self):
        self.runtime.reconcile(fixtures.WORLD,(1,),ready=True)
        row=self.runtime.document['dialogues']['first-meeting']['nodes']['welcome']
        row['audio']=copy.deepcopy(snippet);row['choices'][0]['audio']=dict(snippet,start=1.)
        driver=Driver();events=[]
        start=driver.start_lines
        driver.start_lines=lambda *a:(events.append('text'),start(*a))[1]
        driver.animate_line=lambda v:events.append('animation')
        driver.play_audio=lambda a:events.append(('audio',a))
        flow=NativeFlow(self.runtime,driver);flow.interact([10,20,30])
        self.assertEqual(events[:3],['text','animation',('audio',snippet)])
        driver.event=dict(presentation=1,kind='lines');flow.poll()
        driver.event=dict(presentation=2,kind='choices',index=0);flow.poll()
        self.assertEqual(flow.stage,'lines');self.assertIn(('audio',dict(snippet,start=1.)),events)
    def test_unknown_audio_outcome_is_not_replayed(self):
        self.runtime.reconcile(fixtures.WORLD,(1,),ready=True)
        driver=Driver();driver.play_audio=Mock(side_effect=RuntimeError('unknown audio'))
        flow=NativeFlow(self.runtime,driver)
        with self.assertRaisesRegex(RuntimeError,'unknown audio'):flow.interact([10,20,30])
        self.assertFalse(flow.poll());driver.play_audio.assert_called_once()

class AudioOwnerTests(unittest.TestCase):
    def owner(self):
        owner=DialogueAudio.__new__(DialogueAudio);owner.active=None;owner.deadline=None;owner.failed=False;owner.calls={}
        owner.prepare=Mock(return_value='component');owner._call=Mock();owner.components=N(close=Mock(return_value=True));owner.scope=N(_native_owners=[owner.components])
        return owner
    def test_snippet_starts_at_offset_and_stops_on_deadline_without_sleep(self):
        owner=self.owner()
        with patch('expedition33.story_audio.time.monotonic',return_value=100.):owner.play(snippet)
        owner._call.assert_called_with('component','AudioComponent','Play',StartTime=2.)
        with patch('expedition33.story_audio.time.monotonic',return_value=102.9):owner.poll()
        self.assertEqual(owner._call.call_count,2)
        with patch('expedition33.story_audio.time.monotonic',return_value=103.):owner.poll()
        owner._call.assert_called_with('component','AudioComponent','Stop');self.assertIsNone(owner.active)
    def test_travel_uses_retirement_without_component_dispatch(self):
        owner=self.owner()
        with patch('expedition33._retired_tracking.close_lease_only_scope',return_value=True):self.assertTrue(owner.close(world_retired=True))
        owner.components.close.assert_not_called();owner._call.assert_not_called();self.assertFalse(owner.scope._native_owners)
    def test_deferred_cleanup_keeps_ownership(self):
        owner=self.owner();owner.components.close.return_value=False;owner.active='retained'
        self.assertFalse(owner.close());self.assertEqual(owner.active,'retained')

class AudioPickerTests(unittest.TestCase):
    def test_audio_graph_control_saves_only_selected_card(self):
        pack=test_story_packs.sample();save=Mock()
        model=N(live=N(choices=lambda:None,error=None),library=N(get=lambda _:copy.deepcopy(pack)),edit_pack=save)
        view=StoryView(N(_check=lambda:None),model);view.pack=pack['id'];view.dialogue='first-meeting';view.screen='story_graph'
        frame=view.render();control=next(c for c in frame.controls if c.label.startswith('Audio snippet'))
        frame=view.activate(frame.revision,control.token);self.assertEqual(view.screen,'story_audio')
        clip=next(c for c in frame.controls if c.enabled and view._commands[c.token][0]=='story_audio_select')
        view.activate(frame.revision,clip.token)
        self.assertEqual(view.screen,'story_graph');self.assertEqual(save.call_args.args[:5],(pack['id'],'audio','first-meeting','welcome',None))


class FlowBatchTests(unittest.TestCase):
    def test_response_dispatch_and_progression_share_short_lived_reader(self):
        from contextlib import contextmanager
        active=[];driver=Driver();calls=[]
        @contextmanager
        def operation():
            active.append(True)
            try:yield
            finally:active.pop()
        driver.operation=operation;driver.poll_media=lambda:calls.append(bool(active))
        flow=NativeFlow(N(),driver)
        self.assertFalse(flow.poll());self.assertEqual(calls,[True]);self.assertFalse(active)
class OwnedObservationTests(unittest.TestCase):
    def test_completion_reads_exact_owned_objects_in_one_batch(self):
        from expedition33.story_dialogue import observe_owned
        def obj(i):return N(index=i,serial=i+10,address=i*100)
        npc,system,dialogue=obj(1),obj(2),obj(3)
        def values(**kwargs):return N(types={(0,k):'ObjectProperty' for k in kwargs},values={(0,k):v for k,v in kwargs.items()},errors={})
        rows={1:values(IsInDialog=True,SpawnedDialog=dialogue),2:values(ActiveDialogue=dialogue,LastChoice=0),3:values(IsComplete=True)}
        catalog=N(by_index={1:npc,2:system,3:dialogue})
        with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)) as read:
            result=observe_owned(N(pid=9),(1,11,100),system,dialogue)
        self.assertTrue(result['complete']);self.assertEqual(result['choice'],0);read.assert_called_once()
        rows[2]=values(ActiveDialogue=obj(4),LastChoice=0)
        with patch('expedition33.values.capture_selected_values',return_value=(catalog,rows)):
            self.assertIsNone(observe_owned(N(pid=9),(1,11,100),system,dialogue))
