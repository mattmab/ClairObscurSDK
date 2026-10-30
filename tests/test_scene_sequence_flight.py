import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_runtime_scene_editor import package
from scene_editor_tests.sequence_viewport import call,fly,place_at_view,overview

class SequenceFlightViewTests(unittest.TestCase):
    def test_identity_observation_does_not_retain_a_new_lease(self):
        target=N(index=1,serial=2,address=3)
        observed=N(index=4,serial=5,address=6)
        catalog=Mock();catalog.with_observations.return_value=catalog
        planner=Mock();planner.prepare.return_value.invoke.return_value=nullcontext(N(return_value=observed))
        scope=N(pid=1,invocation_planner=Mock(return_value=planner),retain=Mock())
        with patch('scene_editor_tests.sequence_viewport.capture_matching',return_value=catalog), \
             patch('scene_editor_tests.sequence_viewport.capture_selected',return_value=object()):
            self.assertEqual(call(N(play_scope=scope),target,'ActorComponent','GetOwner',_identity_only=True),(4,5,6))
        scope.retain.assert_not_called()
    def viewport(self):
        component=N(index=11,serial=12,address=13)
        actor=N(index=21,serial=22,address=23,class_name='CineCameraActor')
        p=N(sequence=N(player=object(),pause=Mock()),playing=True,flight=None,
            scope=N(pid=1,_session=N(_transport=N(rotator_values_protocol=1))),
            document={'source':{}},scene_anchor=(0.,0.,0.),menu=N(view=N(picker=False)))
        def dispatch(preview,target,owner,name,**kwargs):
            if name=='GetActiveCameraComponent':return (11,12,13) if kwargs.get('_identity_only') else component
            if name=='GetOwner':return (21,22,23) if kwargs.get('_identity_only') else actor
            if name=='K2_TeleportTo':return True
        return p,component,actor,Mock(side_effect=dispatch)

    def test_failed_camera_read_does_not_publish_partial_overview(self):
        p,component,actor,dispatch=self.viewport()
        bad=N(errors={'PostProcessBlendWeight':'missing'},truncated=False,values={})
        with patch('scene_editor_tests.sequence_viewport.call',dispatch), \
             patch('expedition33.cinematics.authored_cast.bindings',return_value=[{'kind':'spawnable','template':{'class':'CineCameraActor'}}]), \
             patch('expedition33.values.capture_selected_values',return_value=(None,{11:bad})):
            with self.assertRaisesRegex(ValueError,'settings'):overview(p,'overview')
        self.assertFalse(hasattr(p,'overview_camera'))
        self.assertNotIn('K2_TeleportTo',[c.args[3] for c in dispatch.call_args_list])

    def test_repeated_overview_keeps_original_weight_and_revalidates_identity(self):
        p,component,actor,dispatch=self.viewport()
        good=N(errors={},truncated=False,values={(0,'PostProcessBlendWeight'):.75})
        with patch('scene_editor_tests.sequence_viewport.call',dispatch), \
             patch('expedition33.cinematics.authored_cast.bindings',return_value=[{'kind':'spawnable','template':{'class':'CineCameraActor'}}]), \
             patch('expedition33.values.capture_selected_values',return_value=(None,{11:good})) as capture:
            overview(p,'overview');overview(p,'overview')
        self.assertEqual(p.overview_weight,.75)
        self.assertEqual(capture.call_count,1)
        self.assertEqual(sum(c.args[3]=='K2_TeleportTo' for c in dispatch.call_args_list),2)

    def test_changed_active_component_blocks_orbit_before_any_mutation(self):
        p,component,actor,dispatch=self.viewport()
        p.overview_camera=actor;p.overview_component=component;p.overview_weight=.75
        p.overview_yaw=180.;p.overview_distance=1800.;p.overview_height=650.
        dispatch.side_effect=lambda *args,**kwargs:(11,99,13)
        with patch('scene_editor_tests.sequence_viewport.call',dispatch):
            with self.assertRaisesRegex(ValueError,'camera changed'):overview(p,'orbit_left')
        self.assertEqual(p.overview_yaw,180.)
        self.assertEqual([c.args[3] for c in dispatch.call_args_list],['GetActiveCameraComponent'])

    def test_changed_component_owner_blocks_orbit_before_any_mutation(self):
        p,component,actor,dispatch=self.viewport()
        p.overview_camera=actor;p.overview_component=component;p.overview_weight=.75
        p.overview_yaw=180.;p.overview_distance=1800.;p.overview_height=650.
        dispatch.side_effect=lambda *args,**kwargs:(11,12,13) if args[3]=='GetActiveCameraComponent' else (21,99,23)
        with patch('scene_editor_tests.sequence_viewport.call',dispatch):
            with self.assertRaisesRegex(ValueError,'camera changed'):overview(p,'orbit_left')
        self.assertEqual(p.overview_yaw,180.)
        self.assertEqual([c.args[3] for c in dispatch.call_args_list],['GetActiveCameraComponent','GetOwner'])

    def test_missing_native_flight_does_not_move_camera(self):
        p=N(scope=N(_session=N(_transport=N(sequence_flight_protocol=0))),sequence=Mock())
        with self.assertRaisesRegex(ValueError,'does not include'):fly(p)
        p.sequence.pause.assert_not_called()
    def test_native_cancelled_flight_cannot_place_from_stale_pose(self):
        flight=N(active=True)
        def poll():
            flight.active=False
            return (1.,2.,3.,0.,0.,0.)
        flight.poll=poll
        p=N(flight=flight,editor=N(workspace=Mock()),pending=None)
        with self.assertRaisesRegex(ValueError,'ended'):place_at_view(p)
        p.editor.workspace.place_scene.assert_not_called();self.assertIsNone(p.pending)
    def test_whole_scene_placement_uses_world_view_and_queues_existing_apply(self):
        p=N(flight=N(active=True,poll=lambda:(100.,200.,300.,0.,90.,0.)),editor=N(workspace=Mock()),pending=None)
        place_at_view(p)
        target=p.editor.workspace.place_scene.call_args.args[0]
        self.assertAlmostEqual(target[0],100.);self.assertAlmostEqual(target[1],1200.);self.assertAlmostEqual(target[2],300.)
        self.assertEqual(p.pending,'apply');self.assertEqual(p.resume_flight_pose,(100.,200.,300.,0.,90.,0.))
