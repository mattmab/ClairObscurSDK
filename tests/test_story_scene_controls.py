import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.scene_packs import Playback
from expedition33._runtime_scene_wire import validate_request,SIZE
from expedition33.scene_captions import SceneCaptions


class StorySceneControlsTests(unittest.TestCase):
    def test_control_hint_passes_real_panel_label_ownership_guard(self):
        panel=SceneCaptions.__new__(SceneCaptions)
        panel._spawn=Mock(side_effect=[N(index=1),N(index=2),N(index=3)]);panel._class=Mock()
        panel._place=Mock();panel._call=Mock();panel._render_call=Mock()
        panel.labels=[];panel.widget=object();panel.invisible=0;panel.collapsed=1;panel.state='built';panel._text={}
        panel._build_contents()
        panel.set_text(panel.controls,'Paused | E Resume')
        panel._render_call.assert_called_once()

    def packet(self,op):
        p=bytearray(SIZE);struct.pack_into('<4IQ',p,0,7,op,0,0,1);return p

    def test_controls_are_bounded_and_require_zero_unused_options(self):
        for action in (8.,9.,10.):
            p=self.packet(79);struct.pack_into('<2d',p,88,action,0.)
            validate_request(bytes(p),protocol=7)
            struct.pack_into('<d',p,96,1.)
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)
        p=self.packet(79);struct.pack_into('<2d',p,88,11.,0.)
        with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)

    def test_play_preserves_legacy_start_and_checks_pause_identity(self):
        p=self.packet(71);struct.pack_into('<d',p,88,2.)
        validate_request(bytes(p),protocol=7)
        struct.pack_into('<iiQ',p,96,123,4,0x1234)
        validate_request(bytes(p),protocol=7)
        p[112]=1
        with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)
        p[112]=0;struct.pack_into('<iiQ',p,96,123,4,0)
        with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)

    def playback(self,state='playing',scope=None):
        p=Playback.__new__(Playback);p.started=True;p.closed=False;p.document={'captions':[]}
        p.runtime=N(poll=Mock(),status=lambda:dict(state=state,elapsed=4.,paused=True,skip_progress=.5),scope=scope)
        p.captions=Mock();p.input_panel=Mock();return p

    def test_pause_keeps_caption_and_input_owners(self):
        p=self.playback()
        self.assertEqual(p.poll(),'playing')
        p.captions.update.assert_called_once_with([],4.,paused=True,skip_progress=.5)
        p.input_panel.close.assert_not_called()

    def test_finished_waits_for_input_cleanup_before_completing(self):
        p=self.playback('finished');panel=p.input_panel
        panel.close.side_effect=[False,True]
        self.assertEqual(p.poll(),'cleanup_pending');self.assertFalse(p.closed)
        self.assertEqual(p.poll(),'finished');self.assertTrue(p.closed)
        self.assertIsNone(p.input_panel)

    def test_abort_retains_input_until_native_owner_released(self):
        p=self.playback(scope=object());p.runtime.stop=Mock()
        self.assertFalse(p.close());p.input_panel.close.assert_not_called()
        p.runtime.scope=None
        self.assertTrue(p.close());self.assertIsNone(p.input_panel)

    def test_world_retirement_uses_retirement_not_gameplay_restore(self):
        p=self.playback();panel=p.input_panel
        p.runtime.retire_world=lambda:'ack';panel.retire_world.return_value='ack'
        self.assertEqual(p.retire_world(),'ack')
        panel.retire_world.assert_called_once_with(native_retirement_ack=True)
        panel.close.assert_not_called();self.assertTrue(p.closed)


if __name__=='__main__':unittest.main()
