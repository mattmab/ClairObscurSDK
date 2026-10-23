import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33._metadata_stabilization import require_positive_plan_identities
from expedition33.invocation import UnsupportedInvocation
from expedition33.prepared_invocation import InvocationPlanner
class MetadataPlanGuardTests(unittest.TestCase):
 def plan(self):
  return NS(target=NS(serial=11,class_name='BP_PlayerController_C'),function=NS(serial=12),parameters=(NS(constraint=NS(serial=13)),),objects=(NS(object=NS(serial=14)),))
 def test_positive_world_target_and_all_encoded_roles_are_accepted(self):
  plan=self.plan();self.assertIs(require_positive_plan_identities(plan),plan)
 def test_nullable_constraint_and_object_patch_canonical_sentinel_are_preserved(self):
  plan=self.plan();null=NS(index=-1,serial=0,address=0)
  plan.parameters=(NS(constraint=None),NS(constraint=null));plan.objects=(NS(object=None),NS(object=null))
  self.assertIs(require_positive_plan_identities(plan),plan)
 def test_unstabilized_template_function_style_patch_and_constraint_fail_before_plan_exposure(self):
  for role in ('function','constraint','object_patch'):
   plan=self.plan()
   if role=='function':plan.function.serial=0
   elif role=='constraint':plan.parameters[0].constraint.serial=0
   else:plan.objects[0].object.serial=0
   with self.assertRaisesRegex(UnsupportedInvocation,role):require_positive_plan_identities(plan)
 def test_opt_in_planner_rejects_zero_before_return_without_changing_generic_legacy(self):
  planner=InvocationPlanner.__new__(InvocationPlanner);planner._catalog=object();planner._metadata=None;planner._generation=0
  session=NS(supports_pod_values=False,supports_text_values=False,supports_enum_values=False)
  planner._check=lambda:session
  plan=self.plan();plan.function.serial=0
  planner._require_stable_ui_identities=True
  with patch('expedition33.invocation.prepare_call',return_value=plan):
   with self.assertRaises(UnsupportedInvocation):planner.prepare(object(),object())
   planner._require_stable_ui_identities=False
   # No native action is invoked; generic planner retains its prior contract.
   self.assertIs(planner.prepare(object(),object())._plan,plan)
