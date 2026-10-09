from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch
import unittest

from expedition33 import RuntimeQueryError
from expedition33.introspection import _Backend
import test_invocation


class TraceSchemaBrowsingTests(unittest.TestCase):
    def fixture(self):
        sample = test_invocation.InvocationTests()
        sample.setUp()
        descriptor = SimpleNamespace(object=sample.function,
            owners=({'index': 7},), properties=(), function={})
        plan = SimpleNamespace(descriptor=descriptor)
        session = SimpleNamespace(_trace_plan_for=lambda obj: plan if obj.index == 7 else None)
        backend = _Backend(session)
        backend.catalog = sample.catalog
        return backend, sample, descriptor

    def test_mixed_batch_reads_only_unhooked_metadata_and_clears_provenance(self):
        backend, sample, descriptor = self.fixture()
        other = SimpleNamespace(owners=({'index': 5},), properties=())
        with patch('expedition33.introspection.describe', return_value={5: other}) as reader:
            backend.ensure_described((sample.function, sample.target))
            reader.assert_called_once_with(sample.catalog, (sample.target,))
        self.assertIs(backend.descriptors[7], descriptor)
        self.assertEqual(backend.retained_trace_schemas, {7})
        backend.clear()
        self.assertFalse(backend.retained_trace_schemas)

    def test_stale_retained_identity_fails_without_reader_fallback(self):
        backend, sample, descriptor = self.fixture()
        descriptor.object = replace(sample.function, serial=999)
        with patch('expedition33.introspection.describe') as reader:
            with self.assertRaises(RuntimeQueryError):
                backend.ensure_described((sample.function,))
            reader.assert_not_called()
        self.assertFalse(backend.descriptors)

    def test_without_owned_trace_reader_errors_are_preserved(self):
        backend, sample, descriptor = self.fixture()
        backend.session = None
        with patch('expedition33.introspection.describe', side_effect=RuntimeQueryError('foreign hook')):
            with self.assertRaisesRegex(RuntimeQueryError, 'foreign hook'):
                backend.ensure_described((sample.function,))
