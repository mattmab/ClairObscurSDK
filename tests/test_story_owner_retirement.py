import unittest
from types import SimpleNamespace as N
from expedition33.world_lifecycle import WorldLifecycle
from expedition33.story_original import _Owner
from expedition33.story_portal import StoryPortal
from expedition33.story_inworld import InWorldDialogue
class OwnerRetirementTests(unittest.TestCase):
    def test_only_acknowledged_closed_owners_pass_domain_retirement(self):
        coordinator=WorldLifecycle.__new__(WorldLifecycle)
        for cls in (_Owner,StoryPortal):
            owner=cls.__new__(cls);owner.closed=False;owner.unknown=False
            scope=N(_children=[],_native_owners=[owner])
            self.assertFalse(coordinator._scope_domain_ack(scope))
            owner.unknown=True;self.assertFalse(coordinator._scope_domain_ack(scope))
            owner.closed=True;self.assertTrue(coordinator._scope_domain_ack(scope))
    def test_completed_walking_dialogue_requires_actual_close_ack(self):
        coordinator=WorldLifecycle.__new__(WorldLifecycle)
        owner=InWorldDialogue.__new__(InWorldDialogue)
        owner.state='completed';owner.closed=False;owner.unknown=False
        scope=N(_children=[],_native_owners=[owner])
        self.assertFalse(coordinator._scope_domain_ack(scope))
        owner.closed=True
        self.assertTrue(coordinator._scope_domain_ack(scope))
        self.assertEqual(owner.state,'completed')
