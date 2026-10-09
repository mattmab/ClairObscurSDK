from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError
from expedition33._planning_metadata import MetadataObservations
from expedition33.catalog import Catalog
import test_invocation
import test_prepared_invocation


class MetadataObservationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_invocation.InvocationTests()
        self.fixture.setUp()
        self.catalog = self.fixture.catalog
        self.function = self.fixture.function
        self.cache = MetadataObservations()
        self.descriptor = SimpleNamespace(owners=({'index': self.function.index},),
            properties=({'property_class_index': self.fixture.target.index},))
        self.reader = Mock(return_value={self.function.index: self.descriptor})

    def read(self, catalog=None, function=None):
        return self.cache.read('struct', catalog or self.catalog,
                               [function or self.function], self.reader)

    def test_reuses_observation_and_explicit_clear_reads_again(self):
        self.read(); self.read()
        self.assertEqual(self.reader.call_count, 1)
        self.cache.clear(); self.read()
        self.assertEqual(self.reader.call_count, 2)

    def test_dependency_recycling_rejects_cached_descriptor_without_fallback(self):
        self.read()
        target = self.fixture.target
        changed = Catalog(self.catalog.pid,
            [replace(obj, serial=999) if obj.index == target.index else obj for obj in self.catalog.objects],
            tuple(self.catalog.classes.values()))
        with self.assertRaises(RuntimeQueryError): self.read(changed)
        self.assertEqual(self.reader.call_count, 1)

    def test_recycled_function_requires_new_read(self):
        self.read()
        function = replace(self.function, serial=999)
        changed = Catalog(self.catalog.pid,
            [function if obj.index == function.index else obj for obj in self.catalog.objects],
            tuple(self.catalog.classes.values()))
        self.read(changed, function)
        self.assertEqual(self.reader.call_count, 2)

    def test_failed_reader_does_not_create_cached_result(self):
        self.reader.side_effect = RuntimeQueryError('read failed')
        with self.assertRaises(RuntimeQueryError): self.read()
        self.assertFalse(self.cache._entries)


class PlannerMetadataIntegrationTests(unittest.TestCase):
    setUp = test_prepared_invocation.PreparedTextTests.setUp
    session = test_prepared_invocation.PreparedTextTests.session
    response = test_prepared_invocation.PreparedTextTests.response

    def test_rebind_reuses_schema_but_refresh_revokes_observations(self):
        session, transport, _ = self.session()
        from expedition33 import invocation
        with patch('expedition33.catalog.capture', return_value=self.p.catalog), \
                patch('expedition33.invocation.describe', wraps=invocation.describe) as reader:
            with session.invocation_planner() as planner:
                original = planner.prepare(self.p.target, self.p.function, Input='one')
                original.bind(Input='two')
                self.assertEqual(reader.call_count, 1)
                planner.refresh()
                with self.assertRaisesRegex(RuntimeError, 'revoked'): original.invoke()
                planner.prepare(self.p.target, self.p.function, Input='three')
                self.assertEqual(reader.call_count, 2)
            self.assertFalse(planner._metadata._entries)
        self.assertFalse(transport.calls)
