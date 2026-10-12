import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
P=Path(__file__).resolve().parents[1]/'src/expedition33/cinematics'
spec=importlib.util.spec_from_file_location('expedition33.cinematics.media_audio_context',P/'media_audio_context.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
class ContextTests(unittest.TestCase):
    def fixture(self):
        caps=N(**dict.fromkeys(('music_audio_protocol','owned_sound_protocol','original_audio_pause_protocol','owned_audio_cleanup_protocol'),1))
        return N(_session=N(_transport=caps))
    def test_capability_check_precedes_retention_and_rejects_bool(self):
        session=self.fixture();session._session._transport.owned_audio_cleanup_protocol=True
        with patch.object(m,'SessionScope') as scope:
            with self.assertRaises(RuntimeError):m.MediaAudioContext(session,object())
            scope.assert_not_called()
    def test_deferred_cleanup_preserves_scope_then_closes_once(self):
        scope=Mock();audio=Mock();audio.close.side_effect=[False,True]
        with patch.object(m,'SessionScope',return_value=scope):context=m.MediaAudioContext(self.fixture(),object())
        context.audio=audio
        self.assertFalse(context.close());scope.close.assert_not_called()
        self.assertTrue(context.close());scope.close.assert_called_once()
        self.assertTrue(context.close());self.assertEqual(audio.close.call_count,2)
    def test_unknown_cleanup_cannot_drop_scope(self):
        scope=Mock()
        with patch.object(m,'SessionScope',return_value=scope):context=m.MediaAudioContext(self.fixture(),object())
        context.audio=Mock();context.audio.close.side_effect=RuntimeError('unknown owner state')
        with self.assertRaises(RuntimeError):context.close()
        scope.close.assert_not_called();self.assertFalse(context.closed)
if __name__=='__main__':unittest.main()
