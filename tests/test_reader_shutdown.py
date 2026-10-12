"""Actual ReadBatch terminal/reset contract under candidate launcher ordering."""
import io
import pathlib
import sys
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import RuntimeQueryError
from expedition33._reader import ReadBatch, _active, active_reader


class ShutdownReaderTests(unittest.TestCase):
    @contextmanager
    def reader(self):
        # Substitute only OS process I/O. Actual query failure, close, contextvar
        # retention, borrower rejection and __exit__ are the production code.
        owner = ReadBatch(17, share=True)
        owner._process = SimpleNamespace(stdin=io.StringIO(), stdout=io.StringIO(),
            wait=Mock(return_value=0), kill=Mock())
        owner._line = Mock(side_effect=RuntimeQueryError('injected original read failure'))
        owner._token = _active.set(owner)
        try:
            yield owner
        finally:
            owner.__exit__()

    @contextmanager
    def loader(self, cleaned):
        try:
            yield
        finally:
            # NativeManagementMenu.close starts by entering a read operation.
            # With an active failed owner this is the same production rejection.
            if active_reader() is not None:
                with ReadBatch(17):
                    pass
            cleaned.append('loader cleanup outside failed read operation')

    def fail(self, owner):
        with self.assertRaisesRegex(RuntimeQueryError, 'original read failure'):
            owner.query(['--catalog'])
        self.assertTrue(owner._closed)
        self.assertIs(active_reader(), owner)
        with patch('expedition33._reader.subprocess.Popen', side_effect=AssertionError('no implicit restart')):
            with self.assertRaisesRegex(RuntimeQueryError, 'closed'):
                with ReadBatch(17):
                    pass

    def test_current_order_reproduces_shutdown_error(self):
        cleaned = []
        with self.assertRaisesRegex(RuntimeQueryError, 'closed'):
            with self.reader() as owner, self.loader(cleaned):
                self.fail(owner)
        self.assertEqual(cleaned, [])
        self.assertIsNone(active_reader())

    def test_proposed_order_exits_terminal_reader_before_mod_cleanup(self):
        cleaned = []
        with self.loader(cleaned), self.reader() as owner:
            self.fail(owner)
        self.assertEqual(len(cleaned), 1)
        self.assertIsNone(active_reader())
        owner._process.wait.assert_called_once()

    def test_proposed_order_preserves_original_loop_exception(self):
        cleaned = []
        original = ValueError('controller loop failure')
        with self.assertRaises(ValueError) as caught:
            with self.loader(cleaned), self.reader() as owner:
                self.fail(owner)
                raise original
        self.assertIs(caught.exception, original)
        self.assertEqual(len(cleaned), 1)
        self.assertIsNone(active_reader())


if __name__ == '__main__': unittest.main()

