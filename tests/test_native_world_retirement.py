import importlib.util,sys,struct,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _pause_attachment as PAUSE, _menu_wire as WIRE, menu as MENU, widgets as WIDGETS, _runtime_scene_wire as SCENEWIRE, pause_menu as PAUSEMENU
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_retirement_scene_tests',ROOT/'mods/SceneEditor/mod.py',submodule_search_locations=[str(ROOT/'mods/SceneEditor')])
SCENE=importlib.util.module_from_spec(spec);sys.modules[spec.name]=SCENE;spec.loader.exec_module(SCENE)
class Tests(unittest.TestCase):
 def test_pause_wire_is_explicit_capability_only_and_empty(self):
  packet=PAUSE.HEADER.pack(1,8,123,0,0,0)+bytes(PAUSE.call.SIZE)
  with self.assertRaises(ValueError):PAUSE.validate_request(packet)
  PAUSE.validate_request(packet,allow_retired=True)
  with self.assertRaises(ValueError):PAUSE.validate_request(packet[:-1]+b'x',allow_retired=True)
 def test_pause_retired_ack_and_gc_defer_keep_owner(self):
  def command(name,payload):
   p=bytearray(payload);struct.pack_into('<2I',p,24,407 if command.calls==0 else 0,1 if command.calls==0 else 0);command.calls+=1
   return {'pause_attachment_packet':p.hex()}
  command.calls=0;session=N(_check=Mock(),_abort_ownership=Mock(),_transport=N(retired_world_cleanup_protocol=1,command=command,_check_thread=Mock()))
  owner=PAUSE.PauseAttachment(N(_session=session));owner.state='armed'
  self.assertFalse(owner.retire_world());self.assertEqual(owner.state,'armed')
  self.assertTrue(owner.retire_world());self.assertEqual(owner.state,'closed');session._abort_ownership.assert_not_called()
 def test_pause_capture_deferred_never_reports_ready_or_aborts_session(self):
  def command(name,payload):
   p=bytearray(payload);op=struct.unpack_from('<I',p,4)[0]
   struct.pack_into('<2I',p,24,407 if op==1 else 0,2 if op==1 else 0)
   return {'pause_attachment_packet':p.hex()}
  session=N(_check=Mock(),_abort_ownership=Mock(),_transport=N(retired_world_cleanup_protocol=1,command=command))
  owner=PAUSE.PauseAttachment(N(_session=session))
  with self.assertRaises(PAUSE.PauseCaptureDeferred):owner._send(1,123)
  self.assertEqual(owner.state,'capture_pending');session._abort_ownership.assert_not_called()
  self.assertTrue(owner.close());self.assertEqual(owner.state,'closed')
 def test_menu_retired_wire_and_ack_do_not_call_normal_close(self):
  with self.assertRaises(ValueError):WIRE.request('retire',3)
  p=WIRE.request('retire',3,allow_retired=True);self.assertEqual(struct.unpack_from('<I',p,4)[0],7)
  def command(name,payload):
   self.assertEqual(struct.unpack_from('<I',payload,4)[0],7)
   response=bytearray(payload);struct.pack_into('<3I',response,8,0,2,0);return {'menu_packet':response.hex()}
  session=N(_check=Mock(),_abort_ownership=Mock(),_transport=N(retired_world_cleanup_protocol=1,command=command,_check_thread=Mock()))
  # weakref requires a user class rather than SimpleNamespace.
  class Session:pass
  real=Session();real.__dict__.update(session.__dict__);real._menus=set()
  owner=MENU.NativeMenu(real,());real._menus.add(owner);owner._state='focused'
  self.assertTrue(owner.retire_world());self.assertEqual(owner._state,'closed');self.assertNotIn(owner,real._menus)
 def panel(self,state='open',menu=None):
  panel=WIDGETS.OwnedMenuPanel.__new__(WIDGETS.OwnedMenuPanel);panel.state=state;panel.uncertain=False;panel.menu=menu
  panel.scope=Mock();panel._planner=Mock();panel.children=[object()];panel.assigned=True;panel._render_call=Mock();panel.widget=object();return panel
 def test_panel_pending_native_retirement_retains_tree(self):
  owner=Mock();owner.retire_world.return_value=False;p=self.panel(menu=owner)
  self.assertEqual(p.retire_world(),'pending');p.scope.close.assert_not_called();p._render_call.assert_not_called();self.assertEqual(len(p.children),1)
  owner.retire_world.return_value=True;self.assertEqual(p.retire_world(),'ack');p._render_call.assert_not_called();self.assertEqual(p.children,[])
 def test_noninteractive_root_needs_preceding_native_domain_ack(self):
  p=self.panel();self.assertEqual(p.retire_world(),'unknown');p._render_call.assert_not_called()
  self.assertEqual(p.retire_world(native_retirement_ack=True),'ack');p._render_call.assert_called_once_with(p.widget,'Widget','RemoveFromParent')
 def test_pause_entry_never_restores_borrowed_panel_or_focus(self):
  p=PAUSEMENU.PauseMenuEntry.__new__(PAUSEMENU.PauseMenuEntry);p.state='attached';p._return_focus=True
  p._world_reader=Mock();p.observer=Mock();p.attachment=Mock();p.attachment.retire_world.side_effect=[False,True];p.scope=Mock()
  p.invoke=Mock(side_effect=AssertionError('old controller focus write'))
  self.assertEqual(p.retire_world(),'pending');self.assertFalse(p._return_focus);p.scope.close.assert_not_called()
  self.assertEqual(p.retire_world(),'ack');p.invoke.assert_not_called();p.attachment.restore.assert_not_called();p.attachment.close.assert_not_called()
 def test_scene_retired_command_preserves_scopes_until_native_ack(self):
  r=SCENE.Runtime();scopes=[Mock(),Mock(),Mock()];r.scope,r.preview_scope,r.audio_load_scope=scopes
  def command(name,payload):
   SCENEWIRE.validate_request(payload,protocol=7,allow_retired=True)
   p=bytearray(payload);struct.pack_into('<2I',p,8,407 if command.calls==0 else 0,3 if command.calls==0 else 5)
   struct.pack_into('<I',p,20976,1 if command.calls==0 else 0);command.calls+=1;return {'mesh_packet':p.hex()}
  command.calls=0;r.session=N(_session=N(_transport=N(runtime_scene_protocol=7,retired_world_cleanup_protocol=1,command=command,_check_thread=Mock())))
  self.assertEqual(r.retire_world(),'pending');[s.close.assert_not_called() for s in scopes]
  self.assertEqual(r.retire_world(),'ack');[s.close.assert_called_once_with() for s in scopes];self.assertIsNone(r.scope)
 def test_scene_unsupported_host_holds_without_normal_stop(self):
  r=SCENE.Runtime();r.scope=Mock();r.session=N(_session=N(_transport=N(retired_world_cleanup_protocol=0)));r.stop=Mock(side_effect=AssertionError('old restoration'))
  self.assertEqual(r.retire_world(),'unknown');r.stop.assert_not_called();r.scope.close.assert_not_called()
if __name__=='__main__':unittest.main()
