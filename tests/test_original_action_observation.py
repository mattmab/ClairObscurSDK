from dataclasses import FrozenInstanceError
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import unittest

from expedition33 import _original_action_observation as m
from expedition33.values import StoredArray, StoredValues


class OriginalActionObservationTests(unittest.TestCase):
    def setUp(self):
        self.root_path = next(path for path in m.ROOTS if 'BossSimon' in path)
        def obj(index, name, cls, outer=-1):
            return N(pid=123,index=index,serial=1,address=0x10000+index*256,
                name=name,class_name=cls,class_index=index+20,outer_index=outer,outer_serial=1)
        self.world=obj(1,'World','World')
        self.executor=obj(2,'Executor','BP_GameActionExecutorComponent_C',10)
        self.cinematic=obj(3,'Cinematic','BP_CinematicSystem_C',10)
        self.root=obj(4,self.root_path,'BP_GameAction_Sequential_C')
        self.instance=obj(5,'Instance','BP_GameActionInstance_Sequential_C',2)
        self.player=obj(6,'Player','MovieSceneSequencePlayer',3)
        self.sequence=obj(7,'Sequence','LevelSequence')
        self.controller=obj(8,'Controller','PlayerController')
        self.context=dict(controller=m.identity(self.controller),world=m.identity(self.world),world_path='/Game/Exact.World')
        objects=(self.world,self.executor,self.cinematic,self.root,self.instance,self.player,self.sequence,self.controller)
        self.catalog=N(by_index={o.index:o for o in objects})
        self.catalog.by_index[self.instance.class_index]=N(name='SequentialClass')
        self.catalog.by_index[self.executor.class_index]=N(name=m.EXECUTOR)
        self.catalog.by_index[self.cinematic.class_index]=N(name=m.CINEMATIC)
        self.catalog.path_name=lambda o: self.root_path if o is self.root else o.name
        self.catalog.outer_chain=lambda o:(self.world,)
        self.scope=N(pid=123,_check=Mock(),_session=N(_transport=N(_executable='probe')))
        self.fields={2:dict(GameActionInstancesInExecution=StoredArray((),0)),
            3:dict(LevelSequencePlayer=None,LoadCinematicAssetRequest=None),
            5:dict(GameAction=self.root,GameActionSequential=self.root,NextIndex=2,ShouldTriggerAutoSave=False,
                PlayerController=self.controller,ChildGameActionInstance=None),
            6:dict(Sequence=self.sequence,Status=1)}
        self.kinds=dict(GameActionInstancesInExecution='ArrayProperty',LevelSequencePlayer='ObjectProperty',
            LoadCinematicAssetRequest='ObjectProperty',GameActionSequential='ObjectProperty',NextIndex='IntProperty',
            ShouldTriggerAutoSave='BoolProperty',PlayerController='ObjectProperty',Sequence='ObjectProperty',Status='ByteProperty',
            GameAction='ObjectProperty',ChildGameActionInstance='ObjectProperty')
        def read(catalog,obj,*,fields):
            values={(obj.index,key):self.fields[obj.index][key] for key in fields}
            types={(obj.index,key):self.kinds[key] for key in fields}
            return StoredValues(obj,values,{},types),catalog
        self.enterContext(patch.object(m,'ReadBatch'))
        self.context_read=self.enterContext(patch.object(m,'controller_context',return_value=self.context))
        self.capture=self.enterContext(patch.object(m,'capture_selected',return_value=self.catalog))
        self.read=self.enterContext(patch.object(m,'read_values_with_references',side_effect=read))
        self.monitor=m.OriginalActionMonitor(self.scope,executor=self.executor,cinematic_system=self.cinematic,
            root=self.root,root_path=self.root_path,context=self.context)

    def test_idle_is_copied_observation_not_success(self):
        snapshot=self.monitor.observe()
        self.assertTrue(snapshot.idle)
        self.assertFalse(hasattr(snapshot,'completed'))
        self.assertFalse(hasattr(snapshot,'victory'))
        self.capture.assert_called_once_with(123,tuple(m.identity(o)[1:] for o in (self.executor,self.cinematic,self.root)))
        with self.assertRaises(FrozenInstanceError):snapshot.root='Other'
        self.assertEqual(self.context_read.call_count,2)

    def test_sequential_callback_progress_is_observed_without_advancing(self):
        self.fields[2]['GameActionInstancesInExecution']=StoredArray((self.instance,),1)
        snapshot=self.monitor.observe()
        self.assertFalse(snapshot.idle)
        self.assertEqual(snapshot.instances[0].next_index,2)
        self.assertEqual(snapshot.instances[0].sequential_action,self.root_path)
        self.assertFalse(snapshot.instances[0].autosave)
        self.fields[5]['NextIndex']=3
        self.assertEqual(snapshot.instances[0].next_index,2)

    def test_sequence_identity_is_observed_not_visibility_claim(self):
        self.fields[3]['LevelSequencePlayer']=self.player
        snapshot=self.monitor.observe()
        self.assertFalse(snapshot.idle)
        self.assertEqual(snapshot.sequence_path,'Sequence')
        self.assertEqual(snapshot.sequence_player,m.identity(self.player))
        self.assertEqual(snapshot.sequence_status,1)
        self.assertFalse(hasattr(snapshot,'visible'))

    def test_cinematic_monitor_uses_same_world_bracketing_with_exact_profile_admission(self):
        from expedition33.cinematics.original_game_action import profiles
        profile=next(iter(profiles().values()))
        self.root_path=profile['action_path']
        prepared=N(executor=self.executor,component=self.cinematic,asset=self.root,context=self.context)
        monitor=m.CinematicActionMonitor(self.scope,prepared=prepared,profile=profile)
        self.fields[2]['GameActionInstancesInExecution']=StoredArray((self.instance,),1)
        snapshot=monitor.observe()
        self.assertEqual(snapshot.instances[0].action_identity,m.identity(self.root))
        self.assertEqual(snapshot.root,profile['action_path'])
        with self.assertRaisesRegex(ValueError,'reviewed original cinematic'):
            m.CinematicActionMonitor(self.scope,prepared=prepared,profile=dict(profile,action_path='/Game/Other.Other'))
        self.context_read.return_value=dict(self.context,world=(123,100,2,0x99999))
        with self.assertRaisesRegex(RuntimeError,'replaced'):monitor.observe()

    def test_exact_nested_action_path_and_outer_are_observed(self):
        self.fields[2]['GameActionInstancesInExecution']=StoredArray((self.instance,),1)
        self.fields[5]['ChildGameActionInstance']=self.player
        self.player.outer_index=self.instance.index
        self.fields[6]['GameAction']=self.sequence
        self.catalog.by_index[self.player.class_index]=N(name='CinematicActionInstanceClass')
        snapshot=self.monitor.observe()
        self.assertEqual(snapshot.instances[1].action_path,'Sequence')
        self.assertEqual(snapshot.instances[1].parent,m.identity(self.instance))
        self.player.outer_index=100
        with self.assertRaisesRegex(RuntimeError,'outer differs'):self.monitor.observe()

    def test_pending_cinematic_load_is_not_idle(self):
        self.fields[3]['LoadCinematicAssetRequest']=self.player
        self.assertFalse(self.monitor.observe().idle)

    def test_world_replacement_is_terminal_before_old_identity_reads(self):
        self.context_read.return_value=dict(self.context,world=(123,100,2,0x99999))
        with self.assertRaisesRegex(RuntimeError,'replaced'):self.monitor.observe()
        self.capture.assert_not_called()
        self.context_read.return_value=self.context
        with self.assertRaisesRegex(RuntimeError,'world was replaced'):self.monitor.observe()

    def test_mid_read_context_change_discards_snapshot(self):
        self.context_read.side_effect=[self.context,dict(self.context,controller=(123,80,2,0x99999))]
        with self.assertRaisesRegex(RuntimeError,'discard snapshot'):self.monitor.observe()
        self.assertTrue(self.monitor.world_changed)

    def test_closed_scope_and_closed_monitor_do_not_read(self):
        self.scope._check.side_effect=RuntimeError('scope closed')
        with self.assertRaisesRegex(RuntimeError,'scope closed'):self.monitor.observe()
        self.capture.assert_not_called()
        self.scope._check.side_effect=None
        self.monitor.close();self.monitor.close()
        with self.assertRaisesRegex(RuntimeError,'closed'):self.monitor.observe()
        self.capture.assert_not_called()

    def test_incomplete_null_duplicate_and_overlarge_arrays_reject(self):
        for array in (StoredArray((),1),StoredArray((None,),1),StoredArray((self.instance,self.instance),2),
                      StoredArray(tuple(self.instance for _ in range(65)),65)):
            self.fields[2]['GameActionInstancesInExecution']=array
            with self.assertRaises(RuntimeError):self.monitor.observe()

    def test_foreign_service_owner_world_or_sequential_controller_reject(self):
        self.cinematic.outer_index=99
        with self.assertRaisesRegex(RuntimeError,'different owners'):self.monitor.observe()
        self.cinematic.outer_index=10
        self.catalog.outer_chain=lambda o:()
        with self.assertRaisesRegex(RuntimeError,'another world'):self.monitor.observe()
        self.catalog.outer_chain=lambda o:(self.world,)
        self.fields[2]['GameActionInstancesInExecution']=StoredArray((self.instance,),1)
        self.fields[5]['PlayerController']=None
        with self.assertRaisesRegex(RuntimeError,'controller differs'):self.monitor.observe()

    def test_wrong_root_and_unreadable_fields_are_not_reclassified_as_idle(self):
        self.catalog.path_name=lambda o:'Other'
        with self.assertRaisesRegex(RuntimeError,'root identity'):self.monitor.observe()
        self.catalog.path_name=lambda o:self.root_path if o is self.root else o.name
        self.kinds['GameActionInstancesInExecution']='ObjectProperty'
        with self.assertRaisesRegex(RuntimeError,'field type'):self.monitor.observe()
