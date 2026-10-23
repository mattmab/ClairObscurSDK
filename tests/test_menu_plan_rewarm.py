from contextlib import contextmanager
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest
from expedition33.management_service import NativeMenuService
from expedition33 import _reader


class MenuPlanRewarmTests(unittest.TestCase):
    def setUp(self):
        self.session=N(_menu_plan_cache=object())
        self.scope=N(pid=7,_session=self.session,_check=lambda:None,supports_multi_controls=True)
        self.service=NativeMenuService(self.scope,object())
        self.service._keep_menu_plan_warm=True
        self.service._primed_menu_cache=self.session._menu_plan_cache
        self.events=[]
        self.panel=N(state='built',prime_menu_plan=self.prime)
        self.menu=N(panel=self.panel,failure=None,_view_factory=object(),
            open=lambda:self.events.append('attach'),view=object())
        self.service.menu=self.menu
        self.service.prepare=Mock()
        self.service._snapshot=Mock(return_value=())
        self.service._observed=()
    def prime(self):
        self.events.append('prime');self.session._menu_plan_cache=object()
    @contextmanager
    def batch(self,pid):
        self.assertEqual(pid,7);self.events.append('reader.enter')
        yield
        self.events.append('reader.exit')
    def test_unchanged_cache_needs_no_reader_or_replanning(self):
        with patch.object(_reader,'ReadBatch') as batch:self.service._warm_menu_plan()
        batch.assert_not_called();self.assertEqual(self.events,[])
    def test_invalidated_cache_rewarms_before_throttled_detached_poll_returns(self):
        self.session._menu_plan_cache=None;self.service._next_poll=float('inf')
        with patch.object(_reader,'ReadBatch',side_effect=self.batch):self.service.poll()
        self.assertEqual(self.events,['reader.enter','prime','reader.exit'])
        self.assertIs(self.service._primed_menu_cache,self.session._menu_plan_cache)
        self.assertEqual(self.panel.state,'built')
    def test_other_panels_cache_is_not_accepted_and_open_uses_bounded_reader(self):
        self.session._menu_plan_cache=object()
        with patch.object(_reader,'ReadBatch',side_effect=self.batch):
            self.service.open(view_factory=self.menu._view_factory)
        self.assertEqual(self.events,['reader.enter','prime','reader.exit','attach'])
    def test_real_plan_rejection_retains_failure_and_never_attaches(self):
        self.session._menu_plan_cache=None
        self.panel.prime_menu_plan=Mock(side_effect=RuntimeError('identity mismatch'))
        with patch.object(_reader,'ReadBatch',side_effect=self.batch):self.service.poll()
        self.assertIn('identity mismatch',self.service._failure)
        self.assertNotIn('attach',self.events)
        self.assertIs(self.service.menu,self.menu)
    def test_ordinary_services_do_not_compete_for_process_cache_during_poll(self):
        self.service._keep_menu_plan_warm=False;self.session._menu_plan_cache=None
        self.service._next_poll=float('inf')
        with patch.object(_reader,'ReadBatch') as batch:self.service.poll()
        batch.assert_not_called()
    def test_other_mods_open_menu_defers_rewarm_without_suspending_frontend(self):
        self.session._menu_plan_cache=None;self.session._menus=[N(active=True)]
        with patch.object(_reader,'ReadBatch') as batch:self.service._warm_menu_plan()
        batch.assert_not_called();self.assertIsNone(self.service._failure)
        self.session._menus[0].active=False
        with patch.object(_reader,'ReadBatch',side_effect=self.batch):self.service._warm_menu_plan()
        self.assertEqual(self.events,['reader.enter','prime','reader.exit'])

if __name__=='__main__':unittest.main()
