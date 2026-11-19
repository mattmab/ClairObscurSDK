"""Pre/post world proofs share the actor preparation's fresh property reads."""
from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace as N
from unittest import TestCase
from unittest.mock import Mock,patch

from expedition33.catalog import Catalog,CatalogObject,ClassRelation
from expedition33.cinematics.blueprint_actor import BlueprintActor,QA_WORLD
from expedition33.values import StoredValues


class PreparationBatchTests(TestCase):
    def setUp(self):
        kinds=(('Object',-1),('Class',0),('Package',0),('World',0),('LocalPlayer',0),
               ('PlayerController',12),('Pawn',7),('Actor',0),('Function',0),('GameplayStatics',0),
               ('BP_Cine_FacelessBoy_C',7),('CharacterMovementComponent',0),('Controller',7))
        classes=[ClassRelation(i,1,name,parent,4096) for i,(name,parent) in enumerate(kinds)]
        def obj(i,name,cls,outer=-1,flags=0):
            return CatalogObject(123,i,1,0x10000+i*256,name,kinds[cls][0],'Class',cls,outer,1 if outer>=0 else 0,flags,0)
        objects=[obj(i,name,1,18 if i in (0,1,2,8) else 17) for i,(name,_) in enumerate(kinds)]
        objects.extend((obj(17,'/Script/Engine',2),obj(18,'/Script/CoreUObject',2),
            obj(19,'/Game/QA/Map_BattleTesting',2),obj(20,'Map_BattleTesting',3,19),
            obj(21,'PC',5,20),obj(22,'Pawn',6,20),obj(23,'Local',4),
            obj(24,'Owned',10,20),obj(25,'Default__GameplayStatics',9,17,0x10)))
        functions=(('BeginDeferredActorSpawnFromClass',9),('FinishSpawningActor',9),('K2_DestroyActor',7),
                   ('K2_GetPawn',12),('SetActorEnableCollision',7),('SetActorTickEnabled',7),
                   ('SetActorHiddenInGame',7),('SetMovementMode',11))
        objects.extend(obj(i,name,8,outer) for i,(name,outer) in enumerate(functions,30))
        self.catalog=Catalog(123,objects,classes)
        self.world,self.pc,self.pawn,self.local,self.result=(self.catalog.by_index[i] for i in range(20,25))
        self.ctx={'world_path':QA_WORLD,'world':(123,*self.ident(self.world)),'controller':(123,*self.ident(self.pc))}
        self.rows={23:StoredValues(self.local,{(4,'PlayerController'):self.pc},{},{(4,'PlayerController'):'ObjectProperty'}),
                   21:StoredValues(self.pc,{(12,'Pawn'):self.pawn},{},{(12,'Pawn'):'ObjectProperty'})}
        self.anchor=N(identity=self.ident(self.local),_held=N(active=True,object=self.local),scope=N(_check=Mock()))
        self.prepared=N(anchor=self.anchor,context=Mock(return_value=self.ctx),
            resources=N(load=Mock(return_value=self.catalog.by_index[10])),
            observe=Mock(return_value=(self.catalog,self.rows)))
        transport=N(_executable='unused',timeline_current_world_protocol=1,story_blueprint_characters_protocol=1)
        self.scope=N(pid=123,_check=Mock(),_parent=lambda:object(),_world_binding_token=(self.ctx['world'],),
                     _session=N(_transport=transport,_story_construction_resources=self.prepared))
        self.actor=object.__new__(BlueprintActor);self.actor.scope=self.scope;self.actor.state='new';self.actor.profile=None
        self.actor.prepared_actor=None;self.actor.owner=N(actor_identity=self.ident(self.result),spawn_timeline_prepared=Mock())
        self.pose=(0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.)
    @staticmethod
    def ident(obj):return obj.index,obj.serial,obj.address
    def run_prepare(self,post=None):
        with (patch('expedition33.cinematics.blueprint_actor.shared_operation',return_value=nullcontext()),
                patch('expedition33.cinematics.blueprint_actor.capture_selected_values',return_value=post or (self.catalog,self.rows)) as read,
                patch('expedition33.cinematics.blueprint_actor.capture_selected',side_effect=AssertionError('Redundant selected read')),
                patch('expedition33.cinematics.blueprint_actor.read_values_with_references',side_effect=AssertionError('Redundant Pawn read'))):
            result=self.actor.prepare('faceless-boy',self.pose)
        return result,read
    def test_one_initial_context_one_combined_pre_and_one_combined_post(self):
        result,read=self.run_prepare()
        self.assertEqual(result,self.ident(self.result));self.assertEqual(self.actor.state,'prepared')
        self.assertIs(self.actor.prepared_actor,self.result)
        self.prepared.context.assert_called_once_with(self.scope)
        self.prepared.observe.assert_called_once()
        self.assertEqual(self.prepared.observe.call_args.kwargs,{'fields':('PlayerController','Pawn')})
        self.actor.owner.spawn_timeline_prepared.assert_called_once()
        ids=self.actor.owner.spawn_timeline_prepared.call_args.args[0]
        self.assertEqual(ids[:3],[self.pc,self.pawn,self.world])
        self.assertEqual(len(ids),13)
        read.assert_called_once_with(123,(self.ident(self.local),self.ident(self.pc),self.ident(self.world),self.ident(self.result)),
                                    fields=('PlayerController',),references=True)
    def test_changed_current_controller_before_spawn_is_rejected(self):
        self.rows[23].values[4,'PlayerController']=None
        with self.assertRaisesRegex(RuntimeError,'Controller changed'):self.run_prepare()
        self.actor.owner.spawn_timeline_prepared.assert_not_called()
        self.assertEqual(self.actor.state,'failed');self.assertIsNone(self.actor.prepared_actor)
    def test_incomplete_pawn_and_foreign_world_fail_before_native_dispatch(self):
        for mode in ('error','truncated','missing','foreign_world','wrong_owner'):
            with self.subTest(mode=mode):
                self.setUp();key=(12,'Pawn');row=self.rows[21]
                if mode=='error':row.errors[key]='changed'
                elif mode=='truncated':self.rows[21]=replace(row,truncated=frozenset((key,)))
                elif mode=='missing':row.values.pop(key)
                elif mode=='wrong_owner':
                    row.values[4,'Pawn']=row.values.pop(key);row.types[4,'Pawn']=row.types.pop(key)
                else:row.values[key]=self.local
                with self.assertRaises(RuntimeError):self.run_prepare()
                self.actor.owner.spawn_timeline_prepared.assert_not_called()
    def test_retired_scope_or_anchor_does_not_spawn(self):
        for mode in ('world','anchor','lease'):
            with self.subTest(mode=mode):
                self.setUp()
                if mode=='world':self.scope._world_binding_token=((123,99,1,0x10000),)
                elif mode=='anchor':self.anchor.scope._check.side_effect=RuntimeError('Closed anchor')
                else:self.anchor._held.active=False
                with self.assertRaises(RuntimeError):self.run_prepare()
                self.actor.owner.spawn_timeline_prepared.assert_not_called()
    def test_post_spawn_context_change_retains_failed_owner_and_never_replays(self):
        rows=dict(self.rows)
        rows[23]=replace(rows[23],values={(4,'PlayerController'):None})
        with self.assertRaisesRegex(RuntimeError,'Controller changed'):self.run_prepare((self.catalog,rows))
        self.assertEqual(self.actor.state,'failed');self.assertIsNone(self.actor.prepared_actor)
        self.actor.owner.spawn_timeline_prepared.assert_called_once()
        with self.assertRaisesRegex(RuntimeError,'never replayed'):self.actor.prepare('faceless-boy',self.pose)
        self.actor.owner.spawn_timeline_prepared.assert_called_once()
    def test_wrong_result_class_or_world_is_rejected_after_spawn(self):
        for mode in ('class','world'):
            with self.subTest(mode=mode):
                self.setUp()
                wrong=replace(self.result,class_index=7,class_name='Actor') if mode=='class' else replace(self.result,outer_index=-1,outer_serial=0)
                catalog=Catalog(123,[wrong if o.index==24 else o for o in self.catalog.objects],tuple(self.catalog.classes.values()))
                with self.assertRaisesRegex(RuntimeError,'Constructed actor'):self.run_prepare((catalog,self.rows))
                self.actor.owner.spawn_timeline_prepared.assert_called_once()
                self.assertIsNone(self.actor.prepared_actor)
    def test_unknown_native_spawn_does_not_attempt_post_read_or_replay(self):
        self.actor.owner.spawn_timeline_prepared.side_effect=RuntimeError('Acknowledgement lost')
        with self.assertRaisesRegex(RuntimeError,'Acknowledgement lost'):self.run_prepare()
        self.assertEqual(self.actor.state,'failed');self.assertIsNone(self.actor.prepared_actor)
        with self.assertRaisesRegex(RuntimeError,'never replayed'):self.actor.prepare('faceless-boy',self.pose)
        self.actor.owner.spawn_timeline_prepared.assert_called_once()
