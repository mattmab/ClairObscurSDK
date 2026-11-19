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

    def test_transient_discovery_read_is_discarded_and_reobserved_once(self):
        from types import SimpleNamespace
        catalog=SimpleNamespace(objects=())
        with patch('expedition33._reader.active_reader', return_value=None), \
                patch('expedition33._reader.ReadBatch') as readers, \
                patch('expedition33.catalog._query', side_effect=[RuntimeQueryError('READ_FAILED address=0x123 size=40'),({'pid':123},[])]) as query, \
                patch('expedition33.catalog._decode_catalog', return_value=catalog) as decode:
            self.assertIs(capture_matching(123,names=('Create',)),catalog)
        self.assertEqual(query.call_count,2)
        self.assertEqual(readers.call_count,2)
        self.assertEqual(query.call_args_list[0],query.call_args_list[1])
        decode.assert_called_once_with({'pid':123},[])

    def test_borrowed_discovery_read_failure_yields_without_reusing_terminal_reader(self):
        with patch('expedition33._reader.active_reader', return_value=object()), \
                patch('expedition33.catalog._query', side_effect=RuntimeQueryError('READ_FAILED address=0x123 size=40')) as query, \
                patch('expedition33.catalog._decode_catalog') as decode:
            with self.assertRaisesRegex(RuntimeQueryError,'READ_FAILED'):
                capture_matching(123,names=('Create',))
        self.assertEqual(query.call_count,1);decode.assert_not_called()

    def test_standalone_discovery_has_only_one_fresh_retry(self):
        with patch('expedition33._reader.active_reader', return_value=None), \
                patch('expedition33._reader.ReadBatch') as readers, \
                patch('expedition33.catalog._query', side_effect=RuntimeQueryError('READ_FAILED address=0x123')) as query:
            with self.assertRaisesRegex(RuntimeQueryError,'READ_FAILED'):
                capture_matching(123,names=('Create',))
        self.assertEqual(query.call_count,2);self.assertEqual(readers.call_count,2)
