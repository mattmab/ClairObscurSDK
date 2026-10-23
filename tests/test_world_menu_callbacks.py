import unittest
from unittest.mock import Mock
import test_button_actions as buttons
import test_multi_controls as controls


class WorldMenuCallbacksTests(unittest.TestCase):
 def test_single_button_suppresses_and_consumes_sequence_without_replay(self):
  f=buttons.ButtonActionsTests();f.setUp();ready=[False]
  f.menu._world_callback_readiness=lambda:ready[0]
  callback=Mock();action=f.menu.bind_action(callback);f.events=[f.event(action,1)]
  self.assertEqual(action._poll(),0);self.assertEqual(action._last_sequence,1);callback.assert_not_called()
  ready[0]=True;f.events=[];self.assertEqual(action._poll(),0);callback.assert_not_called()
  f.events=[f.event(action,2)];self.assertEqual(action._poll(),1);callback.assert_called_once()
 def test_multiple_controls_suppress_and_consume_sequence_without_replay(self):
  f=controls.MultiControlsTests();f.setUp();ready=[None]
  f.menu._world_callback_readiness=lambda:ready[0]
  callback=Mock();action=f.menu.bind_control(f.leases[2].object,callback)
  f.events=[f.event(action,1)]
  self.assertEqual(f.menu._controls.poll(),0);self.assertEqual(f.menu._controls.sequence,1);callback.assert_not_called()
  ready[0]=True;f.events=[];self.assertEqual(f.menu._controls.poll(),0);callback.assert_not_called()
  f.events=[f.event(action,2)];self.assertEqual(f.menu._controls.poll(),1);callback.assert_called_once()

if __name__=='__main__':unittest.main()
