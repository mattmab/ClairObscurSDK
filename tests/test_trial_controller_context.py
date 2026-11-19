"""Trial preparation retains a selector, never current-world permission."""
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock, patch

from expedition33._original_trigger_fight import OriginalTriggerFight
from expedition33 import _owned_arena_camera as camera


class TrialControllerContextTests(unittest.TestCase):
    def fight(self):
        fight=OriginalTriggerFight.__new__(OriginalTriggerFight)
        fight._scope=N();fight._batch=Mock(side_effect=nullcontext)
        fight._context_reader=None
        return fight

    def test_selector_is_prepared_once_but_each_context_is_fresh(self):
        fight=self.fight();reader=Mock(side_effect=({'world':1},{'world':2}))
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=reader) as select:
            self.assertNotEqual(fight._current_context(),fight._current_context())
        select.assert_called_once_with(fight._scope)
        self.assertEqual(reader.call_count,2);self.assertEqual(fight._batch.call_count,2)

    def test_failed_current_read_does_not_reacquire_or_fall_back(self):
        fight=self.fight();reader=Mock(side_effect=RuntimeError('selected read failed'))
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=reader) as select,\
             patch('expedition33.cinematics.original_game_action.controller_context') as legacy:
            for _ in range(2):
                with self.assertRaisesRegex(RuntimeError,'selected read failed'):fight._current_context()
        select.assert_called_once_with(fight._scope);legacy.assert_not_called()
        self.assertEqual(reader.call_count,2)

    def test_battle_context_change_is_rejected_before_manager_read(self):
        fight=self.fight();fight._context={'world':1}
        with patch('expedition33.cinematics.controller_anchor.context_observer',return_value=lambda:{'world':2}),\
             patch('expedition33.catalog.capture_selected') as capture:
            with self.assertRaisesRegex(RuntimeError,'world/controller changed'):fight._battle_snapshot()
        capture.assert_not_called()


class ArenaCameraContextTests(unittest.TestCase):
    def setUp(self):
        def obj(index,kind,path=None,outer=None):
            return N(index=index,serial=index+1,address=index*256,class_index=kind,
                     path=path,outer_index=outer.index if outer else None,
                     outer_serial=outer.serial if outer else None)
        self.actor=obj(10,100)
        self.context=dict(controller=(123,1,2,256),world=(123,2,3,512),world_path='/Game/QA.Map')
        self.reader=Mock(return_value=self.context)
        self.actor_values=dict(bHidden=True,bActorEnableCollision=False)
        objects={1:obj(1,101),10:self.actor,
                 100:obj(100,0,camera.ARENA),101:obj(101,0,'/Script/Engine.PlayerController'),
                 102:obj(102,0,'/Script/Engine.SceneComponent'),
                 103:obj(103,0,'/Script/Engine.ChildActorComponent'),
                 104:obj(104,0,camera.CAMERA)}
        self.fields={};self.getters=[]
        for i,(point,child) in enumerate(camera.PAIRS):
            p=obj(20+i,102,outer=self.actor);c=obj(30+i,103,outer=self.actor)
            target=obj(40+i,104)
            objects.update({o.index:o for o in (p,c,target)})
            self.actor_values.update({point:p,child:c})
            self.fields[c.index]=dict(ChildActor=target,ChildActorClass=objects[104])
            self.fields[target.index]=dict(CameraFocusPoint=dict(X=float(i),Y=2.,Z=3.))
            query=Mock();query.invoke.side_effect=lambda i=i:nullcontext(N(
                outcome='dispatch_returned',return_value=dict(X=float(i),Y=2.,Z=3.)))
            self.getters.append(query)
        self.fields[self.actor.index]=self.actor_values
        self.manager=obj(50,105)
        self.fields[50]=dict(IsBattleInitialized=False,HasBattleStartedEndFlow=False,
                             Enemies=N(length=0),BattleMapBP=None)
        self.catalog=N(by_index=objects,path_name=lambda o:o.path,ancestors=lambda i:(i,))
        self.catalog.with_observations=lambda _:self.catalog
        self.call=Mock();self.call.invoke.side_effect=lambda:nullcontext(N(outcome='dispatch_returned'))
        self.planner=N(prepare_blueprint=Mock(return_value=self.call),
                       prepare=Mock(side_effect=self.getters),close=Mock(),adopt_observations=Mock())
        self.scope=N(pid=123,_session=N(),invocation_planner=Mock(return_value=self.planner))
        self.owner=N(_scope=self.scope,_transport=N(_executable='candidate-reader'),
                     actor_identity=(10,11,2560),_camera_focus_attempted=False,_component_uncertain=False)
        def read(c,obj,names):
            return {name:self.fields[obj.index][name] for name in names},c
        self.enterContext(patch.object(camera,'ReadBatch',side_effect=lambda *a,**kw:nullcontext()))
        self.shared=self.enterContext(patch.object(camera,'shared_operation',side_effect=lambda *a,**kw:nullcontext()))
        self.enterContext(patch.object(camera,'active_reader',return_value=None))
        self.selector=self.enterContext(patch.object(camera,'context_observer',return_value=self.reader))
        self.capture=self.enterContext(patch.object(camera,'capture_selected',return_value=self.catalog))
        self.enterContext(patch.object(camera,'capture_matching',return_value=self.catalog))
        self.enterContext(patch.object(camera,'_controller_battle_manager',return_value=(self.manager,self.catalog)))
        self.enterContext(patch.object(camera,'_read',side_effect=read))
        def read_many(c,objects,*,fields):
            result={o.index:N(values={(i,name):self.fields[o.index][name] for i,name in enumerate(fields)},
                              errors={},truncated=False) for o in objects}
            return result,c
        self.many=self.enterContext(patch.object(camera,'read_values_many_with_references',side_effect=read_many))
        self.enterContext(patch.object(camera,'_exact',side_effect=lambda c,p:obj(60,106,p)))

    def test_all_idle_guards_remain_fresh_and_original_update_is_verified(self):
        report=camera.refresh_camera_focus(self.owner)
        self.shared.assert_called_once_with(123,_executable='candidate-reader')
        self.selector.assert_called_once_with(self.scope)
        self.assertEqual(self.reader.call_count,8)  # initial plus seven idle guards
        self.call.invoke.assert_called_once_with()
        self.assertTrue(report['verified']);self.assertTrue(self.owner._camera_focus_attempted)
        self.assertFalse(self.owner._component_uncertain);self.planner.close.assert_called_once()
        self.assertEqual(self.many.call_count,3)  # child joins twice and final focus readback

    def test_warm_metadata_is_freshly_selected_and_adopted_without_global_discovery(self):
        held=[N(active=True,object=N(index=60+i,serial=70+i,address=0x5000+i*256)) for i in range(3)]
        observations=object();resources=N(scope=N(_session=self.scope._session,_check=Mock()),
            _owned_arena_camera_inputs=dict(ready=True,objects=held,observations=observations))
        with patch.object(camera,'capture_matching',side_effect=AssertionError('global discovery')):
            self.assertTrue(camera.refresh_camera_focus(self.owner,resources=resources)['verified'])
        self.scope.invocation_planner.assert_called_once_with(observations=observations,selected_results=True)
        self.planner.adopt_observations.assert_called_once_with(self.catalog)
        self.assertIn(unittest.mock.call(123,((10,11,2560),*((h.object.index,h.object.serial,h.object.address) for h in held))),self.capture.call_args_list)
        self.assertEqual(self.reader.call_count,8)

    def test_foreign_or_expired_warm_resources_cannot_dispatch(self):
        resources=N(scope=N(_session=object(),_check=Mock()))
        with self.assertRaisesRegex(RuntimeError,'another session'):
            camera.refresh_camera_focus(self.owner,resources=resources)
        self.reader.assert_not_called();self.call.invoke.assert_not_called()
        resources.scope._session=self.scope._session
        resources._owned_arena_camera_inputs=dict(ready=True,objects=[N(active=False)])
        with self.assertRaisesRegex(RuntimeError,'lease expired'):
            camera.refresh_camera_focus(self.owner,resources=resources)
        self.call.invoke.assert_not_called()

    def test_incomplete_child_batch_blocks_native_update(self):
        self.many.side_effect=lambda c,objects,**kw:({},c)
        with self.assertRaisesRegex(RuntimeError,'Incomplete owned camera batch'):camera.refresh_camera_focus(self.owner)
        self.call.invoke.assert_not_called();self.assertFalse(self.owner._camera_focus_attempted)

    def test_incomplete_focus_after_ack_retains_uncertain_owner(self):
        read=self.many.side_effect
        def truncated(c,objects,*,fields):
            values,c=read(c,objects,fields=fields)
            if fields==('CameraFocusPoint',):next(iter(values.values())).truncated=True
            return values,c
        self.many.side_effect=truncated
        with self.assertRaisesRegex(RuntimeError,'Incomplete owned camera fields'):camera.refresh_camera_focus(self.owner)
        self.call.invoke.assert_called_once_with();self.assertTrue(self.owner._component_uncertain)
        self.assertTrue(self.owner._camera_focus_attempted);self.planner.close.assert_called_once()

    def test_changed_child_after_update_is_rejected(self):
        read=self.many.side_effect
        def replace(c,objects,*,fields):
            values,c=read(c,objects,fields=fields)
            if self.many.call_count==2:
                old=self.fields[30]['ChildActor']
                values[30].values[(0,'ChildActor')]=N(index=old.index,serial=999,address=old.address,class_index=old.class_index)
            return values,c
        self.many.side_effect=replace
        with self.assertRaisesRegex(RuntimeError,'replaced during update'):camera.refresh_camera_focus(self.owner)
        self.assertTrue(self.owner._component_uncertain);self.call.invoke.assert_called_once()

    def test_changed_controller_before_update_prevents_dispatch_and_closes_planner(self):
        self.reader.side_effect=[self.context]*6+[dict(self.context,controller=(123,8,9,2048))]
        with self.assertRaisesRegex(RuntimeError,'Travel during'):camera.refresh_camera_focus(self.owner)
        self.call.invoke.assert_not_called();self.planner.close.assert_called_once()
        self.assertFalse(self.owner._camera_focus_attempted);self.assertFalse(self.owner._component_uncertain)

    def test_changed_world_after_ack_keeps_uncertain_cleanup_journal(self):
        self.reader.side_effect=[self.context]*7+[dict(self.context,world=(123,8,9,2048))]
        with self.assertRaisesRegex(RuntimeError,'Travel during'):camera.refresh_camera_focus(self.owner)
        self.call.invoke.assert_called_once_with();self.planner.close.assert_called_once()
        self.assertTrue(self.owner._camera_focus_attempted);self.assertTrue(self.owner._component_uncertain)
        self.assertEqual(self.owner.camera_focus['phase'],'dispatch_returned')
        self.assertFalse(self.owner.camera_focus['verified'])

    def test_context_read_failure_does_not_dispatch_or_fall_back(self):
        self.reader.side_effect=[self.context,RuntimeError('read unavailable')]
        with patch('expedition33.cinematics.original_game_action.controller_context') as scan:
            with self.assertRaisesRegex(RuntimeError,'read unavailable'):camera.refresh_camera_focus(self.owner)
        scan.assert_not_called();self.call.invoke.assert_not_called()
        self.assertFalse(self.owner._camera_focus_attempted)

    def test_native_update_missing_ack_keeps_attempted_journal(self):
        self.call.invoke.side_effect=RuntimeError('ACK lost')
        with self.assertRaisesRegex(RuntimeError,'ACK lost'):camera.refresh_camera_focus(self.owner)
        self.assertEqual(self.reader.call_count,7)
        self.assertEqual(self.owner.camera_focus['phase'],'dispatch_intent')
        self.assertTrue(self.owner._component_uncertain);self.assertTrue(self.owner._camera_focus_attempted)
        self.planner.close.assert_called_once()

    def test_active_battle_blocks_camera_update(self):
        self.fields[50]['IsBattleInitialized']=True
        with self.assertRaisesRegex(RuntimeError,'Preserve active battle'):camera.refresh_camera_focus(self.owner)
        self.call.invoke.assert_not_called();self.assertFalse(self.owner._camera_focus_attempted)


if __name__=='__main__':unittest.main()
