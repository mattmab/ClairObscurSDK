"""Placement must restore only the engine state it actually changed."""
import unittest
from contextlib import contextmanager,nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.blueprint_actor import BlueprintActor


class BlueprintPlacementTests(unittest.TestCase):
    def move(self,collision,mobility,*,reject=False):
        actor=object.__new__(BlueprintActor);actor.state='visible';actor.profile='test'
        actor.class_path='/Game/Test.Test_C';actor.owner=N(actor_identity=(1,2,0x10000))
        actor.scope=Mock(pid=123);actor.scope._session._transport._executable='unused'
        actor.scope._session._story_construction_resources=None
        obj=N(class_name='Test_C');root=N(index=2,serial=3,address=0x20000)
        catalog=Mock();catalog.by_index={1:obj};catalog.with_observations.return_value=catalog
        catalog.find_path.side_effect=lambda path:path
        values=lambda **fields:N(values={('owner',key):value for key,value in fields.items()},errors=[])
        reads=[(values(bActorEnableCollision=collision,RootComponent=root),catalog),(values(Mobility=mobility),catalog)]
        invoked=[]
        @contextmanager
        def invoke(function,arguments):
            invoked.append((function.rsplit(':',1)[-1],arguments))
            yield N(return_value=not reject)
        planner=Mock();actor.scope.invocation_planner.return_value=planner
        planner.prepare.side_effect=lambda obj,function,**args:N(invoke=lambda:invoke(function,args))
        with patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),patch('expedition33.cinematics.blueprint_actor.capture_matching',return_value=catalog),patch('expedition33.cinematics.blueprint_actor.capture_selected',return_value=catalog),patch('expedition33.cinematics.blueprint_actor.read_values_with_references',side_effect=reads):
            if reject:
                with self.assertRaisesRegex(RuntimeError,'placement was rejected'):actor.move((10,20,30),45,placement=True)
            else:actor.move((10,20,30),45,placement=True)
        planner.close.assert_called_once()
        self.assertEqual(actor.state,'failed' if reject else 'visible')
        return invoked

    def test_movable_noncolliding_carrier_needs_only_teleport(self):
        calls=self.move(False,2)
        self.assertEqual([name for name,args in calls],['K2_TeleportTo'])

    def test_real_collision_and_static_mobility_are_restored_even_after_rejection(self):
        for reject in (False,True):
            with self.subTest(reject=reject):
                calls=self.move(True,0,reject=reject)
                self.assertEqual([name for name,args in calls],['SetActorEnableCollision','SetMobility','K2_TeleportTo','SetMobility','SetActorEnableCollision'])
                self.assertEqual(calls[0][1],dict(bNewActorEnableCollision=False))
                self.assertEqual(calls[1][1],dict(NewMobility=2))
                self.assertEqual(calls[3][1],dict(NewMobility=0))
                self.assertEqual(calls[4][1],dict(bNewActorEnableCollision=True))

    def test_independent_states_are_changed_and_restored_independently(self):
        self.assertEqual([name for name,args in self.move(False,1)],['SetMobility','K2_TeleportTo','SetMobility'])
        self.assertEqual([name for name,args in self.move(True,2)],['SetActorEnableCollision','K2_TeleportTo','SetActorEnableCollision'])
