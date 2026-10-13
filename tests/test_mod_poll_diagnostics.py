import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33.mods import ModLoader, ModError


class ModPollDiagnostics(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.events = []
        self.shared = NS(console=NS(poll=lambda: self.events.append('console')),
                         poll=lambda: self.events.append('shared') or 2)
        self.loader = None

    def tearDown(self):
        if self.loader is not None:
            self.loader._loaded.clear()
            self.loader._keys = None
            self.loader.close()
        self.temp.cleanup()

    def loader_for(self, enabled=False):
        self.loader = ModLoader(self.temp.name, session=self.shared, poll_diagnostics=enabled)
        self.loader._loaded['Sample'] = ('module', NS(poll=lambda: self.events.append('mod')), object())
        return self.loader

    def test_disabled_keeps_order_and_does_not_read_clock(self):
        loader = self.loader_for()
        with patch('expedition33._session.supports_keys', return_value=False), \
             patch('expedition33.mods.time.perf_counter') as clock:
            self.assertEqual(loader.poll(), 2)
            clock.assert_not_called()
        self.assertEqual(self.events, ['console', 'shared', 'mod'])
        self.assertEqual(loader._poll_timings, {})

    def test_enabled_measures_each_phase_and_preserves_delivered_count(self):
        loader = self.loader_for(True)
        loader._keys = NS(session=self.shared, poll=lambda: self.events.append('keys') or 3)
        with patch('expedition33._session.supports_keys', return_value=True), \
             patch('expedition33.mods.time.perf_counter', side_effect=range(10)):
            self.assertEqual(loader.poll(), 5)
        self.assertEqual(self.events, ['console', 'shared', 'keys', 'mod'])
        self.assertEqual(set(loader._poll_timings), {'shared.console.poll', 'shared.poll', 'keys.poll', 'mod.Sample', 'total'})
        for key, value in loader._poll_timings.items():
            self.assertEqual(value['count'], 1)
            self.assertEqual(value['total_ms'], 9000. if key == 'total' else 1000.)

    def test_exception_is_timed_without_stopping_other_mod_callbacks(self):
        loader = self.loader_for(True)
        loader._loaded['Sample'][1].poll = Mock(side_effect=ValueError('bad callback'))
        loader._loaded['Other'] = ('other', NS(poll=lambda: self.events.append('other')), object())
        with patch('expedition33._session.supports_keys', return_value=False):
            with self.assertRaisesRegex(ModError, 'ValueError: bad callback'):
                loader.poll()
        self.assertEqual(self.events, ['console', 'shared', 'other'])
        self.assertEqual(loader._poll_timings['mod.Sample']['count'], 1)
        self.assertEqual(loader._poll_timings['total']['count'], 1)
        self.assertFalse(loader._polling)

    def test_shared_exception_propagates_and_is_timed(self):
        loader = self.loader_for(True)
        self.shared.console.poll = Mock(side_effect=RuntimeError('console failed'))
        with self.assertRaisesRegex(RuntimeError, 'console failed'):
            loader.poll()
        self.assertEqual(set(loader._poll_timings), {'shared.console.poll', 'total'})
        self.assertFalse(loader._polling)

    def test_snapshot_is_logged_every_30_polls_and_window_resets(self):
        loader = self.loader_for(True)
        logger = Mock()
        with patch('expedition33._session.supports_keys', return_value=False), \
             patch('expedition33.mods.logging.getLogger', return_value=logger):
            for _ in range(29): loader.poll()
            logger.info.assert_not_called()
            loader.poll()
        logger.info.assert_called_once()
        snapshot = logger.info.call_args.args[1]
        self.assertEqual(snapshot['total']['count'], 30)
        self.assertEqual(snapshot['mod.Sample']['count'], 30)
        self.assertGreaterEqual(snapshot['total']['total_ms'], snapshot['total']['max_ms'])
        self.assertEqual(loader._poll_timings, {})
        self.assertEqual(loader._poll_sample_count, 0)


if __name__ == '__main__': unittest.main()
