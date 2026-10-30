"""Actual mod/view and SDK lifecycle guards for the direct original-fight route."""
import copy
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import expedition33
expedition33.__path__.insert(0,str(ROOT/'src/expedition33'))
from expedition33.encounter_tuning import EncounterTuning
from expedition33.enemy_spawning import EnemySpawner
from expedition33 import alpha_original_menu

CATALOG_ID='f019ec6032602e07'
RECIPE_ID='duelliste-main'

def load(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'mods/EnemySpawner'/filename)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

class DirectMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod=load('direct_fight_menu_mod','mod.py');cls.view=load('direct_fight_menu_view','view.py')
        cls.catalog=json.loads((ROOT/'src/expedition33/_enemy_catalog.json').read_text())

    def model(self):
        m=self.mod.Mod();m.catalog=copy.deepcopy(self.catalog)
        m.direct_catalog={CATALOG_ID:dict(id=RECIPE_ID,recipe_id=CATALOG_ID,label='Duelliste — original fight',menu_available=True)}
        transport=NS(enemy_trigger_entry_research_protocol=1,battle_entry_dispatch_research_protocol=1,owned_battle_arena_grounding_protocol=1)
        m.spawner=NS(_owner=NS(has_native_work=False),helper_encounter=None,original_fight=None,
            _scope=NS(_session=NS(_transport=transport)),start_original_fight=Mock(return_value={'phase':'entry_pending'}),
            poll_original_fight=Mock(),poll_expanded_formation=Mock(),status=Mock(return_value={}),remove=Mock())
        m.native=NS(parent=NS(close_menu=Mock()))
        m._capture_tuning=Mock(return_value=EncounterTuning())
        return m

    def test_single_intent_closes_menu_before_start_without_selected_arena(self):
        m=self.model();events=[]
        m.native.parent.close_menu.side_effect=lambda:events.append('menu')
        m.spawner.start_original_fight.side_effect=lambda *a,**k:events.append('start') or {'phase':'entry_pending'}
        self.assertIsNone(m.arena_identity)
        m.queue_original_fight(RECIPE_ID);m.poll();m.poll()
        self.assertEqual(events,['menu','start'])
        m.spawner.start_original_fight.assert_called_once_with(RECIPE_ID,tuning=EncounterTuning())
        self.assertTrue(m._last_operation['completed']);self.assertIsNone(m._direct_pending)

    def test_unknown_start_is_not_replayed_or_automatically_retired(self):
        m=self.model();retained=NS(phase='unknown')
        def uncertain(*args,**kwargs):
            m.spawner.original_fight=retained
            raise RuntimeError('uncertain entry; retained')
        m.spawner.start_original_fight.side_effect=uncertain
        m.queue_original_fight(RECIPE_ID);m.poll();m.poll()
        m.spawner.start_original_fight.assert_called_once();m.spawner.remove.assert_not_called()
        self.assertIs(m.spawner.original_fight,retained);self.assertFalse(m._last_operation['completed'])

    def test_failed_menu_close_never_starts(self):
        m=self.model();m.native.parent.close_menu.side_effect=RuntimeError('menu retained')
        m.queue_original_fight(RECIPE_ID);m.poll();m.poll()
        m.spawner.start_original_fight.assert_not_called()

    def test_custom_settings_are_rejected_before_queueing(self):
        m=self.model();m.tuning=EncounterTuning('override',99,1000,2)
        with self.assertRaisesRegex(ValueError,'authored'):m.queue_original_fight(RECIPE_ID)
        self.assertIsNone(m._direct_pending);m.spawner.start_original_fight.assert_not_called()

    def test_click_time_default_settings_survive_next_setting_change(self):
        m=self.model();m.queue_original_fight(RECIPE_ID)
        m.tuning=EncounterTuning('override',99,1000,2);m.poll()
        m.spawner.start_original_fight.assert_called_once_with(RECIPE_ID,tuning=EncounterTuning())

    def test_queued_and_active_direct_fight_exclude_competing_routes(self):
        actions=(lambda m:m.queue('isolated','anything'),lambda m:m.queue_npc(),lambda m:m.queue_helper(),
            lambda m:m.queue_addition('anything','anything'),lambda m:m.queue_original_alpha(),
            lambda m:m.select_arena((1,2,3)),lambda m:m.queue_original_fight(RECIPE_ID))
        for active in (False,True):
            for action in actions:
                m=self.model()
                if active:m.spawner.original_fight=NS(phase='idle_retained')
                else:m.queue_original_fight(RECIPE_ID)
                with self.subTest(active=active,action=action),self.assertRaises(RuntimeError):action(m)
        m=self.model();m.spawner.original_fight=NS(phase='active')
        m.queue('remove');self.assertEqual(m._pending[0],'remove')

    def test_legacy_alpha_entry_cannot_bypass_active_direct_fight_guard(self):
        m=self.model();m.arena_identity=(1,2,3)
        m.spawner._scope._session._transport.owned_authored_entry_protocol=1
        m.spawner._scope._session._transport.encounter_retry_tuning_protocol=1
        m.spawner.original_fight=NS(phase='active')
        with self.assertRaises(RuntimeError):alpha_original_menu.queue(m)

    def test_protocol_booleans_and_old_runtime_are_not_admitted(self):
        for value in (True,0):
            m=self.model();m.spawner._scope._session._transport.enemy_trigger_entry_research_protocol=value
            with self.subTest(value=value),self.assertRaises(RuntimeError):m.queue_original_fight(RECIPE_ID)

    def test_main_menu_exposes_direct_route_without_promoting_world_spawn(self):
        m=self.model();v=self.view.EnemyView.__new__(self.view.EnemyView)
        v.model=m;v.screen='enemy_catalog';v.category='All';v.review=False;v.query='';v.selected=CATALOG_ID
        before=copy.deepcopy(m.catalog)
        title,description,rows=v._rows()
        self.assertTrue(any(r[1:3]==('enemy_select',CATALOG_ID) for r in rows))
        v.screen='enemy_details';title,description,rows=v._rows()
        self.assertTrue(any(r[1]=='enemy_direct_begin' and r[3] for r in rows))
        self.assertTrue(any(r[1]=='enemy_spawn' and not r[3] for r in rows))
        self.assertIn('No exploration character',description)
        self.assertEqual(m.catalog,before)
        self.assertFalse(next(r for r in m.catalog['entries'] if r['id']==CATALOG_ID)['spawn_available'])

    def test_original_stage_descriptions_distinguish_combat_from_cinematic_completion(self):
        from expedition33._original_trigger_fight import direct_fight_recipes
        m=self.model();m.direct_catalog=direct_fight_recipes(m.catalog)
        v=self.view.EnemyView.__new__(self.view.EnemyView)
        v.model=m;v.screen='enemy_details'
        for identity in ('e7e263f066d33733','ab11b529310fbd73'):
            with self.subTest(identity=identity):
                v.selected=identity
                _,description,rows=v._rows()
                self.assertIn('separate original direct-fight choices',description)
                self.assertIn('cinematic handoff between battles',description)
                self.assertIn('not implemented',description)
                self.assertNotIn('not a standalone original encounter',description)
                self.assertTrue(any(r[1]=='enemy_direct_begin' and r[3] for r in rows))
        v.selected='e02190410f616184'
        _,description,_=v._rows()
        self.assertIn('direct fight was tested',description)
        self.assertNotIn('direct fight and original exploration presentation have not been qualified',description)
        v.selected='d6ec611a700522e6'
        _,description,_=v._rows()
        self.assertIn('cutscene was not visible',description)
        self.assertIn('do not verify camera visibility',description)
        self.assertIn('relocation remains unqualified',description)

class DirectSdkLifetimeTests(unittest.TestCase):
    def spawner(self):
        s=EnemySpawner.__new__(EnemySpawner)
        s._scope=NS(_check=Mock());s._owner=NS(has_native_work=False,close=Mock(return_value=True),remove=Mock())
        s._closed=False;s._record={};s._tuning=None;s.helper_encounter=None;s.original_fight=None;s._classes={}
        s.status=Mock(return_value={});return s

    def test_service_is_persisted_before_start_can_fail(self):
        s=self.spawner();service=NS(start=Mock(side_effect=RuntimeError('retained start failure')))
        module=types.ModuleType('expedition33._original_trigger_fight');module.OriginalTriggerFight=Mock(return_value=service)
        with patch.dict(sys.modules,{module.__name__:module}):
            with self.assertRaises(RuntimeError):s.start_original_fight(RECIPE_ID)
        self.assertIs(s.original_fight,service);s._owner.remove.assert_not_called()

    def test_deferred_service_close_prevents_underlying_owner_teardown(self):
        s=self.spawner();s.original_fight=NS(phase='active',close=Mock(return_value=False))
        self.assertFalse(s.close());s._owner.close.assert_not_called()
        with self.assertRaises(RuntimeError):s.remove()
        s._owner.remove.assert_not_called()

    def test_acknowledged_service_remove_does_not_repeat_trigger_removal(self):
        s=self.spawner();s.original_fight=NS(phase='idle_retained',close=Mock(return_value=True))
        s.remove();s.original_fight.close.assert_called_once();s._owner.remove.assert_not_called()

if __name__=='__main__':unittest.main()
