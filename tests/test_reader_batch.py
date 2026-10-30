import io
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError, _query
from expedition33._reader import ReadBatch, _active


class ReadBatchTests(unittest.TestCase):
    def test_source_line_limit_is_explicit_and_bounded(self):
        for invalid in (True, 0, 1048575, 16*1024*1024+1):
            with self.assertRaises(ValueError):
                ReadBatch(17, _line_limit=invalid)
        line = 'x' * 1048576 + '\n'
        for limit, accepted in ((1048576, False), (16*1024*1024, True)):
            batch = ReadBatch(17, _line_limit=limit)
            batch._process = SimpleNamespace(stdout=io.StringIO(line))
            batch._read()
            first = batch._lines.get_nowait()
            if accepted:
                self.assertEqual(first, line)
            else:
                self.assertIsInstance(first, RuntimeQueryError)
            self.assertIsNone(batch._lines.get_nowait())

    def test_larger_source_line_limit_still_rejects_truncated_line(self):
        batch = ReadBatch(17, _line_limit=16*1024*1024)
        batch._process = SimpleNamespace(stdout=io.StringIO('missing newline'))
        batch._read()
        self.assertIsInstance(batch._lines.get_nowait(), RuntimeQueryError)
        self.assertIsNone(batch._lines.get_nowait())

    def batch(self, lines):
        batch = ReadBatch(17)
        batch._process = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(),
                                         wait=Mock(return_value=0), kill=Mock())
        batch._line = Mock(side_effect=lines)
        batch._token = _active.set(batch)
        self.addCleanup(batch.__exit__)
        return batch

    def test_warm_does_not_bind_or_replace_another_read_operation(self):
        parent=ReadBatch(17,share=True);reader=ReadBatch(17,share=True)
        process=SimpleNamespace(stdin=io.StringIO(),stdout=io.StringIO(),wait=Mock(return_value=0),kill=Mock())
        token=_active.set(parent)
        try:
            with patch('expedition33._reader.subprocess.Popen',return_value=process) as spawn, \
                    patch('expedition33._reader.threading.Thread'), \
                    patch.object(reader,'_line',return_value='{"event":"reader_ready","version":2,"pid":17}'):
                reader.warm();reader.warm()
                self.assertIs(_active.get(),parent);self.assertIsNone(reader._token)
                self.assertTrue(reader.supports_catalog_values)
                with self.assertRaisesRegex(RuntimeQueryError,'Enter the read batch'):
                    reader.query(['--catalog'])
                spawn.assert_called_once()
        finally:_active.reset(token)
        with reader.bind():self.assertIs(_active.get(),reader)
        self.assertIsNone(_active.get());reader.close();parent.close()

    def test_complete_framed_response_uses_existing_snapshot_validation(self):
        batch = self.batch(['{"event":"snapshot_start","pid":17}\n',
            '{"event":"snapshot_end","emitted":0}\n',
            '{"event":"reader_result","sequence":1,"code":0}\n'])
        with patch('expedition33.subprocess.run', side_effect=AssertionError('no subprocess fallback')):
            start, rows = _query(['--catalog'])
        self.assertEqual(start['pid'], 17)
        self.assertEqual(rows, [])
        self.assertEqual(batch._process.stdin.getvalue(), '--catalog\n')

    def test_optional_io_timing_does_not_change_framing_or_query_results(self):
        batch=self.batch(['first\n','{"event":"reader_result","sequence":1,"code":0}\n',
                          'second\n','{"event":"reader_result","sequence":2,"code":0}\n'])
        batch._timing={}
        self.assertEqual(batch.query(['--catalog']),'first\n')
        first=batch._timing['source_reader_io_ms']
        self.assertGreaterEqual(first,0.)
        self.assertEqual(batch.query(['--catalog']),'second\n')
        self.assertGreaterEqual(batch._timing['source_reader_io_ms'],first)

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

    def test_shared_operation_borrows_io_without_creating_a_second_owner(self):
        from expedition33._reader import shared_operation
        owner=self.batch(['fresh\n','{"event":"reader_result","sequence":1,"code":0}\n'])
        owner._share=True
        with patch('expedition33._reader.subprocess.Popen',side_effect=AssertionError('no new worker')):
            with shared_operation(17) as borrowed:
                self.assertIs(borrowed._borrowed,owner)
                self.assertEqual(borrowed.query(['--catalog']),'fresh\n')
        self.assertFalse(owner._closed);owner._process.wait.assert_not_called()


class ReaderBindingTests(unittest.TestCase):
    def owner(self):
        owner = ReadBatch(17, share=True)
        owner._process = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(),
            wait=Mock(return_value=0), kill=Mock())
        self.addCleanup(owner.close)
        return owner

    def test_bind_reuses_worker_and_does_not_leak_context(self):
        owner = self.owner()
        owner._line = Mock(side_effect=['first\n', '{"event":"reader_result","sequence":1,"code":0}\n',
            'second\n', '{"event":"reader_result","sequence":2,"code":0}\n'])
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('must not respawn')):
            with owner.bind():
                self.assertIs(_active.get(), owner)
                self.assertEqual(owner.query(['--catalog']), 'first\n')
            self.assertIsNone(_active.get())
            with owner.bind():
                with ReadBatch(17) as borrowed:
                    self.assertEqual(borrowed.query(['--catalog']), 'second\n')
            self.assertIsNone(_active.get())
        owner._process.wait.assert_not_called()

    def test_failed_binding_cannot_restart_or_return_stale_data(self):
        owner = self.owner()
        owner._line = Mock(side_effect=RuntimeQueryError('lost process'))
        with self.assertRaises(RuntimeQueryError):
            with owner.bind():
                owner.query(['--catalog'])
        self.assertIsNone(_active.get())
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('no restart')):
            with self.assertRaisesRegex(RuntimeQueryError, 'closed'):
                with owner.bind(): pass

class ReaderHandshakeTests(unittest.TestCase):
    def test_protocol_version_capability_and_strict_handshake(self):
        import json
        for ready,expected in (({'event':'reader_ready','pid':17,'version':1},False),({'event':'reader_ready','pid':17,'version':2},True),({'event':'reader_ready','pid':17,'version':3},True),({'event':'reader_ready','pid':17,'version':4},None),([],None),({'event':'reader_ready','pid':17,'version':True},None),({'event':'reader_ready','pid':18,'version':2},None),({'event':'reader_ready','pid':17,'version':2,'extra':1},None)):
            process=SimpleNamespace(stdin=io.StringIO(),stdout=io.StringIO(),wait=Mock(return_value=0),kill=Mock())
            batch=ReadBatch(17,_executable='worker.exe');batch._line=Mock(return_value=json.dumps(ready))
            with self.subTest(ready=ready),patch('expedition33._reader.subprocess.Popen',return_value=process):
                if expected is None:
                    with self.assertRaises(RuntimeQueryError):batch.__enter__()
                    self.assertTrue(batch._closed)
                else:
                    with batch:
                        self.assertIs(batch.supports_catalog_values,expected)
                        self.assertIs(batch.supports_asset_names,ready['version']>=3)
                self.assertIsNone(_active.get())
