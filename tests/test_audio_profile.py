import importlib.util,json,sys,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'src/expedition33/cinematics'
def load(name,file):
    spec=importlib.util.spec_from_file_location(name,P/file);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
curve=load('expedition33.cinematics.audio_curve','audio_curve.py')
load('expedition33.cinematics.media_audio_timeline','media_audio_timeline.py')
profile=load('expedition33.cinematics.audio_profile','audio_profile.py')
class ProfileTests(unittest.TestCase):
    def test_exact_authored_offsets_and_external_gain_preserved(self):
        data=json.loads((P/'aliciabirth_audio.json').read_text());rows=profile.decode_sections(data)
        self.assertTrue(data['admitted']);self.assertEqual(len(rows),26)
        offset=next(r for r in rows if r.source_offset)
        self.assertAlmostEqual(offset.source_offset,3484000/24000)
        voiced=next(r for r in rows if r.identity=='MovieSceneAudioSection_32')
        self.assertEqual(voiced.gain(voiced.start),2.)
    def test_second_music_keys_use_root_frames_not_channel_rate(self):
        rows=profile.decode_sections(json.loads((P/'aliciabirth_audio.json').read_text()))
        music=next(r for r in rows if r.source_offset)
        self.assertAlmostEqual(music.gain(2811200/24000),.25)
        self.assertEqual(music.gain(music.start),0.)
    def test_linear_ease_factors_multiply_and_zero_duration_is_identity(self):
        c=curve.UnweightedCubicChannel([],default=2.)
        gain=curve.SectionGain(c,0,100,80,80,1)
        self.assertAlmostEqual(gain(50),2*(50/80)*(50/80))
        self.assertEqual(curve.SectionGain(c,0,100)(0),2.)
        self.assertEqual(gain(100),0.)
    def test_missing_exact_schema_does_not_silently_default(self):
        data=json.loads((P/'aliciabirth_audio.json').read_text());del data['sections'][0]['ease_out']
        with self.assertRaises(KeyError):profile.decode_sections(data)
if __name__=='__main__':unittest.main()
