"""Original core set semantics over the E33 adapter; separate from live proof."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from expedition33.catalog import Catalog, CatalogObject, ClassRelation
from expedition33.introspection import Harness, UnsupportedCapability
from expedition33.invocation import InvocationError
from expedition33 import RuntimeQueryError
from test_catalog import fixture


class HarnessAssignmentTests(unittest.TestCase):
    def setUp(self):
        objects, classes = fixture()
        classes.append(ClassRelation(6, 1, 'Package', 0, 64))
        objects.append(CatalogObject(123, 6, 1, 8192, 'Package', 'Class', 'Class', 1, -1, 0, 0, 0))
        self.catalog = Catalog(123, objects, classes)
        self.session = SimpleNamespace(supports_reflected_invocation=True,
            supports_retained_invocation=False, supports_object_assignment=True, assign_object=Mock())
        self.h = Harness(self.session)
        self.state = None
        self.prop = dict(owner_index=2, name='Child', type='ObjectProperty', flags=0,
                         dimension=1, offset=48, property_class_index=2)
        def refresh():
            b = self.h._backend
            b.catalog = self.catalog
            b._struct_class, b._function_class = 1, 999
            b.descriptors, b.properties, b.function_children, b.observations = {}, {}, {}, {}
        self.h._backend.refresh = refresh
        def describe(_catalog, targets):
            return {obj.index:SimpleNamespace(properties=[self.prop], owners=[{'index':i} for i in (3,2,0)]) for obj in targets}
        def read(_catalog, _obj):
            return SimpleNamespace(types={(2,'Child'):'ObjectProperty'}, errors={}, values={(2,'Child'):self.state})
        def assign(_obj, _owner, _name, value, **kwargs):
            self.assertIs(kwargs['allow_mutation'], True)
            self.assertEqual(kwargs['expected'], self.state)
            self.state = value
        self.session.assign_object.side_effect = assign
        self.patches = [patch('expedition33.introspection.describe', side_effect=describe),
                        patch('expedition33.introspection.read_values', side_effect=read)]
        for p in self.patches: p.start()
        self.addCleanup(lambda: [p.stop() for p in self.patches])
        self.addCleanup(self.h.close)
        self.request = dict(op='set', target={'$object':self.catalog.path_name(self.catalog.by_index[5])},
                            member='Child', value={'$object':self.catalog.path_name(self.catalog.by_index[4])}, allow_mutation=True)

    def test_original_before_after_and_restoration(self):
        result = self.h.request(self.request)
        self.assertIsNone(result['before'])
        self.assertEqual(result['after']['$object'], self.request['value']['$object'])
        restored = self.h.request(dict(self.request, value=None))
        self.assertEqual(restored['before'], result['after'])
        self.assertIsNone(restored['after'])
        self.assertFalse(self.h._backend.mutation_authorized)

    def test_mutation_opt_in_and_property_type_rejections(self):
        for flag in (False, 1, 'true'):
            with self.assertRaises(ValueError): self.h.request(dict(self.request, allow_mutation=flag))
        self.prop['type'] = 'StrProperty'
        with self.assertRaises(UnsupportedCapability): self.h.request(self.request)
        self.session.assign_object.assert_not_called()

    def test_failure_does_not_leave_authorization_or_retry(self):
        self.session.assign_object.side_effect = InvocationError('changed old reference', outcome='not_dispatched', native_error=4)
        with self.assertRaises(InvocationError): self.h.request(self.request)
        self.assertFalse(self.h._backend.mutation_authorized)
        self.assertEqual(self.session.assign_object.call_count, 1)

    def test_post_write_refresh_failure_reports_completed_dispatch(self):
        refresh = self.h._backend.refresh
        calls = 0
        def fail_second():
            nonlocal calls
            calls += 1
            if calls == 2: raise RuntimeQueryError('post-write catalog failed')
            refresh()
        self.h._backend.refresh = fail_second
        with self.assertRaises(InvocationError) as caught: self.h.request(self.request)
        self.assertEqual(caught.exception.outcome, 'dispatch_returned')
        self.assertEqual(self.session.assign_object.call_count, 1)

    def test_capability_is_partial_and_old_backend_rejects_set(self):
        self.assertEqual(self.h.request({'op':'status'})['write_types'], ['ObjectProperty'])
        self.session.supports_object_assignment = False
        with Harness(self.session) as old:
            with self.assertRaises(UnsupportedCapability): old.request(self.request)
