import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import RuntimeQueryError
from expedition33.save_story_ui import SaveStoryUI

class CleanupTests(unittest.TestCase):
    def owner(self):
        service=object.__new__(SaveStoryUI);service._closed=False;service.failed=None
        owner=Mock();owner.unknown=False
        owner.close.side_effect=RuntimeQueryError('Object identity changed or belongs to another process')
        service.labels={'row':(owner,1,'story')}
        return service,owner
    def test_read_only_title_exit_race_retains_owner_without_escaping_host(self):
        service,owner=self.owner();service.poll(None)
        self.assertIsNone(service.failed);self.assertIn('row',service.labels)
        owner.close.side_effect=None;owner.close.return_value=True
        service.poll(None);self.assertEqual(service.labels,{})
    def test_unknown_mutation_is_suspended_and_never_retried(self):
        service,owner=self.owner();owner.unknown=True
        service.poll(None);self.assertIsNotNone(service.failed)
        service.poll(None);self.assertEqual(owner.close.call_count,1)
