import unittest
from types import SimpleNamespace
from unittest.mock import patch,Mock,MagicMock
from expedition33.story_arrival import StorySceneArrival
from expedition33.map_readiness import NativeMapReadiness,ReadinessPending

class ArrivalTests(unittest.TestCase):
    def test_explicit_return_position_is_placed_without_custom_layers(self):
        a=self.owner();a.state='new';a.layer_states={};a.layers=Mock();a.runtime=None
        a.position=(-1500.,-8840.,22.);a.yaw=-35.;a.token='token'
        planner=MagicMock();a.scope=MagicMock();a.scope.pid=1
        a.scope._session._story_construction_resources=None
        a.scope.invocation_planner.return_value.__enter__.return_value=planner
        planner.prepare.return_value.invoke.return_value.__enter__.return_value=SimpleNamespace(return_value=True)
        catalog=Mock();catalog.by_index={4:object()};catalog.with_observations.return_value=catalog
        query=Mock();query.query.side_effect=ReadinessPending('streaming')
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.capture_selected',return_value=catalog),patch('expedition33.story_arrival.capture_matching'),patch('expedition33.story_arrival.MapRuntime'),patch('expedition33.story_arrival.NativeMapReadiness',return_value=query):
            self.assertFalse(a.advance())
        self.assertEqual(a.state,'observing')
        self.assertEqual(planner.prepare.call_args.kwargs['DestLocation'],dict(X=-1500.,Y=-8840.,Z=22.))
        a.layers.requested_ready.assert_not_called()
        query.query.assert_called_once_with()
    def owner(self,*,collision=True,visual=True,height=9148.6):
        a=object.__new__(StorySceneArrival);a.state='observing';a.scope=object();a.ctx={'visit':[1,2,3],'pawn':[4,5,6]};a.floor_height=9148.6
        a.gate=SimpleNamespace(status=lambda:{'state':2,'world':[1,2,3],'pawn':[4,5,6]})
        a.runtime=SimpleNamespace(close=lambda:True)
        a.query=SimpleNamespace(query=lambda:SimpleNamespace(collision_ready=collision,visual_ready=visual,support_heights=(height,)*5))
        return a
    def test_arrival_requires_floor_and_streaming_evidence(self):
        for collision,visual,height,ready in ((True,True,9148.6,True),(False,True,9148.6,False),(True,False,9148.6,False),(True,True,192.,False)):
            a=self.owner(collision=collision,visual=visual,height=height)
            with patch('expedition33.story_arrival.context',return_value=a.ctx):self.assertEqual(a.advance(),ready)
    def test_changed_possession_cannot_complete_arrival(self):
        a=self.owner()
        with patch('expedition33.story_arrival.context',return_value={'visit':[1,2,3],'pawn':[7,8,9]}):
            with self.assertRaises(RuntimeError):a.advance()
        self.assertEqual(a.state,'observing')
    def test_unconfirmed_hold_defers_readiness(self):
        a=self.owner();a.gate.status=lambda:{'state':1,'world':[1,2,3],'pawn':[4,5,6]}
        a.query.query=lambda:(_ for _ in ()).throw(AssertionError('No query without hold'))
        with patch('expedition33.story_arrival.context',return_value=a.ctx):self.assertFalse(a.advance())
    def test_saved_checkpoint_finishes_floor_proof_after_its_hold_ended(self):
        for collision,expected in ((False,False),(True,True)):
            a=self.owner(collision=collision);a.position=None
            a.gate.status=lambda:{'state':1,'world':[1,2,3],'pawn':[4,5,6],'hold_sequence':1}
            with patch('expedition33.story_arrival.context',return_value=a.ctx):self.assertEqual(a.advance(),expected)
    def test_released_hold_cannot_admit_pending_teleport(self):
        a=self.owner();a.position=(1.,2.,3.)
        a.gate.status=lambda:{'state':1,'world':[1,2,3],'pawn':[4,5,6],'hold_sequence':1}
        a.query.query=Mock(side_effect=AssertionError('No placement without hold'))
        with patch('expedition33.story_arrival.context',return_value=a.ctx):self.assertFalse(a.advance())
    def new_owner(self,*,layers=True):
        a=self.owner();a.state='new';a.position=None;a.token='token';a.runtime=None
        a.layer_states={'floor':2} if layers else {};a.layers=Mock()
        a.layers.requested_ready.return_value=True
        runtime=Mock();runtime.close.return_value=True
        query=Mock();query.query.return_value=SimpleNamespace(collision_ready=True,visual_ready=True,support_heights=(9148.6,)*5)
        return a,runtime,query
    def test_already_ready_scene_completes_without_scheduler_yields(self):
        for layers in (True,False):
            with self.subTest(layers=layers):
                a,runtime,query=self.new_owner(layers=layers)
                with patch('expedition33.story_arrival.context',return_value=a.ctx) as context,patch('expedition33.story_arrival.MapRuntime',return_value=runtime),patch('expedition33.story_arrival.NativeMapReadiness',return_value=query):
                    self.assertTrue(a.advance())
                    self.assertTrue(a.advance())
                self.assertEqual(a.state,'ready');self.assertEqual(context.call_count,3)
                query.query.assert_called_once_with();runtime.close.assert_called_once_with()
                self.assertEqual(set(a.timings),{'new','layers','observing'})
                self.assertTrue(all(row['count']==1 for row in a.timings.values()))
                if layers:a.layers.apply.assert_called_once_with()
                else:a.layers.apply.assert_not_called()
    def test_pending_layers_stop_without_spinning_or_reapplying(self):
        a,runtime,query=self.new_owner();a.layers.requested_ready.side_effect=(False,True)
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.MapRuntime',return_value=runtime) as constructor,patch('expedition33.story_arrival.NativeMapReadiness',return_value=query):
            self.assertFalse(a.advance());self.assertEqual(a.state,'layers')
            a.layers.requested_ready.assert_called_once_with();constructor.assert_not_called()
            self.assertTrue(a.advance())
        a.layers.apply.assert_called_once_with();query.query.assert_called_once_with()

    def test_shared_collision_owner_is_queried_and_never_destroyed(self):
        a,runtime,query=self.new_owner();a.runtime=runtime;a._owns_runtime=False
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.MapRuntime') as constructor,patch('expedition33.story_arrival.NativeMapReadiness',return_value=query) as observer:
            self.assertTrue(a.advance())
        constructor.assert_not_called();runtime.close.assert_not_called()
        observer.assert_called_once_with(runtime,a.ctx,expected_token=a.token)
        query.query.assert_called_once_with()
        self.assertEqual(a.state,'ready')
    def test_possession_change_between_phases_stops_before_observation(self):
        a,runtime,query=self.new_owner()
        changed=dict(a.ctx,pawn=[7,8,9])
        with patch('expedition33.story_arrival.context',side_effect=(a.ctx,changed)),patch('expedition33.story_arrival.MapRuntime',return_value=runtime) as constructor:
            with self.assertRaisesRegex(RuntimeError,'possession changed'):a.advance()
        self.assertEqual(a.state,'layers');constructor.assert_not_called()
        a.layers.apply.assert_called_once_with();a.layers.requested_ready.assert_not_called()
    def test_hidden_shared_collision_helpers_require_rendered_landing_support(self):
        from expedition33.map_readiness import Receipt
        from dataclasses import replace
        ready=Receipt(50,50,50,0,5,5,0,7,0,538,0,5,0,(9148.6,)*5)
        for receipt,expected in ((ready,True),(replace(ready,streaming_pending=1),False),
                (replace(ready,rendered_support_hits=4),False),
                (replace(ready,live_rows=49),False),(replace(ready,visible_rows=1),False)):
            with self.subTest(receipt=receipt):
                a=self.owner();a._owns_runtime=False;a.query.query=lambda:receipt
                with patch('expedition33.story_arrival.context',return_value=a.ctx):
                    self.assertEqual(a.advance(),expected)
    def test_hold_change_between_phases_keeps_guard_and_defers(self):
        a,runtime,query=self.new_owner();held=a.gate.status()
        a.gate.status=Mock(side_effect=(held,dict(held,state=1)))
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.MapRuntime',return_value=runtime) as constructor:
            self.assertFalse(a.advance())
        self.assertEqual(a.state,'layers');constructor.assert_not_called()
        a.layers.requested_ready.assert_not_called()
    def test_pending_collision_rechecks_once_next_call_without_rebuilding(self):
        a,runtime,query=self.new_owner()
        ready=query.query.return_value
        query.query.side_effect=(SimpleNamespace(collision_ready=False,visual_ready=True,support_heights=(9148.6,)*5),ready)
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.MapRuntime',return_value=runtime) as constructor,patch('expedition33.story_arrival.NativeMapReadiness',return_value=query):
            self.assertFalse(a.advance());self.assertEqual(query.query.call_count,1)
            self.assertEqual(a.state,'observing');runtime.close.assert_not_called()
            self.assertTrue(a.advance())
        constructor.assert_called_once_with(a.scope);a.layers.apply.assert_called_once_with()
    def test_uncertain_teleport_is_never_replayed(self):
        a,_,_=self.new_owner(layers=False);a.position=(1.,2.,3.);a.yaw=0.
        planner=MagicMock();a.scope=MagicMock();a.scope.pid=1
        a.scope._session._story_construction_resources=None
        a.scope.invocation_planner.return_value.__enter__.return_value=planner
        planner.prepare.return_value.invoke.side_effect=RuntimeError('unknown native outcome')
        catalog=Mock();catalog.by_index={4:object()};catalog.with_observations.return_value=catalog
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.capture_selected',return_value=catalog),patch('expedition33.story_arrival.capture_matching'):
            with self.assertRaisesRegex(RuntimeError,'unknown native outcome'):a.advance()
            with self.assertRaisesRegex(RuntimeError,'unavailable'):a.advance()
        self.assertEqual(a.state,'unknown');planner.prepare.return_value.invoke.assert_called_once_with()
    def native_owner(self):
        a=self.owner();a.scope=SimpleNamespace(pid=1,_check=Mock())
        a.runtime=SimpleNamespace(scope=a.scope,close=Mock(return_value=True))
        a.token=((1,1,2,3),(1,7,8,0x20000),(1,9,10,0x30000),2)
        a.query=NativeMapReadiness(a.runtime,a.ctx,expected_token=a.token)
        return a
    def test_native_observer_uses_fresh_native_proof_instead_of_duplicate_python_context(self):
        a=self.native_owner();ready=SimpleNamespace(collision_ready=True,visual_ready=True,support_heights=(9148.6,)*5)
        a.query.query=Mock(side_effect=(ReadinessPending('world/save or floor pending'),ready))
        with patch('expedition33.story_arrival.context') as context:
            self.assertFalse(a.advance());a.runtime.close.assert_not_called()
            self.assertTrue(a.advance());context.assert_not_called()
        self.assertEqual(a.query,None)
        self.assertEqual(a.scope._check.call_count,2)
    def test_native_proof_expected_save_change_rejects_before_query(self):
        a=self.native_owner();a.query.expected_token=(*a.query.expected_token[:3],3);a.query.query=Mock()
        with patch('expedition33.story_arrival.context') as context:
            with self.assertRaisesRegex(RuntimeError,'native context proof changed'):a.advance()
        a.query.query.assert_not_called();a.runtime.close.assert_not_called();context.assert_not_called()
    def test_native_observation_still_requires_current_loading_hold(self):
        a=self.native_owner();a.gate.status=lambda:dict(state=1,world=a.ctx['visit'],pawn=a.ctx['pawn']);a.query.query=Mock()
        self.assertFalse(a.advance());a.query.query.assert_not_called();a.runtime.close.assert_not_called()
    def test_return_teleport_uses_retained_schema_with_fresh_pawn(self):
        a=self.owner();a.state='layers';a.layer_states={};a.position=(1.,2.,3.);a.yaw=4.;a.token='token'
        planner=MagicMock();planner.prepare.return_value.invoke.return_value.__enter__.return_value=SimpleNamespace(return_value=True)
        construction=MagicMock();construction.movement_planner.return_value.__enter__.return_value=planner
        a.scope=SimpleNamespace(pid=1,_session=SimpleNamespace(_story_construction_resources=construction))
        catalog=Mock();catalog.by_index={4:object()};catalog.with_observations.return_value=catalog
        query=Mock();query.query.side_effect=ReadinessPending('still streaming')
        with patch('expedition33.story_arrival.context',return_value=a.ctx),patch('expedition33.story_arrival.capture_selected',return_value=catalog) as selected,patch('expedition33.story_arrival.capture_matching') as scan,patch('expedition33.story_arrival.MapRuntime'),patch('expedition33.story_arrival.NativeMapReadiness',return_value=query):
            self.assertFalse(a.advance())
        selected.assert_called_once_with(1,((4,5,6),));scan.assert_not_called()
        construction.catalog.assert_called_once_with(a.scope,('K2_TeleportTo',))
        construction.movement_planner.assert_called_once_with(a.scope,catalog)
        planner.prepare.return_value.invoke.assert_called_once_with()
