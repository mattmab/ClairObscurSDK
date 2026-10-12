import unittest
from dataclasses import replace
from unittest.mock import patch
from expedition33.catalog import Catalog
from expedition33._scope import SessionScope
from expedition33.invocation import InvocationError
import test_retained_results

class SelectedFactoryObservationTests(unittest.TestCase):
    setUp=test_retained_results.RetainedResultTests.setUp

    def test_factory_selected_result_keeps_descriptor_catalog_and_owned_identity(self):
        original=self.p.catalog
        created=replace(self.p.target,index=max(original.by_index)+1,address=self.p.target.address+0x10000,name='CreatedMusic')
        full=Catalog(original.pid,(*original.objects,created),tuple(original.classes.values()))
        selected=full.subset((created,))
        self.assertNotIn(self.p.function.index,selected.by_index)
        self.transport.obj=created
        scope=SessionScope(self.session)
        planner=scope.invocation_planner(catalog=original,selected_results=True)
        self.addCleanup(planner.close)
        prepared=planner.prepare(self.p.target,self.p.function)
        with patch('expedition33.catalog.capture',side_effect=AssertionError('full result scan')),patch('expedition33.catalog.capture_selected',return_value=selected) as select:
            result=prepared.invoke(refresh_from_result=True)
        self.assertEqual(result.return_value,created)
        self.assertEqual(planner._catalog.resolve(created),created)
        for observed in original.objects:
            self.assertEqual(planner._catalog.resolve(observed),observed)
        self.assertEqual(len(select.call_args.args[1]),1)
        self.assertTrue(result.active)
        with patch('expedition33.invocation.prepare_call',return_value=prepared._plan) as next_plan:
            planner.prepare(created,self.p.function)
            self.assertEqual(next_plan.call_args.args[0].resolve(self.p.function),self.p.function)
        scope.close()
        self.assertFalse(result.active)
        self.assertFalse(self.transport.tokens)

    def test_selected_result_identity_mismatch_releases_factory_lease_no_retry(self):
        original=self.p.catalog
        created=replace(self.p.target,index=max(original.by_index)+1,address=self.p.target.address+0x10000,name='CreatedAudio')
        changed=replace(created,serial=created.serial+1)
        selected=Catalog(original.pid,(*original.objects,changed),tuple(original.classes.values())).subset((changed,))
        self.transport.obj=created
        scope=SessionScope(self.session)
        planner=scope.invocation_planner(catalog=original,selected_results=True)
        self.addCleanup(planner.close)
        prepared=planner.prepare(self.p.target,self.p.function)
        with patch('expedition33.catalog.capture',side_effect=AssertionError('full result scan')),patch('expedition33.catalog.capture_selected',return_value=selected):
            with self.assertRaises(InvocationError):prepared.invoke(refresh_from_result=True)
        self.assertIsNone(planner._catalog)
        self.assertEqual(self.transport.calls.count('retained-invoke'),1)
        self.assertFalse(self.transport.tokens)
        scope.close()

if __name__=='__main__':unittest.main()

