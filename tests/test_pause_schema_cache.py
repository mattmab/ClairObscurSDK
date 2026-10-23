from types import SimpleNamespace as N
import unittest
from unittest.mock import patch
from expedition33.pause_menu import PauseMenuEntry
from expedition33 import invocation
import test_prepared_invocation

class PauseSchemaCacheTests(unittest.TestCase):
    setUp=test_prepared_invocation.PreparedTextTests.setUp
    session=test_prepared_invocation.PreparedTextTests.session
    response=test_prepared_invocation.PreparedTextTests.response

    def test_stabilized_entry_schemas_survive_planner_refresh_and_next_entry(self):
        session,_,_=self.session()
        with patch.object(invocation,'describe',wraps=invocation.describe) as describe:
            for _ in range(2):
                entry=PauseMenuEntry.__new__(PauseMenuEntry)
                entry.parent_scope=N(_session=session);entry._metadata_stable_ui=True
                with session.invocation_planner(catalog=self.p.catalog) as planner:
                    entry.planner=planner
                    entry.prepare(self.p.target,self.p.function,Input='one')
                    planner.refresh_from(self.p.catalog)
                    entry.prepare(self.p.target,self.p.function,Input='two')
            self.assertEqual(describe.call_count,1)
        self.assertTrue(session._pause_schema_observations._entries)

    def test_unstabilized_legacy_entry_does_not_share_schemas(self):
        session,_,_=self.session();entry=PauseMenuEntry.__new__(PauseMenuEntry)
        entry.parent_scope=N(_session=session)
        with patch.object(invocation,'describe',wraps=invocation.describe) as describe:
            with session.invocation_planner(catalog=self.p.catalog) as planner:
                entry.planner=planner
                entry.prepare(self.p.target,self.p.function,Input='one')
                planner.refresh_from(self.p.catalog)
                entry.prepare(self.p.target,self.p.function,Input='two')
            self.assertEqual(describe.call_count,2)
        self.assertFalse(hasattr(session,'_pause_schema_observations'))

if __name__=='__main__':unittest.main()
