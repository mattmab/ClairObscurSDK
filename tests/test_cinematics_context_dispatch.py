import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_cinematics import module

class CinematicsContextDispatchTests(unittest.TestCase):
 def model(self,cap):
  model=module.Mod();model.session=N(_session=N(_transport=N(stable_lease_protocol=cap)))
  return model
 def test_current_context_is_fresh_through_retained_anchor(self):
  model=self.model(1);observe=Mock(side_effect=({'world':1},{'world':2}))
  with patch('expedition33.cinematics.controller_anchor.for_scope',return_value=N(context=observe)) as anchor,patch.object(module,'controller_context') as scan:
   self.assertNotEqual(model._context_now(),model._context_now())
  self.assertEqual(observe.call_count,2);self.assertEqual(anchor.call_count,2);scan.assert_not_called()
 def test_anchor_failure_is_not_retried_by_full_discovery(self):
  model=self.model(1)
  with patch('expedition33.cinematics.controller_anchor.for_scope',side_effect=RuntimeError('retired')),patch.object(module,'controller_context') as scan:
   with self.assertRaisesRegex(RuntimeError,'retired'):model._context_now()
  scan.assert_not_called()
 def test_unavailable_or_noninteger_capability_keeps_original_reader(self):
  for cap in (0,True,'1'):
   model=self.model(cap)
   with patch('expedition33.cinematics.controller_anchor.for_scope') as anchor,patch.object(module,'controller_context',return_value='fresh') as scan:
    self.assertEqual(model._context_now(),'fresh')
   anchor.assert_not_called();scan.assert_called_once_with(model.session,project=True)
