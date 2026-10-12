import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError, _query
from expedition33._reader import ReadBatch, _active


class ReadBatchTests(unittest.TestCase):
    def batch(self, lines):
        batch = ReadBatch(17)
        batch._process = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(),
                                         wait=Mock(return_value=0), kill=Mock())
        batch._line = Mock(side_effect=lines)
        batch._token = _active.set(batch)
        self.addCleanup(batch.__exit__)
        return batch

    def test_complete_framed_response_uses_existing_snapshot_validation(self):
        batch = self.batch(['{"event":"snapshot_start","pid":17}\n',
            '{"event":"snapshot_end","emitted":0}\n',
            '{"event":"reader_result","sequence":1,"code":0}\n'])
        with patch('expedition33.subprocess.run', side_effect=AssertionError('no subprocess fallback')):
            start, rows = _query(['--catalog'])
        self.assertEqual(start['pid'], 17)
        self.assertEqual(rows, [])
        self.assertEqual(batch._process.stdin.getvalue(), '--catalog\n')

    def test_wrong_sequence_closes_worker_and_prevents_fallback(self):
        batch = self.batch(['{"event":"reader_result","sequence":2,"code":0}\n'])
        with patch('expedition33.subprocess.run', side_effect=AssertionError('no fallback')):
            with self.assertRaises(RuntimeQueryError): _query(['--catalog'])
            with self.assertRaisesRegex(RuntimeQueryError, 'closed'): _query(['--catalog'])
        self.assertTrue(batch._process.stdin.closed)
        batch._process.wait.assert_called_once()

    def test_valid_frame_with_invalid_snapshot_also_closes_worker(self):
        batch = self.batch(['{"event":"reader_result","sequence":1,"code":0}\n'])
        with self.assertRaises(RuntimeQueryError): _query(['--catalog'])
        self.assertTrue(batch._closed)

    def test_failure_and_truncated_response_do_not_return_partial_rows(self):
        for ending in ('{"event":"reader_result","sequence":1,"code":1}\n',
                       RuntimeQueryError('stream ended')):
            batch = self.batch(['{"event":"snapshot_start","pid":17}\n', ending])
            with self.assertRaises(RuntimeQueryError): batch.query(['--catalog'])
            self.assertTrue(batch._closed)
            batch.__exit__()

    def test_mutation_foreign_process_and_line_injection_never_reach_worker(self):
        batch = self.batch([])
        for args in (['--session'], ['--thread-ping'], ['--describe','18','1:2:10000'],
                     ['--describe','17','1:2:10000\n--session']):
            with self.assertRaises(RuntimeQueryError): batch.query(args)
        self.assertEqual(batch._process.stdin.getvalue(), '')
        batch._line.assert_not_called()

    def test_nested_batch_rejected_without_starting_another_process(self):
        self.batch([])
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('must not spawn')):
            with self.assertRaisesRegex(RuntimeQueryError, 'nested'): ReadBatch(17).__enter__()

    def test_shared_owner_serves_fresh_queries_and_survives_borrower_exit(self):
        owner = self.batch(['first\n', '{"event":"reader_result","sequence":1,"code":0}\n',
                            'second\n', '{"event":"reader_result","sequence":2,"code":0}\n'])
        owner._share = True
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('must not spawn')):
            with ReadBatch(17) as borrowed:
                self.assertIs(_active.get(), owner)
                self.assertEqual(borrowed.query(['--catalog']), 'first\n')
            self.assertFalse(owner._closed)
            with ReadBatch(17) as borrowed:
                self.assertEqual(borrowed.query(['--catalog']), 'second\n')
            with self.assertRaises(RuntimeQueryError): ReadBatch(18).__enter__()
            with self.assertRaises(RuntimeQueryError): ReadBatch(17, share=True).__enter__()
        owner._process.wait.assert_not_called()

    def test_shared_failure_is_terminal_after_borrower_exit(self):
        owner = self.batch(['{"event":"reader_result","sequence":99,"code":0}\n'])
        owner._share = True
        with ReadBatch(17) as borrowed:
            with self.assertRaises(RuntimeQueryError): borrowed.query(['--catalog'])
        self.assertTrue(owner._closed)
        self.assertIs(_active.get(), owner)
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('no restart')):
            with self.assertRaisesRegex(RuntimeQueryError, 'closed'): ReadBatch(17).__enter__()
