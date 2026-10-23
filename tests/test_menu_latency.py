import unittest
from unittest.mock import patch
from types import SimpleNamespace
from contextlib import contextmanager
from expedition33._menu_latency import MenuLatency
from expedition33.management_native import NativeManagementMenu,display_line,display_detail
from expedition33.widgets import OwnedMenuPanel
class LatencyTests(unittest.TestCase):
 def test_meter_records_failures_without_suppressing(self):
  clock=iter([1.,1.025]);m=MenuLatency(clock=lambda:next(clock))
  with self.assertRaisesRegex(RuntimeError,'original'):
   with m.measure('test'):raise RuntimeError('original')
  r=m.snapshot()['timings']['test'];self.assertEqual(r['count'],1);self.assertEqual(r['failed'],1);self.assertAlmostEqual(r['last_ms'],25.)
 def test_color_cached_only_after_call_return(self):
  m=NativeManagementMenu.__new__(NativeManagementMenu);m.latency=MenuLatency();m._button_colors={};calls=[];m.panel=SimpleNamespace(buttons=[0],_render_call=lambda *a,**k:calls.append(k))
  m._set_button_color(0,(.1,.2,.3));m._set_button_color(0,(.1,.2,.3));self.assertEqual(len(calls),1)
  m.panel._render_call=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('unknown'))
  with self.assertRaises(RuntimeError):m._set_button_color(0,(.4,.5,.6))
  self.assertEqual(m._button_colors[0],(.1,.2,.3))
 def test_batch_failure_invalidates_tentative_color_cache(self):
  m=NativeManagementMenu.__new__(NativeManagementMenu);m.latency=MenuLatency();m._button_colors={0:(1,2,3)};m._presentation_suspended=False
  @contextmanager
  def batch():yield;raise RuntimeError('batch unknown')
  m.panel=SimpleNamespace(paint_batch=batch);m._paint_frame=lambda:None
  with self.assertRaisesRegex(RuntimeError,'batch unknown'):m._paint()
  self.assertEqual(m._button_colors,{})
 def test_mutation_unknown_latch_unchanged(self):
  p=OwnedMenuPanel.__new__(OwnedMenuPanel);p.uncertain=False;p.latency=MenuLatency()
  def unknown():raise RuntimeError('lost acknowledgment')
  with self.assertRaisesRegex(RuntimeError,'lost acknowledgment'):p._mutate(unknown)
  self.assertTrue(p.uncertain)
  with self.assertRaisesRegex(RuntimeError,'no retry'):p._mutate(lambda:None)
 def test_format_caches_preserve_value(self):
  display_line.cache_clear();display_detail.cache_clear()
  a=display_line('two  words',20);b=display_line('two  words',20);self.assertEqual(a,b);self.assertEqual(display_line.cache_info().hits,1)
  self.assertEqual(display_detail('x\ny'),display_detail('x\ny'));self.assertEqual(display_detail.cache_info().hits,1)

import test_management
from test_mods_workspace_scroll import ScrollFakePanel
from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu
class CountingPanel(ScrollFakePanel):
 def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.appearance=None;self.native_calls=[]
 def _render_call(self,*args,**kwargs):self.native_calls.append((args,kwargs))
class WorkspaceLatencyTests(unittest.TestCase):
 setUp=test_management.ManagementTests.setUp
 tearDown=test_management.ManagementTests.tearDown
 def colors(self,menu):return [v for v in menu.panel.native_calls if v[0][1:]==('Button','SetBackgroundColor')]
 def test_final_colors_one_per_button_and_none_for_unchanged_repaint(self):
  with patch('expedition33.mods_workspace_scroll.ScrollWorkspacePanel',CountingPanel):m=ScrollWorkspaceMenu(None,self.registry)
  m.prepare()
  self.assertEqual(len(self.colors(m)),105);rows=len(m.view.row_states);self.assertGreater(rows,0)
  m.panel.native_calls.clear();m.refresh_detached();self.assertEqual(self.colors(m),[])
  self.loader.enable('Specimen');m.panel.native_calls.clear();m.refresh_detached()
  self.assertLessEqual(len(self.colors(m)),2);self.assertGreater(len(self.colors(m)),0)
 def test_theme_change_invalidates_final_color_cache(self):
  with patch('expedition33.mods_workspace_scroll.ScrollWorkspacePanel',CountingPanel):m=ScrollWorkspaceMenu(None,self.registry)
  m.prepare();m.panel.native_calls.clear()
  m.panel.appearance=('different',1.);m.refresh_detached();self.assertEqual(len(self.colors(m)),105)

if __name__=='__main__':unittest.main()
