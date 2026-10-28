import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.cinematics.browser_view import WorkspaceBrowserView
from expedition33.mods_workspace_scroll import ScrollWorkspacePanel, ScrollWorkspaceMenu
from expedition33.management import ManagementError
from test_cinematic_browser_view import scene

class WorkspaceBrowserTests(unittest.TestCase):
 def setUp(self):
  self.registry=N(_check=Mock(),select=Mock(side_effect=ManagementError('no settings')))
  self.model=N(library=[scene(str(i)) for i in range(18)],show_all=True,stop=Mock(return_value=True),control=Mock(),discover=Mock())
  self.view=WorkspaceBrowserView(self.registry,self.model)
 def test_physical_slots_preserve_logical_tokens_on_later_pages(self):
  frame=self.view.render();frame=self.view.activate(frame.revision,8)
  self.assertEqual(len(frame.controls),105);self.assertEqual(frame.controls[12].token,106)
  self.assertIn(111,self.view.bindable_tokens());self.assertEqual(frame.controls[51].token,6)
  self.assertTrue(all(not c.enabled for c in frame.controls if not c.label))
  frame=self.view.activate(frame.revision,106);self.assertEqual(self.view.selected,'6')
  self.assertEqual(frame.controls[48].token,9)
 def test_cached_suspend_revokes_old_revision_without_rebuilding(self):
  frame=self.view.render();commands=dict(self.view._commands)
  replacement=self.view.suspend_frame(frame)
  self.assertEqual(replacement.controls,frame.controls);self.assertEqual(commands,self.view._commands)
  self.assertEqual(self.view.revision,self.view._revision);self.assertEqual(self.view.revision,self.view._base_revision)
  with self.assertRaises(ManagementError):self.view.activate(frame.revision,100)
  self.view.activate(replacement.revision,100)
 def panel(self):
  p=Mock();p.latency=None;p.layout_mode=None;p.scroll_marker=None;p.key_row_capacity=12
  for attr,count in [('surface_slots',3),('panel_title_slots',3),('surfaces',3),('panel_titles',3),('button_slots',105),('label_slots',105),('row_slots',8)]:setattr(p,attr,list(range(count)))
  p.metadata=[];p.metadata_labels=[];p.key_slots=[];p.switches=[]
  p.invisible='visible';p.collapsed='collapsed';p.visible='visible'
  return p
 def test_actual_panel_layout_accepts_complete_workspace_contract(self):
  self.view.render();panel=self.panel()
  ScrollWorkspacePanel.layout(panel,self.view)
  self.assertEqual(panel.layout_mode,('editor',False));panel.position.assert_called()
  self.assertEqual(panel.scroll_marker,('cinematics',0,0))
 def test_actual_menu_paint_and_bind_use_physical_buttons_for_large_scene_tokens(self):
  self.view.render();self.view.page=2;frame=self.view.render()
  panel=self.panel();panel.layout=lambda view:ScrollWorkspacePanel.layout(panel,view)
  panel.labels=[N(index=i) for i in range(105)];panel.buttons=list(range(105));panel.text_bounds={}
  panel.appearance=('World Builder',1.);panel.paint_appearance=lambda *args:None
  panel.menu.bind_controls.side_effect=lambda pairs:[object() for _ in pairs]
  menu=object.__new__(ScrollWorkspaceMenu);menu.view=self.view;menu.frame=frame;menu.panel=panel
  menu.error="";menu._field_context=None;menu._button_colors={};menu._set_button_color=Mock();menu.actions=[];menu._presentation_suspended=False
  menu._sync_key_capture=lambda:None
  menu._paint_frame();menu._bind()
  self.assertIn(112,menu._binding_tokens)
  bound_buttons=[button for call in panel.menu.bind_controls.call_args_list for button,callback in call.args[0]]
  self.assertIn(12,bound_buttons);self.assertNotIn(112,bound_buttons)
  self.model.discover.assert_not_called();self.model.control.assert_not_called()



