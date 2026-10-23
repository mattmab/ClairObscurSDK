import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch
from contextlib import contextmanager

from expedition33 import RuntimeQueryError

SOURCE = Path(__file__).resolve().parents[1] / 'src/expedition33/world_admission.py'
spec = importlib.util.spec_from_file_location('expedition33._admission_candidate', SOURCE)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def obj(index, cls):
    return N(pid=7, index=index, serial=1, address=0x10000+index*0x100,
             class_name=cls, object_flags=0, class_index=index+10)


def values(**fields):
    return N(types={(1,key): 'BoolProperty' if type(value) is bool else 'IntProperty'
                    for key,value in fields.items()},
             values={(1,key): value for key,value in fields.items()}, errors={}, truncated=set())


class AdmissionTests(unittest.TestCase):
    def observe(self, *, loaded=True, loading=False, slot=0, pawn='BP_jRPG_Character_World_C',
                reciprocal=True, controller_world=None):
        chain = tuple(obj(i, cls) for i,cls in enumerate(
            ('GameEngine','CustomGameViewportClient','World','BP_jRPG_GI_Custom_C'), 1))
        manager = obj(5, 'BP_SaveManager_C')
        controller = obj(6, 'PlayerController')
        catalog = N(pid=7, by_index={14: obj(14,'Class'),15: obj(15,'Class')})
        controller_catalog = N(by_index={6: controller,16: obj(16,'Class')})
        def read_reference(c, target, owner, name, *, project=False):
            self.assertTrue(project)
            return ({'SaveManager':manager, 'GameInstanceReference':chain[3] if reciprocal else None,
                'Pawn':obj(7,pawn) if pawn else None}[name], c)
        def read_values(c, targets, *, fields):
            target=targets[0]
            expected={5:('LoadIsInProgress','SelectedSlot'),4:('SaveLoaded',),6:('Pawn',)}
            self.assertEqual(fields,expected[target.index])
            return {target.index:read_one(target)}
        def read_one(target):
            if target is manager: return values(LoadIsInProgress=loading,SelectedSlot=slot)
            if target is chain[3]: return values(SaveLoaded=loaded)
            return N(types={(16,'Pawn'):'ObjectProperty'})
        with patch.object(m,'ReadBatch'), patch.object(m,'capture_matching',return_value=catalog), \
             patch.object(m,'anchor',return_value=(chain,catalog)), \
             patch.object(m,'read_object_reference',side_effect=read_reference), \
             patch.object(m,'read_values_many',side_effect=read_values), \
             patch.object(m,'capture_selected',return_value=controller_catalog), \
             patch.object(m,'controller_context',return_value=dict(controller=m.identity(controller),
                world=m.identity(chain[2]) if controller_world is None else controller_world)):
            return m.observe_admission(7)

    def test_loaded_reciprocal_save_and_exploration_admit(self):
        snapshot = self.observe(slot=2)
        self.assertTrue(snapshot.activation_ready)
        self.assertEqual(snapshot.token[-1],2)

    def test_title_and_loading_explicitly_inhibit(self):
        self.assertEqual(self.observe(loaded=False).state,'inactive')
        self.assertEqual(self.observe(loading=True).state,'loading')

    def test_combat_possession_preserves_world_token_without_admitting_first_activation(self):
        exploration = self.observe()
        combat = self.observe(pawn='BattlePawn')
        self.assertEqual(combat.state,'world_ready')
        self.assertEqual(combat.token,exploration.token)
        self.assertFalse(combat.activation_ready)

    def test_controller_world_and_reciprocal_races_inhibit_without_teardown(self):
        self.assertEqual(self.observe(controller_world=(7,99,1,0x9999)).state,'observation_pending')
        self.assertEqual(self.observe(reciprocal=False).state,'observation_pending')

    def test_changed_slot_changes_generation(self):
        self.assertNotEqual(self.observe(slot=0).token,self.observe(slot=1).token)

    def test_before_after_must_match(self):
        ready=self.observe()
        changed=m.Admission('inactive','save_not_loaded')
        with patch.object(m,'ReadBatch'), patch.object(m,'_observe',side_effect=(
                (ready,('chain',),('controller',)),(changed,('chain',),None))):
            self.assertEqual(m.observe_admission(7).reason,'context_changed')

    def test_transient_read_is_uncertainty_decode_error_visible(self):
        with patch.object(m,'ReadBatch'), patch.object(m,'_observe',side_effect=RuntimeQueryError('READ_FAILED')):
            self.assertEqual(m.observe_admission(7).state,'observation_pending')
        with patch.object(m,'ReadBatch'), patch.object(m,'_observe',side_effect=RuntimeQueryError('malformed property')):
            with self.assertRaises(RuntimeQueryError):m.observe_admission(7)

    def test_each_restoration_step_rechecks_admission(self):
        first=self.observe()
        states=iter((first,m.Admission('loading','save_load_in_progress'),
                     m.Admission('inactive','save_not_loaded'),self.observe(slot=1)))
        restored=[]
        for index in range(4):
            observation=next(states)
            if observation.activation_ready:restored.append((index,observation.token))
        self.assertEqual([index for index,token in restored],[0,3])
        self.assertNotEqual(restored[0][1],restored[1][1])


class WarmObserverTests(unittest.TestCase):
    def test_engine_discovery_once_but_selected_fresh_every_time(self):
        engine=obj(1,'GameEngine')
        catalog=N(select=lambda name:(engine,))
        provider=m.WarmAdmissionObserver(7)
        with patch.object(m,'capture_matching',return_value=catalog) as discover, \
             patch.object(m,'capture_selected',side_effect=('fresh1','fresh2')) as selected:
            self.assertEqual(provider.engine_catalog(),'fresh1')
            self.assertEqual(provider.engine_catalog(),'fresh2')
            self.assertEqual(discover.call_count,1)
            self.assertEqual(selected.call_count,2)
        provider.close()

    def controller(self,array, *, replacement=False):
        local=obj(8 if replacement else 7,'LocalPlayer')
        if array=='valid':array=m.StoredArray((local,),1)
        values=N(types={(1,'LocalPlayers'):'ArrayProperty'},values={(1,'LocalPlayers'):array},errors={},truncated=set())
        player=obj(9,'PlayerController');world=obj(10,'World')
        catalog=N(by_index={20:object()},outer_chain=lambda target:(world,))
        provider=m.WarmAdmissionObserver(7)
        with patch.object(m,'read_values_with_references',return_value=(values,catalog)) as read, \
             patch.object(m,'read_values_many',return_value={local.index:N(types={(20,'PlayerController'):'ObjectProperty'})}), \
             patch.object(m,'read_object_reference',return_value=(player,catalog)):
            result=provider.controller(catalog,obj(11,'BP_jRPG_GI_Custom_C'))
            read.assert_called_once()
            self.assertEqual(read.call_args.kwargs,{'fields':('LocalPlayers',)})
            return result

    def test_current_localplayer_replacement_is_not_cached(self):
        self.assertEqual(self.controller('valid'),self.controller('valid',replacement=True))

    def test_partial_ambiguous_and_wrong_member_arrays_rejected(self):
        for array,error in ((m.StoredArray((),1),RuntimeError),
                            (m.StoredArray((),0),m.NotReady),
                            (m.StoredArray((obj(1,'LocalPlayer'),obj(2,'LocalPlayer')),2),m.NotReady),
                            (m.StoredArray((obj(1,'Other'),),1),RuntimeError)):
            with self.subTest(array=array),self.assertRaises(error):self.controller(array)

    def test_stale_engine_selection_never_retried_same_call(self):
        provider=m.WarmAdmissionObserver(7)
        provider._engine=(1,2,0x10000)
        with patch.object(m,'capture_selected',side_effect=RuntimeQueryError('selected identity changed')) as selected, \
             patch.object(m,'capture_matching') as discover:
            with self.assertRaises(RuntimeQueryError):provider.engine_catalog()
            self.assertEqual(selected.call_count,1)
            discover.assert_not_called()

    def test_worker_reused_but_double_observations_fresh_and_close_owned(self):
        class Reader:
            def __init__(self):self._closed=False;self.binds=0;self.closes=0
            @contextmanager
            def bind(self):self.binds+=1;yield
            def close(self):self._closed=True;self.closes+=1
        reader=Reader();provider=m.WarmAdmissionObserver(7)
        state=m.Admission('world_ready','exploration_ready',('epoch',),True)
        with patch.object(m,'ReadBatch',return_value=reader) as factory, \
             patch.object(m,'_read_admission',side_effect=(state,state)) as observe:
            self.assertEqual(provider.observe(),state)
            self.assertEqual(provider.observe(),state)
            self.assertEqual(factory.call_count,1)
            self.assertEqual(observe.call_count,2)
            self.assertEqual(reader.binds,2)
            provider.close();provider.close()
            self.assertEqual(reader.closes,1)
            with self.assertRaises(RuntimeError):provider.observe()

    def test_failed_worker_discarded_before_next_operation(self):
        class Reader:
            _closed=False
            @contextmanager
            def bind(self):yield
            def close(self):self._closed=True
        first=Reader();second=Reader();provider=m.WarmAdmissionObserver(7)
        with patch.object(m,'ReadBatch',side_effect=(first,second)) as factory, \
             patch.object(m,'_read_admission',side_effect=(RuntimeQueryError('bad decode'),m.Admission('inactive','save_not_loaded'))):
            with self.assertRaises(RuntimeQueryError):provider.observe()
            self.assertTrue(first._closed)
            self.assertIsNone(provider._reader)
            self.assertEqual(factory.call_count,1)
            self.assertEqual(provider.observe().state,'inactive')
            self.assertEqual(factory.call_count,2)
            provider.close()


if __name__=='__main__':unittest.main()
