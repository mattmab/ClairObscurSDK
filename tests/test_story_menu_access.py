import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_menu_access import StoryMenuAccess

class MenuAccessTests(unittest.TestCase):
    def owner(self,unlocked=False):
        o=StoryMenuAccess.__new__(StoryMenuAccess)
        o.scope=N(pid=1);o.key='test';o.identity=N(read=lambda:'test')
        o.done=False;o.unknown=False;o.get=Mock();o.set=Mock()
        o.get.invoke.side_effect=lambda:nullcontext(N(outputs={'IsUnlocked':unlocked}))
        return o
    def test_existing_unlock_does_not_regrant_or_change_other_capacities(self):
        o=self.owner(True)
        with patch('expedition33.story_menu_access.shared_operation',return_value=nullcontext()):o.unlock();o.unlock()
        o.set.invoke.assert_not_called();self.assertTrue(o.done)
    def test_save_mismatch_does_not_unlock(self):
        o=self.owner();o.identity.read=lambda:'another-save'
        with patch('expedition33.story_menu_access.shared_operation',return_value=nullcontext()):
            with self.assertRaisesRegex(RuntimeError,'save changed'):o.unlock()
        o.set.invoke.assert_not_called()
    def test_uncertain_dispatch_is_not_replayed(self):
        o=self.owner();o.set.invoke.side_effect=RuntimeError('unknown dispatch')
        with patch('expedition33.story_menu_access.shared_operation',return_value=nullcontext()):
            with self.assertRaisesRegex(RuntimeError,'unknown dispatch'):o.unlock()
            with self.assertRaisesRegex(RuntimeError,'do not replay'):o.unlock()
        o.set.invoke.assert_called_once()
