from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from expedition33._pause_clicks import PauseClicks


class PauseClicksTests(TestCase):
    def test_new_subscription_keeps_shared_renewal_deadline(self):
        session, function = NS(), object()
        trace = Mock(state='active', _observed=0)
        trace.read.return_value = ()
        with patch('expedition33._pause_clicks.time.monotonic', return_value=0), patch('expedition33._pause_clicks._traces.start', return_value=trace):
            first = PauseClicks(session,function,NS(pid=1,index=2,serial=3),None)
        with patch('expedition33._pause_clicks.time.monotonic', return_value=119):
            second = PauseClicks(session,function,NS(pid=1,index=4,serial=5),None)
        with patch('expedition33._pause_clicks.time.monotonic', return_value=121):
            second.read()
        trace.renew.assert_called_once()
        self.assertEqual(first.hub['renew_at'],241)

    def test_confirmed_expiry_replaces_shared_trace_without_losing_subscriptions(self):
        session,function=NS(),object()
        old=Mock(state='active',_observed=0)
        new=Mock(state='active',_observed=0);new.read.return_value=()
        with patch('expedition33._pause_clicks._traces.start',return_value=old):
            first=PauseClicks(session,function,NS(pid=1,index=2,serial=3),None)
            second=PauseClicks(session,function,NS(pid=1,index=4,serial=5),None)
        old.state='expired'
        with patch('expedition33._pause_clicks._traces.start',return_value=new) as start:
            first.read()
        old.close.assert_called_once();start.assert_called_once()
        self.assertEqual(second.state,'active')
        self.assertEqual(len(first.hub['queues']),2)

    def test_group_polls_once_and_retains_other_subscriptions(self):
        session, function = NS(), object()
        a, b = NS(pid=1, index=2, serial=3), NS(pid=1, index=4, serial=5)
        trace = Mock(state='active', _observed=0)
        trace.read.return_value = (b, a)
        with patch('expedition33._pause_clicks._traces.start', return_value=trace):
            first = PauseClicks(session, function, a, None)
            second = PauseClicks(session, function, b, None)
        self.assertEqual(first.read(), (a,))
        self.assertEqual(second.read(poll=False), (b,))
        self.assertEqual(second.read(poll=False), ())
        trace.read.assert_called_once()
        first.close(); second.close()

    def test_independent_routing_and_last_owner_cleanup(self):
        session, function = NS(), object()
        trace = Mock(state='active', _observed=0)
        a, b = NS(pid=1, index=2, serial=3), NS(pid=1, index=4, serial=5)
        stale = NS(pid=1, index=4, serial=6)
        trace.read.side_effect = [(b, stale, a), (), (b,)]
        with patch('expedition33._pause_clicks._traces.start', return_value=trace) as start:
            first = PauseClicks(session, function, a, None)
            second = PauseClicks(session, function, b, None)
        start.assert_called_once()
        self.assertEqual(first.read(), (a,))
        self.assertEqual(second.read(), (b,))
        first.close()
        trace.close.assert_not_called()
        self.assertEqual(second.read(), (b,))
        second.close()
        trace.close.assert_called_once()
        self.assertIsNone(session._pause_click_hub)
