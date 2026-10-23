"""Offline guards for the new menu path, using the unchanged roster adapter."""
import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT/'src'))
import expedition33
expedition33.__path__.insert(0,str(ROOT/'src/expedition33'))

from expedition33 import alpha_original_menu as api
from expedition33.encounter_tuning import EncounterTuning
from expedition33.original_encounter_roster import resolve_source


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'mods/EnemySpawner'/filename)
    value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class AlphaMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'src/expedition33/_enemy_catalog.json').read_text(encoding='utf-8'))
        cls.mod=module('alpha_menu_mod','mod.py')
        cls.view=module('alpha_menu_view','view.py')

    def model(self):
        m=self.mod.Mod();m.catalog=copy.deepcopy(self.catalog)
        m.arena_identity=(100,0,900000);m.arenas={'arenas':[{'identity':m.arena_identity}]}
        m.native=NS(parent=NS(close_menu=Mock()))
        m._capture_tuning=Mock(return_value=EncounterTuning('override',99,1000,2))
        transport=NS(owned_authored_entry_protocol=1,encounter_retry_tuning_protocol=1)
        m.spawner=NS(_owner=NS(has_native_work=False),helper_encounter=None,
            _scope=NS(_session=NS(_transport=transport)),
            spawn=Mock(return_value={'has_owned_enemy':True,'stage':'prepared','arena_identity':(100,42,900000)}),
            start_authored_encounter=Mock(return_value={'acknowledged':True}),
            status=Mock(return_value={}),poll_expanded_formation=Mock(),remove=Mock(),activate=Mock())
        return m

    def test_menu_closes_before_spawn_and_uses_exact_held_anchor(self):
        m=self.model();order=[]
        m.native.parent.close_menu.side_effect=lambda:order.append('close')
        def spawn(*args,**kwargs):
            order.append('spawn')
            self.assertFalse(kwargs['activate']);self.assertTrue(kwargs['grounded'])
            self.assertEqual(args,(api.ANCHOR,));self.assertEqual(kwargs['policy'],'isolated')
            self.assertEqual(kwargs['tuning'].health,1000)
            m.spawner._owner.has_native_work=True
            return {'has_owned_enemy':True,'stage':'prepared','arena_identity':(100,42,900000)}
        m.spawner.spawn.side_effect=spawn
        m.spawner.start_authored_encounter.side_effect=lambda *a,**k:order.append('entry') or {'acknowledged':True}
        m.queue_original_alpha();m.poll()
        self.assertEqual(order,['close','spawn','entry'])
        m.spawner.start_authored_encounter.assert_called_once_with(api.ALPHA,experimental=True,dispatch=True)
        m.spawner.activate.assert_not_called();m.spawner.remove.assert_not_called()
        self.assertEqual(m.arena_identity,(100,42,900000))
        self.assertTrue(m._last_operation['completed']);self.assertFalse(m._last_operation['exploration_assembly_verified'])

    def test_pending_capture_is_immutable_and_status_serializes(self):
        m=self.model();m.queue_original_alpha()
        m.tuning=EncounterTuning()
        self.assertEqual(m._original_pending['tuning'].health,1000)
        status=m.current_status();json.dumps(status)
        self.assertEqual(status['pending'],('original_alpha_roster',api.ALPHA))

    def test_unknown_dispatch_is_not_replayed_or_retired(self):
        m=self.model();m.spawner.start_authored_encounter.side_effect=RuntimeError('Unknown acknowledgement')
        m.queue_original_alpha();m.poll();m.poll()
        m.spawner.start_authored_encounter.assert_called_once()
        m.spawner.remove.assert_not_called()
        self.assertIsNone(m._original_pending)
        self.assertTrue(m._last_operation['dispatch_attempted']);self.assertFalse(m._last_operation['completed'])
        self.assertEqual(m._last_error,'Unknown acknowledgement')

    def test_failed_stage_never_dispatches_and_is_not_retried(self):
        m=self.model();m.spawner.spawn.side_effect=RuntimeError('Anchor failed')
        m.queue_original_alpha();m.poll();m.poll()
        m.spawner.spawn.assert_called_once();m.spawner.start_authored_encounter.assert_not_called()
        self.assertFalse(m._last_operation['dispatch_attempted'])

    def test_close_failure_does_not_dispatch(self):
        m=self.model();m.native.parent.close_menu.side_effect=RuntimeError('menu retained')
        m.queue_original_alpha();api.poll(m);api.poll(m)
        m.spawner.spawn.assert_not_called();m.spawner.start_authored_encounter.assert_not_called()

    def test_competing_operations_block_while_pending(self):
        for action in (lambda m:m.queue('remove'),lambda m:m.queue_npc(),lambda m:m.queue_helper(),
                       lambda m:m.queue_addition(api.ALPHA,'Boss_Simon_ALPHA'),
                       lambda m:m.select_arena((100,42,900000)),lambda m:m.queue_original_alpha()):
            m=self.model();m.queue_original_alpha()
            with self.subTest(action=action),self.assertRaises(RuntimeError):action(m)
            m.spawner.spawn.assert_not_called()

    def test_existing_owners_pending_operations_and_old_runtime_reject(self):
        changes=[lambda m:setattr(m,'mode','original_campaign_actions'),lambda m:setattr(m,'arena_identity',None),
            lambda m:setattr(m.spawner._owner,'has_native_work',True),
            lambda m:setattr(m.spawner,'helper_encounter',NS(phase='waiting_for_approach')),
            lambda m:setattr(m,'npc_encounter',NS(phase='waiting_for_approach')),
            lambda m:setattr(m,'_pending',('isolated',api.ANCHOR)),
            lambda m:setattr(m,'_pending_addition',(api.ALPHA,'Boss_Simon_ALPHA')),
            lambda m:setattr(m.spawner._scope._session._transport,'owned_authored_entry_protocol',0),
            lambda m:setattr(m.spawner._scope._session._transport,'encounter_retry_tuning_protocol',0)]
        for mutate in changes:
            m=self.model();mutate(m)
            with self.subTest(mutate=mutate),self.assertRaises((ValueError,RuntimeError)):m.queue_original_alpha()
            self.assertIsNone(m._original_pending);m.spawner.spawn.assert_not_called()

    def test_catalog_drift_rejects_without_promoting_any_entry(self):
        for identity in (api.ALPHA,api.ANCHOR):
            m=self.model();entry=next(e for e in m.catalog['entries'] if e['id']==identity)
            entry['class_path']='/Game/Wrong.Wrong_C'
            with self.subTest(identity=identity),self.assertRaises(ValueError):m.queue_original_alpha()
        m=self.model();before=copy.deepcopy(m.catalog);m.queue_original_alpha();self.assertEqual(m.catalog,before)
        self.assertFalse(next(e for e in m.catalog['entries'] if e['id']==api.ALPHA)['spawn_available'])
        for identity in ('0000000000000000',):
            with self.subTest(identity=identity),self.assertRaises(ValueError):resolve_source(m.catalog,identity)
        for identity in ('e7e263f066d33733','ab11b529310fbd73','e02190410f616184'):
            changed=copy.deepcopy(m.catalog)
            next(e for e in changed['entries'] if e['id']==identity)['class_path']='/Game/Wrong.Wrong_C'
            with self.subTest(identity=identity),self.assertRaises(ValueError):resolve_source(changed,identity)

    def test_late_owner_or_arena_change_rejects_before_spawn(self):
        for field in ('owner','arena'):
            m=self.model();m.queue_original_alpha()
            if field=='owner':m.spawner._owner.has_native_work=True
            else:m.arena_identity=(900,99,910000)
            api.poll(m);m.spawner.spawn.assert_not_called();m.spawner.start_authored_encounter.assert_not_called()

    def test_menu_is_available_without_altering_catalog_classification(self):
        m=self.model();view=self.view.EnemyView.__new__(self.view.EnemyView)
        view.model=m;view.screen='enemy_original_alpha';view.category='All';view.review=False;view.query='';view.selected=None
        title,description,rows=view._rows()
        self.assertIn('original exploration Simon is not staged',description)
        self.assertIn('Normal Simon and phase 2',description)
        self.assertTrue(any(r[1]=='enemy_original_alpha_begin' and r[3] for r in rows))
        m.arena_identity=None
        self.assertTrue(any(r[1]=='enemy_original_alpha_begin' and not r[3] for r in view._rows()[2]))
        view.screen='enemy_catalog'
        self.assertTrue(any(r[1]=='enemy_original_alpha' for r in view._rows()[2]))
        self.assertFalse(any(r[1:3]==('enemy_select',api.ALPHA) for r in view._rows()[2]))


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(AlphaMenuTests)
    spec=importlib.util.spec_from_file_location('existing_original_roster_tests',ROOT/'candidate-tests/test_original_encounter_roster.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(old))
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (HERE/'alpha-menu-test-results.json').write_text(json.dumps(dict(
        tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        successful=result.wasSuccessful(),runtime_accessed=False,
        limitations='Offline orchestration/source tests; new menu preflight/dispatch not live verified.'),indent=2)+'\n',encoding='utf-8')
    raise SystemExit(not result.wasSuccessful())
