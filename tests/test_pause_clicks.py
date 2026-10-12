from types import SimpleNamespace as NS
from unittest import TestCase
from unittest.mock import Mock, patch
from expedition33._pause_clicks import PauseClicks


class PauseClicksTests(TestCase):
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
