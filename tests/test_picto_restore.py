import unittest
from contextlib import nullcontext
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33 import picto_restore as module


def values(**fields):
    items={(1,k):v for k,v in fields.items()}
    return NS(types=items,values=items,errors={})


class RestoreTests(unittest.TestCase):
    def setUp(self):
        def obj(index,cls):return NS(index=index,class_name=cls,object_flags=0,name=cls,outer_index=-1)
        self.item=obj(1,'BP_ItemInstance_Gear_Pictos_C');self.char=obj(2,'BP_CharacterData_C');self.gi=obj(3,'BP_jRPG_GI_Custom_C');self.table=obj(4,'DataTable')
        self.objects=[self.item,self.char,self.gi,self.table]
        names=['ChangeLevel','SetBaseStatsMultiplier','RefreshCurrentGearStats','SetCurrentStatValue','UpdateEquipmentStats','RefreshUsedLuminaPointsInternal','Map_Remove','SetPassiveEffectSharedProgression']
        for i,name in enumerate(names):self.objects.append(NS(index=10+i,name=name,class_name='Function',object_flags=0,outer_index=100 if i<4 else 101))
        self.catalog=NS(objects=self.objects,select=lambda cls:[o for o in self.objects if getattr(o,'class_name',None)==cls],
            find_class=lambda cls:NS(index=100 if cls=='BP_ItemInstance_Gear_C' else 101),
            path_name=lambda o:'/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
        self.state={'ItemDefinitionID':'Cheater','CurrentLevel':33,'BaseStatsMultipliers':NS(items={1:.7,6:0.}), 'CurrentStats':NS(items={1:2636,6:249})}
        self.calls=[];self.cost=40
        def invoke(obj,fn,**args):
            self.calls.append(fn.name)
            if fn.name=='SetBaseStatsMultiplier':self.state['BaseStatsMultipliers'].items[args['Stat']]=args['Value']
            return NS(invoke=lambda:nullcontext())
        self.scope=NS(pid=123,_session=NS(_transport=NS(picto_startup_protocol=1)),invocation_planner=lambda **kw:NS(prepare=invoke))
        def change(scope,op,target,fn,source,panel,gi,expected,value):
            self.assertIsNone(panel);self.calls.append(op)
            if op==7:return self.cost
            if op==6:self.cost=value
            if op==4:self.state['CurrentLevel']=value
            if op==9:self.state['CurrentStats'].items[value]=0
            if op==12:self.state['CurrentStats' if expected==1 else 'BaseStatsMultipliers'].items.pop(value,None)
            return value
        self.native=change

    def run_restore(self,profiles,change=None):
        with patch('expedition33.picto_inventory.owned_pictos',return_value=(self.catalog,{'Cheater':(self.item,33)})), \
             patch.object(module,'read_values_many',side_effect=lambda c,objs,**kw:{o.index:values(**self.state) for o in objs}), \
             patch.object(module,'read_values',side_effect=lambda c,o:values(**self.state)), \
             patch.object(module,'change',side_effect=change or self.native):
            return module.restore(self.scope,profiles,catalog=self.catalog)

    def test_startup_mastery_uses_batch_only_for_mismatch(self):
        self.scope._session._transport.picto_mastery_batch_protocol=1
        self.state['SharedPassiveEffectProgression']=NS(items={})
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=NS(owned={})), \
             patch('expedition33.picto_startup_batch.run',return_value=['Cheater']) as run:
            result=self.run_restore({'Cheater':{'mastered':True}})
        self.assertEqual(run.call_args.args[1],['Cheater'])
        self.assertFalse(self.calls);self.assertEqual(result['batch_groups'],1)
        self.assertEqual(result['applied'],[['Cheater','mastered']])

    def test_matching_mastery_is_not_queued(self):
        self.scope._session._transport.picto_mastery_batch_protocol=1
        self.state['SharedPassiveEffectProgression']=NS(items={'Cheater':NS(fields={
            'IsLearnt_9_2561000E49D90653437DE9A45BE2A86D':True,
            'LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F':4})})
        with patch('expedition33.picto_startup_batch.run') as run:
            self.run_restore({'Cheater':{'mastered':True}})
        run.assert_not_called();self.assertFalse(self.calls)

    def test_batch_failure_does_not_fall_back_to_individual_mutations(self):
        self.scope._session._transport.picto_mastery_batch_protocol=1
        self.state['SharedPassiveEffectProgression']=NS(items={})
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=NS(owned={})), \
             patch('expedition33.picto_startup_batch.run',side_effect=RuntimeError('uncertain')) as run:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                self.run_restore({'Cheater':{'mastered':True}})
        run.assert_called_once();self.assertFalse(self.calls)

    def test_cost_restores_without_menu_or_stat_mutations(self):
        result=self.run_restore({'Cheater':{'cost':35}})
        self.assertEqual(self.cost,35);self.assertEqual(self.calls,[7,6]);self.assertEqual(result['applied'],[['Cheater','cost']])

    def test_ownership_restore_skips_matching_snapshot_rows(self):
        owner=NS(owned={'Cheater':(self.item,33)},catalog=self.catalog,set_owned=Mock(return_value=True))
        self.catalog.with_observations=lambda other:self.catalog
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=owner):
            result=self.run_restore({'Cheater':{'owned':True},'Missing':{'owned':False}})
        owner.set_owned.assert_not_called()
        self.assertEqual(result['applied'],[])

    def test_ownership_restore_dispatches_only_changed_membership(self):
        owner=NS(owned={'Cheater':(self.item,33)},catalog=self.catalog,set_owned=Mock(return_value=True))
        self.catalog.with_observations=lambda other:self.catalog
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=owner):
            self.run_restore({'Cheater':{'owned':False},'Missing':{'owned':False}})
        owner.set_owned.assert_called_once_with('Cheater',False)

    def test_missing_owned_item_is_reported_not_granted(self):
        result=self.run_restore({'Missing':{'level':33}})
        self.assertEqual(result['missing'],['Missing']);self.assertFalse(self.calls)

    def test_zero_override_clears_stale_stat_even_if_multiplier_already_zero(self):
        result=self.run_restore({'Cheater':{'multipliers':{'6':0.}}})
        self.assertEqual(self.calls,['RefreshCurrentGearStats',9,'UpdateEquipmentStats'])
        self.assertEqual(self.state['CurrentStats'].items[6],0)
        self.assertEqual(result['applied'],[['Cheater','multipliers','6']])

    def test_uncertain_mutation_is_not_retried(self):
        calls=[]
        def fail(*args):
            calls.append(args[1])
            if args[1]==7:return 40
            raise RuntimeError('uncertain')
        with self.assertRaisesRegex(RuntimeError,'uncertain'):self.run_restore({'Cheater':{'cost':35}},fail)
        self.assertEqual(calls,[7,6])

    def test_exact_restore_removes_added_zero_entries(self):
        self.run_restore({'Cheater':{'multipliers':{'1':.7,'6':0.},'stat_keys':[1],'multiplier_keys':[1]}})
        self.assertEqual(self.state['CurrentStats'].items,{1:2636})
        self.assertEqual(self.state['BaseStatsMultipliers'].items,{1:.7})
        self.assertEqual(self.calls.count(12),2)

    def test_zero_entry_that_existed_in_baseline_is_retained(self):
        self.run_restore({'Cheater':{'multipliers':{'1':.7,'6':0.},'stat_keys':[1,6],'multiplier_keys':[1,6]}})
        self.assertIn(6,self.state['CurrentStats'].items)
        self.assertNotIn(12,self.calls)

    def test_level_precedes_explicit_multiplier_and_final_refresh(self):
        self.run_restore({'Cheater':{'level':32,'multipliers':{'1':.6}}})
        self.assertEqual(self.calls,[4,'SetBaseStatsMultiplier','RefreshCurrentGearStats','UpdateEquipmentStats'])

    def test_ownership_additions_use_one_explicit_subset_batch(self):
        self.scope._session._transport.picto_batch_protocol=1
        owner=NS(owned={'Cheater':(self.item,33)},catalog=self.catalog,set_owned=Mock())
        self.catalog.with_observations=lambda other:self.catalog
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=owner), \
             patch('expedition33.picto_startup_batch.run',return_value=['NewA','NewB']) as run:
            result=self.run_restore({'Cheater':{'owned':True},'NewA':{'owned':True},'NewB':{'owned':True}})
        run.assert_called_once_with(owner,['NewA','NewB'],desired=True)
        owner.set_owned.assert_not_called()
        self.assertEqual(result['applied'],[['NewA','owned'],['NewB','owned']])

    def test_ownership_removals_use_false_batch(self):
        self.scope._session._transport.picto_batch_protocol=1
        owner=NS(owned={'Cheater':(self.item,33)},catalog=self.catalog,set_owned=Mock())
        self.catalog.with_observations=lambda other:self.catalog
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=owner), \
             patch('expedition33.picto_startup_batch.run',return_value=['Cheater']) as run:
            self.run_restore({'Cheater':{'owned':False}})
        run.assert_called_once_with(owner,['Cheater'],desired=False)
        owner.set_owned.assert_not_called()

    def test_ownership_batch_failure_never_retries_individually(self):
        self.scope._session._transport.picto_batch_protocol=1
        owner=NS(owned={},catalog=self.catalog,set_owned=Mock())
        with patch('expedition33.picto_inventory.PictoOwnership',return_value=owner), \
             patch('expedition33.picto_startup_batch.run',side_effect=RuntimeError('uncertain')) as run:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):
                self.run_restore({'NewA':{'owned':True}})
        run.assert_called_once()
        owner.set_owned.assert_not_called()
