from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,patch
from expedition33._scope import SessionScope
from test_mods import FakeSession


class ScopeWorldCallbackTests(unittest.TestCase):
 def test_hook_uncertainty_skips_delivery_but_scope_cleanup_apis_remain_available(self):
  session=FakeSession();session._transport=object();ready=[True];captured=[]
  session.hook=lambda obj,target,callback:captured.append(callback) or Mock()
  scope=SessionScope(session);scope._world_callback_readiness=lambda:ready[0]
  child=SessionScope(scope);callback=Mock();child.hook(object(),'event',callback)
  ready[0]=None;captured[0](object());callback.assert_not_called()
  child._check() # Native retirement can still use this scope.
  ready[0]=True;captured[0](object());callback.assert_called_once()
  scope.close()
 def test_scoped_console_delivery_blocks_world_callback_without_closing_scope(self):
  session=FakeSession();session._transport=object();scope=SessionScope(session)
  ready=[False];scope._world_callback_readiness=lambda:ready[0];callback=Mock()
  scope.console.register('world',callback,owner=object())
  session.console.dispatcher.execute('world');callback.assert_not_called();scope._check()
  ready[0]=True;session.console.dispatcher.execute('world');callback.assert_called_once()
  scope.close()
 def test_invalid_gate_is_visible_and_legacy_scope_has_no_new_gate(self):
  scope=SessionScope(FakeSession());self.assertTrue(scope._callbacks_ready())
  scope._world_callback_readiness=lambda:1
  with self.assertRaises(TypeError):scope._callbacks_ready()
  scope.close()
 def test_prepared_native_menu_inherits_exact_scope_callback_gate(self):
  session=FakeSession();session._transport=object();session._menus=set();scope=SessionScope(session)
  ready=[True];scope._world_callback_readiness=lambda:ready[0]
  class Menu:
   active=True
   def close(self):self.active=False;return True
  menu=Menu()
  def prepare(*args,**kwargs):session._menus.add(menu);return menu
  with patch('expedition33.menu.prepare',side_effect=prepare):
   self.assertIs(scope.prepare_menu(object(),object(),object()),menu)
  self.assertTrue(menu._world_callback_readiness());ready[0]=None
  self.assertFalse(menu._world_callback_readiness());scope.close()

if __name__=='__main__':unittest.main()
