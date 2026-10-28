import importlib.util,sys,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch,MagicMock
from expedition33 import media
from expedition33.cinematics import media_presentation as pres
from expedition33.cinematics import fullscreen_media as full
from expedition33 import management_service as service
from test_cinematics import module as mod

class FullscreenTests(unittest.TestCase):
 def fake(self):
  order=[];v=Mock();v.uncertain=False;v.native_owner.close.return_value=True
  v.native_owner.close.side_effect=lambda:order.append('native_close') or True
  v.close.side_effect=lambda:order.append('scope_close');v._call.side_effect=lambda *a:order.append('remove')
  presentation=Mock();presentation.restore.side_effect=lambda:order.append('restore')
  with patch.object(full,'OwnedVideoWidget',return_value=v):owner=full.FullscreenMedia(N())
  owner.presentation=presentation;owner.state='opened';owner.button=N();owner.label_frame=N();owner.action=Mock()
  owner.action.remove.side_effect=lambda:order.append('unbind') or True
  return owner,v,presentation,order
 def test_stop_closes_native_before_controls_and_restore(self):
  owner,v,p,order=self.fake();self.assertTrue(owner.close())
  self.assertEqual(order,['native_close','unbind','remove','remove','scope_close','restore'])
  self.assertEqual(owner.state,'closed');owner.close();self.assertEqual(order.count('restore'),1)
 def test_deferred_close_keeps_visible_control_and_presentation(self):
  owner,v,p,order=self.fake();v.native_owner.close.side_effect=None;v.native_owner.close.return_value=False
  self.assertFalse(owner.close());owner.action.remove.assert_not_called();p.restore.assert_not_called();v.close.assert_not_called()
  v.native_owner.close.return_value=True;self.assertTrue(owner.close())
 def test_unknown_control_or_media_does_not_restore(self):
  for attr in ('_control_uncertain','uncertain'):
   owner,v,p,order=self.fake()
   if attr=='uncertain':v.uncertain=True
   else:setattr(owner,attr,True)
   with self.assertRaises(RuntimeError):owner.close()
   p.restore.assert_not_called();v.native_owner.close.assert_not_called()
 def test_escape_stops_playback_without_detaching_menu(self):
  for done in (True,False):
   s=object.__new__(service.NativeMenuService);s._check=Mock();s._failure=None
   stop=Mock(return_value=done);s.menu=N(panel=N(state='open'),_presentation_owner=N(stop_playback=stop),hide=Mock())
   s.close_menu();stop.assert_called_once();s.menu.hide.assert_not_called()
 def test_fullscreen_geometry_uses_stretch_anchors_not_resolution(self):
  v=object.__new__(media.OwnedVideoWidget);panel=object();v.state='configured';v.attached=False;v.parent=panel;v.widget=object()
  panel=N(canvas=object());v.parent=panel;v._invoke=Mock(return_value=N(return_value='slot'));v._call=Mock()
  v.attach_fullscreen(panel)
  self.assertEqual(v._call.call_args.kwargs,{'InAnchors':{'Minimum':{'X':0.,'Y':0.},'Maximum':{'X':1.,'Y':1.}}})
  self.assertTrue(v.attached)
 def test_natural_end_uses_stop_and_keeps_pending_owner(self):
  from expedition33.cinematics.adapters import MediaAdapter
  from expedition33.cinematics.controller import ReplayController, StartResult
  adapter=MediaAdapter(None,{},None,None,None);video=Mock(state='opened')
  adapter.backend=video;adapter.running=True;adapter._observed_playing=True;adapter.start=Mock(return_value=StartResult.STARTED)
  video.playback_status.return_value={'IsReady':True,'IsPlaying':False,'IsPaused':False}
  video.close.return_value=False
  controller=ReplayController();controller.queue('movie',lambda:adapter,'epoch');controller.poll('epoch')
  controller.poll('epoch');video.close.assert_called_once();self.assertTrue(controller.status().busy)
  self.assertNotIn('polling failed',controller.status().detail)
  video.close.return_value=True;controller.poll('epoch');self.assertFalse(controller.status().busy)
  self.assertEqual(video.close.call_count,2)
 def test_visible_stop_binding_runs_during_suspension_and_unknown_bind_is_retained(self):
  owner,v,presentation,order=self.fake();panel=N(tree=object(),canvas=object(),invisible=object(),state='open',menu=N(bind_control=Mock(return_value=Mock())))
  owner.menu=N(panel=panel,_presentation_suspended=True)
  catalog=N(objects=[N(name='Default__GameplayStatics'),N(name='CTS_B1_SmallLine_Outline_C')]);catalog.with_observations=lambda _:catalog
  v.scope=N(pid=7);v.planner=N(_catalog=catalog,refresh_from=Mock());v._one=lambda rows:list(rows)[0];v._class=lambda name:name
  v._invoke=Mock(return_value=N(return_value=object()));v._call=Mock();callback=Mock(return_value=True)
  with patch.object(full,'capture_matching',return_value=catalog):owner._build_stop(callback)
  panel.menu.bind_control.call_args.args[1](None);callback.assert_called_once()
  self.assertFalse(owner._control_uncertain)
  panel.menu.bind_control.side_effect=RuntimeError('unknown registration')
  with patch.object(full,'capture_matching',return_value=catalog):
   with self.assertRaises(RuntimeError):owner._build_stop(callback)
  self.assertTrue(owner._control_uncertain)
  with self.assertRaises(RuntimeError):owner.close()
  v.native_owner.close.assert_not_called();presentation.restore.assert_not_called()

 def test_timing_requires_typed_valid_values(self):
  from expedition33._pod_values import TimespanValue
  v=object.__new__(media.OwnedVideoWidget);v.scope=N(_session=N(_transport=N(timespan_values_protocol=1)));v.player=object();v.state='opened';v.uncertain=False
  v._read=Mock(side_effect=[TimespanValue(10_000_000),TimespanValue(20_000_000)])
  self.assertEqual(v.media_time()['time_seconds'],1.)
  v._read=Mock(side_effect=[TimespanValue(-1),TimespanValue(20_000_000)])
  with self.assertRaises(ValueError):v.media_time()

class ChildrenPresentationTests(unittest.TestCase):
 def test_only_snapshotted_owned_children_are_hidden_and_restored(self):
  root=N(index=1,serial=1,address=1);canvas=N(index=2,serial=1,address=2);children=[N(index=i,serial=1,address=i) for i in (3,4)]
  planner=Mock();planner.prepare.side_effect=lambda *a,**k:MagicMock()
  scope=N(pid=7,_check=Mock(),invocation_planner=Mock(return_value=planner))
  panel=N(state='open',uncertain=False,scope=scope,widget=root,canvas=canvas,children=children,_mutate=lambda f,*a:f(*a))
  menu=N(panel=panel,_presentation_owner=None,_restore_presentation_frame=Mock())
  fn=N(outer_index=10,name='SetRenderOpacity',class_name='Function');catalog=N(objects=[fn],by_index={10:N(index=10)},find_class=lambda _:N(index=10));catalog.with_observations=lambda _:catalog
  values=N(types={(10,'RenderOpacity'):'FloatProperty'},values={(10,'RenderOpacity'):.75},errors={},truncated=set())
  owner=pres.MenuChildrenPresentation(menu,Mock())
  with patch.object(pres,'capture_matching',return_value=catalog),patch.object(pres,'capture_selected',return_value=catalog),patch.object(pres,'read_values',return_value=values):owner.prepare()
  self.assertEqual([c.args[0] for c in planner.prepare.call_args_list],[children[0],children[0],children[1],children[1]])
  children.append(N(index=5,serial=1,address=5)) # A subsequently attached sibling must stay visible.
  owner.suspend();self.assertTrue(menu._presentation_suspended);owner.restore();self.assertFalse(menu._presentation_suspended)
  self.assertEqual(len(owner.hide_call),2);self.assertEqual(len(owner.restore_call),2);menu._restore_presentation_frame.assert_called_once()
 def test_unknown_hide_never_attempts_blind_restore(self):
  panel=N(state='open',uncertain=False,_mutate=Mock(side_effect=RuntimeError('unknown')))
  menu=N(panel=panel,_presentation_owner=None);owner=pres.MenuChildrenPresentation(menu,Mock());owner.state='prepared';owner.hide_call=()
  with self.assertRaises(RuntimeError):owner.suspend()
  self.assertEqual(owner.state,'unknown');self.assertTrue(menu._presentation_suspended)
  with self.assertRaises(RuntimeError):owner.restore()
  self.assertEqual(panel._mutate.call_count,1)

if __name__=='__main__':unittest.main()
