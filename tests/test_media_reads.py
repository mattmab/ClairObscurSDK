import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,MagicMock
from expedition33._pod_values import TimespanValue
from expedition33 import media as m
class Reads(unittest.TestCase):
 def fixture(self):
  v=m.OwnedVideoWidget.__new__(m.OwnedVideoWidget);v.state='opened';v.uncertain=False;v.player=object()
  v._read_planner=None;v._reads={};v._function=lambda owner,name:name
  planner=Mock();calls={}
  def prepare(target,name):
   p=Mock();result=MagicMock();result.__enter__.return_value=N(return_value=TimespanValue(10) if name in ('GetTime','GetDuration') else True)
   p.invoke.return_value=result;calls[name]=p;return p
  planner.prepare.side_effect=prepare
  v.scope=N(_session=N(_transport=N(timespan_values_protocol=1)),invocation_planner=Mock(return_value=planner))
  v.planner=Mock();return v,planner,calls
 def test_warms_once_and_scalar_reads_do_not_refresh(self):
  v,p,c=self.fixture();v.prepare_reads();self.assertEqual(p.prepare.call_count,6)
  v.playback_status();v.playback_status();self.assertEqual(p.prepare.call_count,6)
  self.assertEqual(c['IsPlaying'].invoke.call_count,2)
  c['IsPlaying'].invoke.assert_called_with()
  c['IsReady'].invoke.assert_not_called();c['IsClosed'].invoke.assert_not_called()
 def test_audio_position_omits_duration(self):
  v,p,c=self.fixture();self.assertEqual(v.media_position()['time_ticks'],10)
  c['GetDuration'].invoke.assert_not_called();c['GetTime'].invoke.assert_called_once_with()
 def test_closed_and_uncertain_never_dispatch(self):
  v,p,c=self.fixture();v.uncertain=True
  with self.assertRaises(RuntimeError):v.media_position()
  p.prepare.assert_not_called()
if __name__=='__main__':unittest.main()
