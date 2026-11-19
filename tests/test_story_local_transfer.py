import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_local_transfer import PreparedStoryLanding

class LocalTransferTests(unittest.TestCase):
    def owner(self):
        o=PreparedStoryLanding.__new__(PreparedStoryLanding)
        o.scope=object();o.ctx={'visit':(1,2,3)};o.position=(10.,20.,192.);o.floor_height=100.;o.half_height=90.;o._prepare_call=Mock()
        o.closed=o.unknown=o.ready=False
        o.query=N(query=Mock(return_value=N(collision_ready=True,streaming_pending=0,support_heights=(100.,)*5)))
        o.call=Mock();return o
    def test_collision_or_streaming_failure_never_arms_landing(self):
        o=self.owner();self.assertTrue(o.qualify())
        o.query.query.return_value.streaming_pending=1;self.assertFalse(o.qualify())
        o.query.query.return_value.streaming_pending=0;o.query.query.return_value.support_heights=(100.,100.,100.,50.,100.)
        self.assertFalse(o.qualify());o.call.invoke.assert_not_called()
    def test_pending_readiness_read_disarms_without_mutation_or_unknown(self):
        from expedition33.map_readiness import ReadinessPending
        o=self.owner();o.ready=True;o.query.query.side_effect=ReadinessPending('pending')
        self.assertFalse(o.qualify());self.assertFalse(o.unknown);o.call.invoke.assert_not_called()
    def test_unqualified_or_replaced_possession_never_dispatches(self):
        o=self.owner()
        with self.assertRaisesRegex(RuntimeError,'qualified'):o.transfer(None)
        o.ready=True
        with patch('expedition33.story_local_transfer.context',return_value={'visit':(4,5,6)}):
            with self.assertRaisesRegex(RuntimeError,'possession'):o.transfer(None)
        o.call.invoke.assert_not_called()
    def test_uncertain_dispatch_is_not_replayed(self):
        o=self.owner();o.ready=True;o.call.invoke.side_effect=RuntimeError('uncertain')
        with patch('expedition33.story_local_transfer.context',return_value=o.ctx):
            with self.assertRaisesRegex(RuntimeError,'uncertain'):o.transfer(None)
            with self.assertRaisesRegex(RuntimeError,'qualified'):o.transfer(None)
        o.call.invoke.assert_called_once();self.assertFalse(o.close())
    def test_known_preflight_rejection_disarms_without_unknown_or_replay(self):
        from expedition33.invocation import InvocationError
        o=self.owner();o.ready=True
        o.call.invoke.side_effect=InvocationError('identity changed',outcome='not_dispatched',native_error=202)
        with patch('expedition33.story_local_transfer.context',return_value=o.ctx):
            with self.assertRaises(InvocationError):o.transfer(None)
            with self.assertRaisesRegex(RuntimeError,'qualified'):o.transfer(None)
        self.assertFalse(o.unknown);self.assertFalse(o.ready);o.call.invoke.assert_called_once()


class LandingPreparationTests(unittest.TestCase):
    def fixture(self,warm=True):
        pawn=N(index=1,serial=2,address=0x10000);capsule=N(index=3,serial=4,address=0x20000,outer_index=1,outer_serial=2)
        catalog=Mock(by_index={1:pawn});catalog.with_observations.return_value=catalog;function=object();catalog.find_path.return_value=function
        values=N(errors={},truncated=False,values={(1,'CapsuleComponent'):capsule})
        size=N(errors={},truncated=False,values={(1,'CapsuleHalfHeight'):90.,(1,'RelativeScale3D'):N(fields={'Z':1.})})
        planner=Mock();construction=Mock();construction.movement_planner.return_value=planner
        scope=N(pid=1,_session=N(_story_construction_resources=construction if warm else None),invocation_planner=Mock(return_value=planner))
        parent=N(pid=1,_world_binding_token='saved-world')
        return parent,scope,catalog,values,size,construction,planner,function
    def test_warm_preparation_reads_pawn_and_capsule_but_never_releases_process_metadata(self):
        from expedition33 import story_local_transfer as source
        parent,scope,catalog,values,size,construction,planner,function=self.fixture()
        with patch.object(source,'SessionScope',return_value=scope),patch.object(source,'NativeMapReadiness'),patch.object(source,'capture_selected_values',return_value=(catalog,{1:values})) as fresh,patch.object(source,'read_values_with_references',return_value=(size,catalog)) as dimensions,patch.object(source,'capture_matching') as scan,patch('expedition33._stable_lease.acquire_stable') as lease:
            owner=PreparedStoryLanding(parent,object(),{'pawn':[1,2,0x10000]},(1.,2.,3.),4.,floor_height=0.)
        fresh.assert_called_once_with(1,((1,2,0x10000),),fields=('CapsuleComponent',),references=True)
        dimensions.assert_called_once();scan.assert_not_called();lease.assert_not_called()
        construction.catalog.assert_called_once_with(scope,('K2_TeleportTo',));construction.movement_planner.assert_called_once_with(scope,catalog)
        self.assertIs(owner.teleport,function);self.assertIsNone(owner.teleport_lease);self.assertEqual(owner.half_height,90.)
        planner.prepare.assert_called_once_with(catalog.by_index[1],function,DestLocation=dict(X=1.,Y=2.,Z=3.),DestRotation=dict(Pitch=0.,Yaw=4.,Roll=0.))
        planner.prepare.return_value.invoke.assert_not_called()
    def test_rebound_or_incomplete_capsule_rejects_before_planning(self):
        from expedition33 import story_local_transfer as source
        for changed in ('owner','read'):
            parent,scope,catalog,values,size,construction,planner,function=self.fixture()
            if changed=='owner':values.values[(1,'CapsuleComponent')].outer_serial=99
            else:values.errors={'capsule':'incomplete'}
            with patch.object(source,'SessionScope',return_value=scope),patch.object(source,'NativeMapReadiness'),patch.object(source,'capture_selected_values',return_value=(catalog,{1:values})):
                with self.assertRaisesRegex(RuntimeError,'capsule'):PreparedStoryLanding(parent,object(),{'pawn':[1,2,0x10000]},(1.,2.,3.),4.,floor_height=0.)
            construction.catalog.assert_not_called();planner.prepare.assert_not_called()
    def test_generic_preparation_keeps_its_own_teleport_lease(self):
        from expedition33 import story_local_transfer as source
        parent,scope,catalog,values,size,construction,planner,function=self.fixture(warm=False)
        held=N(object=function)
        with patch.object(source,'SessionScope',return_value=scope),patch.object(source,'NativeMapReadiness'),patch.object(source,'capture_selected_values',return_value=(catalog,{1:values})),patch.object(source,'read_values_with_references',return_value=(size,catalog)),patch.object(source,'capture_matching',return_value=catalog),patch.object(source,'capture_selected',return_value=catalog),patch('expedition33._stable_lease.acquire_stable',return_value=(held,catalog)) as lease:
            owner=PreparedStoryLanding(parent,object(),{'pawn':[1,2,0x10000]},(1.,2.,3.),4.,floor_height=0.)
        self.assertIs(owner.teleport_lease,held);lease.assert_called_once_with(scope,function)
        construction.movement_planner.assert_not_called()
