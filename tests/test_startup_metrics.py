import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'src/expedition33/startup_metrics.py'
spec = importlib.util.spec_from_file_location('startup_metrics_candidate', MODULE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Clock:
    def __init__(self): self.value = 10.
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.metrics = m.StartupMetrics(process_started=8., clock=self.clock)

    def test_nested_phases_preserve_completion_order_and_inclusive_duration(self):
        with self.metrics.phase('bootstrap'):
            self.clock.advance(.1)
            with self.metrics.phase('module.prepare', module='EnemySpawner'):
                self.clock.advance(.2)
            self.clock.advance(.1)
        rows = self.metrics.snapshot()['events']
        self.assertEqual([r['phase'] for r in rows], ['module.prepare', 'bootstrap'])
        self.assertAlmostEqual(rows[0]['duration_ms'], 200.)
        self.assertAlmostEqual(rows[1]['duration_ms'], 400.)
        self.assertAlmostEqual(rows[1]['start_ms'], 2000.)

    def test_failure_records_once_and_does_not_leak_exception(self):
        failure = RuntimeError('private error payload')
        with self.assertRaises(RuntimeError) as raised:
            with self.metrics.phase('world.activate'):
                self.clock.advance(.5)
                raise failure
        self.assertIs(raised.exception, failure)
        data = self.metrics.snapshot()
        self.assertEqual(len(data['events']), 1)
        self.assertFalse(data['events'][0]['success'])
        self.assertEqual(data['summary'][0]['failed'], 1)
        self.assertNotIn('private error payload', json.dumps(data))

    def test_bounded_history_keeps_complete_aggregates(self):
        metrics = m.StartupMetrics(clock=self.clock, event_limit=2)
        for duration in (.1, .2, .3):
            with metrics.phase('map.placement'):
                self.clock.advance(duration)
        data = metrics.snapshot()
        self.assertEqual([r['sequence'] for r in data['events']], [2, 3])
        self.assertEqual(data['dropped_events'], 1)
        summary = data['summary'][0]
        self.assertEqual(summary['count'], 3)
        self.assertAlmostEqual(summary['total_ms'], 600.)
        self.assertAlmostEqual(summary['max_ms'], 300.)
        self.assertAlmostEqual(summary['last_ms'], 300.)

    def test_summary_cardinality_is_bounded(self):
        metrics = m.StartupMetrics(clock=self.clock, phase_limit=1)
        with metrics.phase('discovery'): pass
        with self.assertRaises(ValueError):
            with metrics.phase('different'): pass
        self.assertEqual(len(metrics.snapshot()['summary']), 1)

    def test_bad_clock_rejected_and_original_failure_preserved(self):
        with self.assertRaises(ValueError):
            m.StartupMetrics(clock=lambda: float('nan'))
        with self.assertRaises(ValueError):
            m.StartupMetrics(clock=self.clock, process_started=11.)
        with self.assertRaises(ValueError):
            with self.metrics.phase('bootstrap'):
                self.clock.value -= 1.
        self.clock.value = 10.
        with self.assertRaisesRegex(RuntimeError, '^original$'):
            with self.metrics.phase('bootstrap'):
                self.clock.value = float('nan')
                raise RuntimeError('original')
        self.assertEqual(self.metrics.snapshot()['summary'][0]['failed'], 1)

    def test_snapshot_does_not_expose_mutable_storage(self):
        with self.metrics.phase('discovery'): pass
        copy = self.metrics.snapshot()
        copy['events'][0]['phase'] = 'changed'
        copy['summary'][0]['count'] = 99
        self.assertEqual(self.metrics.snapshot()['events'][0]['phase'], 'discovery')
        self.assertEqual(self.metrics.snapshot()['summary'][0]['count'], 1)

    def test_single_owner_thread(self):
        errors = []
        def other():
            try: self.metrics.snapshot()
            except Exception as error: errors.append(error)
        thread = threading.Thread(target=other)
        thread.start(); thread.join()
        self.assertIsInstance(errors[0], RuntimeError)

    def test_atomic_local_output_and_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'startup.json'
            path.write_text('previous', encoding='utf8')
            with self.metrics.phase('bootstrap'): pass
            with patch.object(m.os, 'replace', side_effect=OSError('blocked')):
                with self.assertRaises(OSError): self.metrics.write_json(path)
            self.assertEqual(path.read_text(encoding='utf8'), 'previous')
            self.assertEqual(list(path.parent.glob('*.tmp')), [])
            self.metrics.write_json(path)
            self.assertEqual(json.loads(path.read_text(encoding='utf8'))['version'], 1)
            self.assertEqual(list(path.parent.glob('*.tmp')), [])

    def test_relative_and_remote_paths_rejected(self):
        for path in ('metrics.json', '//server/share/metrics.json'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                self.metrics.write_json(path)

    def test_only_identifier_metadata_and_finite_wallclock(self):
        with self.assertRaises(ValueError):
            with self.metrics.phase('config secret payload'): pass
        with self.assertRaises(ValueError):
            m.StartupMetrics(clock=self.clock, wallclock=float('inf'))
        metrics = m.StartupMetrics(clock=self.clock, wallclock=1234.)
        self.assertEqual(metrics.snapshot()['process_wallclock'], 1234.)


if __name__ == '__main__': unittest.main()
