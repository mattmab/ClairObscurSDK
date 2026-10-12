import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,MagicMock
P=Path(__file__).resolve().parents[1]/'src/expedition33/cinematics'

def load(name,file):
 spec=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
plan=load('expedition33.cinematics.media_audio_timeline','media_audio_timeline.py');curve=load('audio_curve','audio_curve.py');dispatch=load('expedition33.cinematics.owned_audio_timeline','owned_audio_timeline.py')
class CurveTests(unittest.TestCase):
 def test_constants_and_boundary_extrapolation(self):
  c=curve.UnweightedCubicChannel([],default=2.);self.assertEqual(c.evaluate(1),2.)
  c=curve.UnweightedCubicChannel([curve.CubicKey(10,.2,0.,0.),curve.CubicKey(20,.8,0.,0.)],default=1.)
  self.assertEqual(c.evaluate(0),.2);self.assertEqual(c.evaluate(30),.8);self.assertAlmostEqual(c.evaluate(15),.5)
 def test_tangent_is_scaled_by_raw_frame_delta(self):
  c=curve.UnweightedCubicChannel([curve.CubicKey(0,0.,0.,.1),curve.CubicKey(10,1.,.1,0.)],default=0.)
  self.assertAlmostEqual(c.evaluate(2.5),.25)
 def test_duplicate_or_nonfinite_keys_rejected(self):
  with self.assertRaises(ValueError):curve.UnweightedCubicChannel([curve.CubicKey(0,1.,0.,0.),curve.CubicKey(0,2.,0.,0.)],default=1.)
  with self.assertRaises(ValueError):curve.UnweightedCubicChannel([curve.CubicKey(0,float('nan'),0.,0.)],default=1.)
class DispatcherTests(unittest.TestCase):
 def fixture(self):
  source=N(path='/Game/A.A');component=object();objects=[N(index=1,name='AudioComponent',class_name='Class',outer_index=-1),N(index=2,name='Default__AudioComponent',class_index=1,outer_index=-1,class_name='AudioComponent')]
  objects += [N(index=i+3,name=n,outer_index=1,class_name='Function') for i,n in enumerate(('Play','Stop','SetVolumeMultiplier'))]
  catalog=N(objects=objects,resolve=lambda x:x,path_name=lambda x:x.path)
  planner=N(_catalog=catalog,prepare=Mock(side_effect=lambda *a,**k:MagicMock()))
  owner=N(scope=N(_session=N(_transport=N(owned_sound_capacity=32,owned_sound_volume_max=2))),_sounds=[],create_sound=Mock(return_value=component),close=Mock(return_value=True))
  section=plan.Section('one',source.path,0.,1.,0.,lambda _:1.)
  d=dispatch.OwnedAudioTimelineDispatcher(owner,planner,object(),[section]);return d,owner,planner,source
 def test_preflight_does_not_dispatch_and_every_start_is_owned(self):
  d,owner,planner,source=self.fixture();d.prepare({source.path:source});owner.create_sound.assert_called_once();self.assertEqual(owner.create_sound.call_args.kwargs,{'volume':0.,'pitch':1.})
  result=d.advance(.1,playing=True);self.assertEqual(result['actions'],2);self.assertEqual(d.timeline.position,.1)
 def test_missing_exact_source_precedes_component_allocation(self):
  d,owner,planner,source=self.fixture()
  with self.assertRaises(ValueError):d.prepare({})
  owner.create_sound.assert_not_called()
 def test_unknown_dispatch_never_retries_and_cleanup_deferral_keeps_step(self):
  d,owner,planner,source=self.fixture();d.prepare({source.path:source});prepared=MagicMock();prepared.invoke.side_effect=RuntimeError('unknown');planner.prepare.return_value=prepared;planner.prepare.side_effect=None
  with self.assertRaises(RuntimeError):d.advance(.1,playing=True)
  self.assertTrue(d.uncertain);pending=d.timeline.pending
  with self.assertRaises(RuntimeError):d.advance(.1,playing=True)
  owner.close.return_value=False;self.assertFalse(d.close_audio());self.assertIs(d.timeline.pending,pending)
  owner.close.return_value=True;self.assertTrue(d.close_audio());self.assertIsNone(d.timeline.pending)
if __name__=='__main__':unittest.main()
