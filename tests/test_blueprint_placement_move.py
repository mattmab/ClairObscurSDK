import unittest
from contextlib import contextmanager,nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.blueprint_actor import BlueprintActor

class PlacementMoveTests(unittest.TestCase):
    def test_process_selectors_avoid_rescan_but_recapture_current_actor(self):
        obj=N(class_name='BP_Cine_FacelessBoy_C')
        catalog=N(by_index={1:obj},with_observations=lambda other:catalog,find_path=lambda path:path)
        planner=N(prepare=Mock(return_value=N(invoke=lambda:nullcontext(N(return_value=True)))),close=Mock())
        resources=N(catalog=Mock(return_value=catalog),movement_planner=Mock(return_value=planner))
        scope=N(pid=1,_check=Mock(),_session=N(_transport=N(_executable='probe'),_story_construction_resources=resources),
            invocation_planner=Mock(return_value=planner))
        actor=object.__new__(BlueprintActor);actor.scope=scope;actor.owner=N(actor_identity=(1,2,3));actor.state='visible';actor.profile='faceless-boy'
        with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),\
                patch('expedition33.cinematics.blueprint_actor.capture_matching') as scan,\
                patch('expedition33.cinematics.blueprint_actor.capture_selected',return_value=catalog) as selected:
            actor.move([1.,2.,3.],45.)
            scan.assert_not_called();selected.assert_called_once_with(1,((1,2,3),))
        resources.catalog.assert_called_once();planner.prepare.assert_called_once()
        resources.movement_planner.assert_called_once_with(scope,catalog)
        scope.invocation_planner.assert_not_called()
        self.assertEqual(actor.state,'visible')

    def test_stationary_root_and_collision_restore_even_when_teleport_rejects(self):
        for accepted in (True,False):
            with self.subTest(accepted=accepted):
                events=[];obj=N(class_name='BP_Cine_FacelessBoy_C');root=object()
                catalog=N(by_index={1:obj},with_observations=lambda other:catalog,find_path=lambda path:path)
                @contextmanager
                def invoke(path,args):
                    events.append((path.rsplit(':',1)[1],args))
                    yield N(return_value=accepted)
                planner=N(prepare=lambda target,path,**args:N(invoke=lambda:invoke(path,args)),close=Mock())
                scope=N(pid=1,_check=lambda:None,_session=N(_transport=N(_executable='probe')),invocation_planner=lambda **kw:planner)
                actor=object.__new__(BlueprintActor);actor.scope=scope;actor.owner=N(actor_identity=(1,2,3));actor.state='visible';actor.profile='faceless-boy'
                observations=[(N(errors={},values={(1,'bActorEnableCollision'):True,(1,'RootComponent'):root}),catalog),
                    (N(errors={},values={(2,'Mobility'):1}),catalog)]
                with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),\
                        patch('expedition33.cinematics.blueprint_actor.capture_matching',return_value=catalog),\
                        patch('expedition33.cinematics.blueprint_actor.capture_selected',return_value=catalog),\
                        patch('expedition33.cinematics.blueprint_actor.read_values_with_references',side_effect=observations):
                    if accepted:actor.move([1.,2.,3.],45.,placement=True)
                    else:
                        with self.assertRaisesRegex(RuntimeError,'placement was rejected'):actor.move([1.,2.,3.],45.,placement=True)
                self.assertEqual([name for name,_ in events],['SetActorEnableCollision','SetMobility','K2_TeleportTo','SetMobility','SetActorEnableCollision'])
                self.assertEqual(events[0][1],dict(bNewActorEnableCollision=False))
                self.assertEqual(events[1][1],dict(NewMobility=2))
                self.assertEqual(events[3][1],dict(NewMobility=1))
                self.assertEqual(events[4][1],dict(bNewActorEnableCollision=True))
                self.assertEqual(actor.state,'visible' if accepted else 'failed');planner.close.assert_called_once()
