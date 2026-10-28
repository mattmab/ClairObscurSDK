import unittest
from expedition33.cinematics.media_audio_timeline import *
class PlannerTests(unittest.TestCase):
 def section(self,**kw):
  args=dict(identity='s',source='/Game/Audio/Exact.Exact',start=0.,end=1.,source_offset=5.,gain=lambda t:1.);args.update(kw);return Section(**args)
 def test_gain_precedes_source_offset_play_and_commit_is_explicit(self):
  p=MediaAudioPlanner([self.section()],capacity=32);s=p.plan(.1,playing=True)
  self.assertEqual(s.actions,(Action('gain','s',1.),Action('play','s',5.1)));self.assertFalse(p.active)
  with self.assertRaises(RuntimeError):p.plan(.11,playing=True)
  p.commit(s);self.assertEqual(p.active,frozenset(['s']));self.assertEqual(p.plan(.2,playing=True).actions,())
 def test_async_open_is_not_audio_start(self):
  p=MediaAudioPlanner([self.section()],capacity=32);self.assertIsNone(p.plan(0,playing=False));self.assertIsNone(p.pending)
 def test_backward_large_jump_and_missed_start_fail(self):
  for start,end in ((.1,.09),(.1,.5)):
   p=MediaAudioPlanner([self.section()],capacity=32);p.commit(p.plan(start,playing=True))
   with self.assertRaises(RuntimeError):p.plan(end,playing=True)
  with self.assertRaises(RuntimeError):MediaAudioPlanner([self.section()],capacity=32).plan(1.,playing=True)
 def test_ended_section_stops_and_suppresses_source_replay(self):
  p=MediaAudioPlanner([self.section(end=.15)],capacity=32);p.commit(p.plan(.1,playing=True));s=p.plan(.2,playing=True)
  self.assertEqual(s.actions,(Action('stop','s'),));p.commit(s);self.assertFalse(p.active)
 def test_native_bound_applies_to_complete_section_set_not_overlap(self):
  sections=[self.section(identity=str(i),start=float(i),end=float(i)+.5) for i in range(26)]
  with self.assertRaises(ValueError):MediaAudioPlanner(sections,capacity=16)
  self.assertEqual(len(MediaAudioPlanner(sections,capacity=32).sections),26)
 def test_authored_gain2_supported_only_if_advertised_and_never_clamped(self):
  section=self.section(gain=lambda _:2.)
  with self.assertRaises(ValueError):MediaAudioPlanner([section],capacity=32).plan(0,playing=True)
  self.assertEqual(MediaAudioPlanner([section],capacity=32,volume_max=2).plan(0,playing=True).actions[0].value,2.)
 def test_lost_media_playback_cannot_leave_active_audio_running(self):
  p=MediaAudioPlanner([self.section()],capacity=32);p.commit(p.plan(0,playing=True))
  with self.assertRaises(RuntimeError):p.plan(0,playing=False)
 def test_forged_commit_rejected_without_changing_state(self):
  p=MediaAudioPlanner([self.section()],capacity=32);s=p.plan(0,playing=True)
  with self.assertRaises(RuntimeError):p.commit(Step(s.serial,s.position,s.actions,s.active,s.gains))
  self.assertIs(p.pending,s);self.assertFalse(p.active)
if __name__=='__main__':unittest.main()

class ElapsedClockTests(unittest.TestCase):
 def planner(self):
  return MediaAudioPlanner([Section('s','/Game/Audio/Exact.Exact',0.,20.,0.,lambda _:1.)],capacity=32)
 def test_live_one_second_poll_gap_is_normal_elapsed_playback(self):
  p=self.planner();p.commit(p.plan(.033333,playing=True))
  step=p.plan(1.066666,playing=True,elapsed=1.04)
  self.assertEqual(step.position,1.066666);self.assertEqual(step.actions,())
 def test_forward_seek_exceeding_elapsed_budget_and_every_backward_seek_fail(self):
  for position,elapsed in ((1.066666,.05),(.02,20.)):
   p=self.planner();p.commit(p.plan(.033333,playing=True))
   with self.assertRaises(RuntimeError):p.plan(position,playing=True,elapsed=elapsed)
   self.assertIsNone(p.pending);self.assertEqual(p.position,.033333)
 def test_bad_monotonic_interval_and_missed_initial_start_still_reject(self):
  for elapsed in (-1.,float('nan'),float('inf'),True):
   with self.assertRaises(ValueError):self.planner().plan(.01,playing=True,elapsed=elapsed)
  with self.assertRaises(RuntimeError):self.planner().plan(1.1,playing=True,elapsed=10.)
 def test_dispatcher_anchor_includes_time_spent_in_acknowledged_native_work(self):
  from contextlib import nullcontext
  from types import SimpleNamespace as N
  from unittest.mock import Mock
  from expedition33.cinematics.owned_audio_timeline import OwnedAudioTimelineDispatcher
  ticks=iter((10.,11.04,11.09))
  audio=N(scope=N(_session=N(_transport=N(owned_sound_capacity=32,owned_sound_volume_max=1))),_sounds=[])
  planner=Mock();planner.prepare.return_value.invoke.side_effect=lambda:nullcontext()
  current_planner=OwnedAudioTimelineDispatcher.__init__.__globals__['MediaAudioPlanner']
  current_section=current_planner.__init__.__globals__['Section']
  section=current_section('s','/Game/Audio/Exact.Exact',0.,20.,0.,lambda _:1.)
  dispatcher=OwnedAudioTimelineDispatcher(audio,planner,None,[section],clock=lambda:next(ticks))
  dispatcher.prepared=True;dispatcher.components={'s':object()};dispatcher.functions={key:object() for key in ('Play','Stop','SetVolumeMultiplier')}
  dispatcher.advance(.033333,playing=True);dispatcher.advance(1.066666,playing=True)
  with self.assertRaises(RuntimeError):dispatcher.advance(2.,playing=True)
  self.assertEqual(dispatcher.timeline.position,1.066666)
