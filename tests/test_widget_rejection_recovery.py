import unittest
from types import SimpleNamespace
from unittest.mock import patch
from expedition33.widgets import OwnedMenuPanel
from expedition33.invocation import InvocationError
from expedition33._menu_latency import MenuLatency

class WidgetRejectionRecoveryTests(unittest.TestCase):
 def panel(self):
  p=OwnedMenuPanel.__new__(OwnedMenuPanel)
  p.uncertain=False;p.latency=MenuLatency();p.state='built';p.menu=None
  p.assigned=True;p.tree=object();p.canvas=object();p.children=[];p._planner=None
  p._text={};p._enabled={};p._visible={};p._functions={};p._defaults={}
  self.calls=[]
  p.scope=SimpleNamespace(assign_object=lambda *a,**k:self.calls.append('clear_root'),close=lambda:self.calls.append('release'))
  p._class=lambda n:object();p._root=lambda:None
  return p
 def test_known_rejection_keeps_prior_ack_and_allows_owned_root_cleanup(self):
  p=self.panel();p._mutate(lambda:self.calls.append('prior_ack'))
  error=InvocationError('rejected',outcome='not_dispatched',native_error=202)
  def fail():self.calls.append('rejected_once');raise error
  with self.assertRaises(InvocationError) as caught:p._mutate(fail)
  self.assertIs(caught.exception,error);self.assertFalse(p.uncertain)
  self.assertTrue(p.close_owned_tree())
  self.assertEqual(self.calls,['prior_ack','rejected_once','clear_root','release'])
 def test_unknown_and_returned_failure_keep_cleanup_blocked(self):
  for outcome in ('unknown','dispatch_returned'):
   p=self.panel()
   def fail():raise InvocationError('failed',outcome=outcome,native_error=202)
   with self.assertRaises(InvocationError):p._mutate(fail)
   with self.assertRaisesRegex(RuntimeError,'unknown'):p.close_owned_tree()
   self.assertTrue(p.uncertain);self.assertEqual(self.calls,[])
 def test_inactive_focus_precondition_rejection_leaves_tree_closeable(self):
  from expedition33.menu import MenuError
  for active in (False,True,None):
   p=self.panel();p.widget=object();p.buttons=[object()];p.player=object()
   p.scope.prepare_menu=lambda *a,**k:(_ for _ in ()).throw(
       MenuError('focus',outcome='returned',native_error=90220,active=active))
   with self.assertRaises(MenuError):p.open()
   self.assertEqual(p.uncertain,active is not False)
   self.assertIsNone(p.menu);self.assertEqual(p.state,'built')
 def test_diagnostic_is_bounded_read_only_and_cannot_mask_original(self):
  p=self.panel();p.scope.pid=1
  target=SimpleNamespace(index=2,serial=3,address=4);fn=SimpleNamespace(index=5,serial=6,address=7)
  with patch('expedition33.widgets.capture_selected',side_effect=RuntimeError('private detail')) as capture, self.assertLogs('expedition33.widgets',level='ERROR') as logs:
   p._diagnose_rejected_identity(target,fn)
  self.assertEqual(capture.call_count,2)
  self.assertNotIn('private detail',' '.join(logs.output))
  self.assertFalse(p.uncertain)

if __name__=='__main__':unittest.main()
