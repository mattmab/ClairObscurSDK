import unittest
from unittest.mock import Mock
from expedition33 import RuntimeQueryError
from expedition33.invocation import InvocationError
from expedition33.story_preflight import PreflightReadDeferred,observe


class SafeReadTests(unittest.TestCase):
    def test_external_read_failure_is_explicitly_retryable(self):
        original=RuntimeQueryError('selected read worker ended')
        reader=Mock(side_effect=original)
        with self.assertRaises(PreflightReadDeferred) as result:observe(reader,'actor',fields=('Body',))
        self.assertIs(result.exception.__cause__,original)
        reader.assert_called_once_with('actor',fields=('Body',))

    def test_native_outcome_is_never_reclassified(self):
        for outcome in ('unknown','not_dispatched','dispatch_returned'):
            original=InvocationError('native operation failed',outcome=outcome)
            with self.assertRaises(InvocationError) as result:observe(Mock(side_effect=original))
            self.assertIs(result.exception,original)
            self.assertNotIsInstance(result.exception,PreflightReadDeferred)

    def test_unknown_failure_type_is_not_assumed_read_only(self):
        original=RuntimeError('asset owner uncertain')
        with self.assertRaises(RuntimeError) as result:observe(Mock(side_effect=original))
        self.assertIs(result.exception,original)


if __name__=='__main__':unittest.main()
