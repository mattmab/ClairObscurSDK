import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.sdk import Session
class EmptyEventPollTests(unittest.TestCase):
    def fixture(self):
        s=Session.__new__(Session);s._check=Mock();s._release_pending_leases=Mock()
        s._polling=False;s._enabled=False;s._ever_observed=False;s._closed=False;s._menus=[];s._hooks=[]
        s._transport=N(command=Mock(return_value={'events':[],'dropped':0}))
        s._object=N(pid=1,index=2,serial=3,name='Default__Actor',class_name='Actor',address=0x10000)
        s.dropped_events=0;s._sequence=0;s._dispatcher=Mock()
        return s
    def test_no_empty_game_thread_drain_before_first_observer(self):
        s=self.fixture();self.assertEqual(s.poll(),0);s._transport.command.assert_not_called()
        s._release_pending_leases.assert_called_once()
    def test_active_and_previously_disabled_producers_still_drain(self):
        for active in (False,True):
            s=self.fixture();s._enabled=active;s._ever_observed=True
            if active:s._hooks=[N(active=True)]
            s.poll();s._transport.command.assert_called_once_with('drain')
    def test_first_hook_records_producer_start_after_acknowledged_enable(self):
        s=self.fixture();s._validate_target=Mock();s._dispatcher.subscribe.return_value=N(active=True)
        s.hook(object(),'Actor.IsActorBeingDestroyed',lambda event:None)
        s._transport.command.assert_called_once_with('enable')
        self.assertTrue(s._enabled);self.assertTrue(s._ever_observed)
