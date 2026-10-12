import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock
P=Path(__file__).resolve().parents[1]/'src/expedition33/cinematics'
def load(name,file):
 s=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
f=load('expedition33.cinematics.fullscreen_media_staged','fullscreen_media.py')
class CleanupTests(unittest.TestCase):
 def fixture(self):
  events=[];owner=Mock();owner.close.side_effect=lambda:events.append('media') or True
  audio=Mock();audio.close.side_effect=lambda:events.append('audio') or True
  overlay=f.FullscreenMedia.__new__(f.FullscreenMedia)
  overlay.state='opened';overlay._control_uncertain=False;overlay._removed=set()
  overlay.video=N(uncertain=False,native_owner=owner,close=lambda:events.append('video_scope'))
  overlay.audio_dependency=audio;overlay.action=None;overlay.label_frame=overlay.button=overlay.backdrop=None
  overlay.presentation=N(restore=lambda:events.append('restore'))
  return overlay,audio,events
 def test_media_then_audio_then_presentation(self):
  overlay,audio,events=self.fixture();self.assertTrue(overlay.close())
  self.assertEqual(events,['media','audio','video_scope','restore'])
 def test_pending_audio_keeps_visible_controls_and_presentation(self):
  overlay,audio,events=self.fixture();audio.close.side_effect=None;audio.close.return_value=False
  action=Mock();overlay.action=action
  self.assertFalse(overlay.close());self.assertEqual(events,['media']);action.remove.assert_not_called()
  self.assertEqual(overlay.state,'cleanup_pending')
  audio.close.return_value=True;self.assertTrue(overlay.close());action.remove.assert_called_once()
 def test_unknown_audio_keeps_presentation_and_failure_evidence(self):
  overlay,audio,events=self.fixture();audio.close.side_effect=RuntimeError('quarantined')
  with self.assertRaisesRegex(RuntimeError,'quarantined'):overlay.close()
  self.assertEqual(events,['media']);self.assertEqual(overlay.state,'cleanup_pending')
 def test_original_pause_precedes_video_play(self):
  overlay,audio,events=self.fixture();overlay.state='prepared'
  audio.start.side_effect=lambda:events.append('pause_original')
  overlay.presentation.suspend=lambda:events.append('hide_menu');overlay.video.play=lambda:events.append('play')
  overlay.play();self.assertEqual(events,['pause_original','hide_menu','play'])
if __name__=='__main__':unittest.main()
