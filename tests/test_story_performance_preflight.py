import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_performance_preflight import PerformancePreflight,warm,_pod_closure


class PerformanceMetadataTests(unittest.TestCase):
    def test_transform_schema_includes_nested_quat_and_vector_before_planning(self):
        objects={i:N(index=i,serial=i+10,address=i*100) for i in range(1,5)}
        catalog=N(by_index=objects);catalog.with_observations=lambda other:catalog
        def descriptor(i,children=()):
            return N(object=objects[i],properties=tuple(dict(type='StructProperty',struct_index=x) for x in children))
        first=N(catalog=catalog,descriptors={1:descriptor(1,(2,))})
        transform=N(catalog=catalog,descriptors={2:descriptor(2,(3,4))})
        children=N(catalog=catalog,descriptors={3:descriptor(3),4:descriptor(4)})
        with patch('expedition33.reflection.describe_selected',side_effect=(transform,children)) as read:
            observed,descriptors=_pod_closure(7,first)
        self.assertIs(observed,catalog);self.assertEqual(set(descriptors),{1,2,3,4})
        self.assertEqual(read.call_count,2)
        self.assertEqual(read.call_args_list[1].args,(7,((3,13,300),(4,14,400))))

    def test_failed_nested_schema_never_publishes_partial_cache_or_retries(self):
        from expedition33 import RuntimeQueryError
        from expedition33.story_preflight import PreflightReadDeferred
        child=N(index=2,serial=12,address=200)
        first=N(catalog=N(by_index={2:child}),descriptors={1:N(properties=({'type':'StructProperty','struct_index':2},))})
        with patch('expedition33.reflection.describe_selected',side_effect=RuntimeQueryError('retired type')) as read:
            with self.assertRaises(PreflightReadDeferred):_pod_closure(7,first)
        read.assert_called_once();self.assertEqual(set(first.descriptors),{1})

    def test_asset_warmup_is_shared_without_caching_a_pawn(self):
        resources=Mock();session=N(_story_construction_resources=N(resources=resources))
        scope=N(_session=session,_check=Mock())
        owner=object()
        with patch('expedition33.story_performance_preflight.PerformancePreflight',return_value=owner) as factory:
            self.assertIs(warm(scope,('body-a','body-a','body-b')),owner)
            self.assertIs(warm(scope,('body-b',)),owner)
        factory.assert_called_once_with(scope)
        self.assertEqual([c.args for c in resources.load.call_args_list],[('body-a',),('body-b',),('body-b',)])
        self.assertEqual(set(vars(session)),{'_story_construction_resources','_story_performance_preflight'})

    def test_planning_selects_fresh_target_and_argument_identities(self):
        owner=PerformancePreflight.__new__(PerformancePreflight);owner.session=object();owner.paths={'path'};owner.observations=object()
        scope=Mock(pid=7,_session=owner.session)
        actor=N(index=1,serial=2,address=0x10000)
        clip=N(index=3,serial=4,address=0x30000,class_index=100)
        fresh=object()
        with patch('expedition33.catalog.capture_selected',return_value=fresh) as capture:
            planner=owner.planner(scope,actor,'path',{'Asset':clip,'LoopCount':1})
        capture.assert_called_once_with(7,((1,2,0x10000),(3,4,0x30000)))
        planner.adopt_observations.assert_called_once_with(fresh)
        scope.invocation_planner.assert_called_once_with(observations=owner.observations,selected_results=True)
        planner.prepare.assert_not_called()  # Metadata reuse is not dispatch authority.

    def test_session_or_function_mismatch_never_plans(self):
        owner=PerformancePreflight.__new__(PerformancePreflight);owner.session=object();owner.paths={'path'}
        scope=Mock(_session=object())
        with self.assertRaises(ValueError):owner.planner(scope,object(),'path',{})
        scope._session=owner.session
        with self.assertRaises(ValueError):owner.planner(scope,object(),'other',{})
        scope.invocation_planner.assert_not_called()

    def test_failed_fresh_identity_capture_releases_planner_without_fallback(self):
        owner=PerformancePreflight.__new__(PerformancePreflight);owner.session=object();owner.paths={'path'};owner.observations=object()
        scope=Mock(pid=7,_session=owner.session);actor=N(index=1,serial=2,address=0x10000)
        with patch('expedition33.catalog.capture_selected',side_effect=RuntimeError('retired pawn')):
            with self.assertRaisesRegex(RuntimeError,'retired pawn'):owner.planner(scope,actor,'path',{})
        scope.invocation_planner.return_value.close.assert_called_once()


if __name__=='__main__':unittest.main()
