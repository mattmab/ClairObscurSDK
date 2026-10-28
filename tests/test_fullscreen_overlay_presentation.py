import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.media_presentation import FullscreenOverlayPresentation
from expedition33.cinematics.fullscreen_media import FullscreenMedia

class OverlayPresentationTests(unittest.TestCase):
 def menu(self):
  panel=N(state='open',uncertain=False,children=[object() for _ in range(750)],scope=Mock())
  return N(panel=panel,_presentation_owner=None,_presentation_suspended=False,_restore_presentation_frame=Mock())
 def test_large_workspace_does_not_read_or_mutate_children(self):
  menu=self.menu();p=FullscreenOverlayPresentation(menu,Mock());p.prepare();p.suspend()
  menu.panel.scope.assert_not_called();self.assertIsNone(p.planner)
  self.assertTrue(menu._presentation_suspended);self.assertIs(menu._presentation_owner,p)
  with self.assertRaises(RuntimeError):p.restore()
  menu._restore_presentation_frame.assert_not_called()
  p.acknowledge_overlay_closed();p.restore()
  menu._restore_presentation_frame.assert_called_once();self.assertFalse(menu._presentation_suspended)
 def test_exclusive_owner_and_changed_context_never_repaint_foreign_menu(self):
  menu=self.menu();p=FullscreenOverlayPresentation(menu,Mock()).prepare()
  foreign=object();menu._presentation_owner=foreign
  with self.assertRaises(RuntimeError):p.suspend()
  self.assertIs(menu._presentation_owner,foreign)
  menu._presentation_owner=None;p.suspend();p.acknowledge_overlay_closed();menu.panel=object()
  with self.assertRaises(RuntimeError):p.restore()
  menu._restore_presentation_frame.assert_not_called()
 def test_build_retains_presentation_before_video_work_and_prepares_after_overlay(self):
  menu=self.menu();video=Mock();events=[]
  with patch('expedition33.cinematics.fullscreen_media.OwnedVideoWidget',return_value=video):owner=FullscreenMedia(object())
  video.build.side_effect=lambda *a:events.append(('video',owner.presentation.state))
  owner._build_stop=lambda callback:events.append(('overlay',owner.presentation.state))
  owner.build(menu,'movie',Mock())
  self.assertEqual(events,[('video','new'),('overlay','new')]);self.assertEqual(owner.presentation.state,'prepared')
 def test_native_or_action_deferral_keeps_overlay_gate_until_every_close_ack(self):
  menu=self.menu();video=Mock(uncertain=False);video.native_owner.close.side_effect=[False,True,True]
  with patch('expedition33.cinematics.fullscreen_media.OwnedVideoWidget',return_value=video):owner=FullscreenMedia(object())
  owner.menu=menu;owner.presentation=FullscreenOverlayPresentation(menu,Mock()).prepare();owner.presentation.suspend()
  owner.action=Mock();owner.action.remove.side_effect=[False,True]
  owner.button=object();owner.label_frame=object();owner.backdrop=object();owner.state='opened'
  self.assertFalse(owner.close());self.assertFalse(owner.close())
  self.assertTrue(menu._presentation_suspended);menu._restore_presentation_frame.assert_not_called();video.close.assert_not_called()
  self.assertTrue(owner.close());video.close.assert_called_once();menu._restore_presentation_frame.assert_called_once()
  self.assertEqual(owner.presentation.state,'restored')

class OwnedOverlayLayerTests(unittest.TestCase):
 def test_owned_canvas_slots_have_explicit_backdrop_video_stop_label_order(self):
  from expedition33.cinematics import fullscreen_media as full
  panel=N(tree=object(),canvas=object(),invisible=object(),state='open',menu=N(bind_control=Mock(return_value=Mock())))
  video=Mock();video.scope=N(pid=7)
  catalog=N(objects=[N(name='Default__GameplayStatics'),N(name='CTS_B1_SmallLine_Outline_C')]);catalog.with_observations=lambda _:catalog
  video.planner=N(_catalog=catalog,refresh_from=Mock());video._one=lambda rows:list(rows)[0];video._class=lambda name:name
  video._invoke.side_effect=lambda *a,**k:N(return_value=object())
  video.attach_fullscreen.return_value=object()
  with patch.object(full,'OwnedVideoWidget',return_value=video):owner=full.FullscreenMedia(object())
  owner.menu=N(panel=panel)
  with patch.object(full,'capture_matching',return_value=catalog):owner._build_stop(Mock())
  z=[(call.args[0],call.kwargs['InZOrder']) for call in video._call.call_args_list if call.args[2]=='SetZOrder']
  self.assertEqual([value for slot,value in z],[10000,10001,10002,10003])
  self.assertEqual(len({id(slot) for slot,value in z}),4)
  self.assertIs(z[1][0],video.attach_fullscreen.return_value)
  video.attach_fullscreen.assert_called_once_with(panel)
