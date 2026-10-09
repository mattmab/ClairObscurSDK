import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import capture_matching


class MatchingCatalogTests(unittest.TestCase):
    def test_invalid_selectors_never_start_reader(self):
        with patch('expedition33._reader.ReadBatch', side_effect=AssertionError('no worker')):
            for names in ((), ('Widget,Other',), ('a\nb',), ('a', 'a'), (12,), ('a' * 1025,)):
                with self.assertRaises(ValueError): capture_matching(123, names=names)
            with self.assertRaises(ValueError): capture_matching(True, names=('Widget',))

    def test_selector_encoding_and_changed_process_rejection(self):
        with patch('expedition33._reader.active_reader', return_value=object()), \
                patch('expedition33.catalog._query', return_value=({'pid':124}, [])) as query, \
                patch('expedition33.catalog._decode_catalog', side_effect=AssertionError('no decode')):
            with self.assertRaisesRegex(RuntimeQueryError, 'process changed'):
                capture_matching(123, names=('Create',), classes=('PlayerController',))
        query.assert_called_once_with(['--catalog-match', '123', 'n=Create,c=PlayerController'])

    def test_worker_failure_never_falls_back_to_full_capture(self):
        with patch('expedition33._reader.active_reader', return_value=object()), \
                patch('expedition33.catalog._query', side_effect=RuntimeQueryError('identity changed')) as query:
            with self.assertRaisesRegex(RuntimeQueryError, 'identity changed'):
                capture_matching(123, names=('Create',))
        self.assertEqual(query.call_count, 1)
