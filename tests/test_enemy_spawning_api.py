import json
from pathlib import Path
import runpy
import tempfile
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33._scope import SessionScope
from expedition33.enemy_spawning import EnemySpawner,load_catalog

class EnemySpawningAPITests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.catalog_path=Path(self.directory.name)/'catalog.json'
        self.data=dict(schema=1,entries=[dict(id='world',class_path='/Game/Enemies/BP_World.BP_World_C',spawn_available=True),
            dict(id='review',class_path='/Game/Enemies/BP_Review.BP_Review_C',spawn_available=False)])
        self.catalog_path.write_text(json.dumps(self.data),encoding='utf8')
        self.transport=NS(enemy_spawn_protocol=3,enemy_retirement_protocol=1,enemy_pose_protocol=1,command=Mock())
        self.scope=SessionScope(NS(_transport=self.transport,_check=lambda:None,pid=1,
            console=NS(dispatcher=NS(namespace={})),_abort_ownership=Mock()))
    def service(self):return EnemySpawner(self.scope,catalog_path=self.catalog_path)
    def test_review_entries_and_unknown_ids_never_load_or_spawn(self):
        service=self.service()
        with patch('expedition33.enemy_spawning.load_class') as load,patch('expedition33.enemy_spawning.controller_context') as context:
            for key in ('review','unknown',[]):
                with self.assertRaises(ValueError):service.spawn(key)
            load.assert_not_called();context.assert_not_called()
        self.transport.command.assert_not_called();service.close()
    def test_invalid_policy_is_rejected_before_context_or_native_work(self):
        service=self.service()
        with patch('expedition33.enemy_spawning.controller_context') as context:
            with self.assertRaises(ValueError):service.spawn('world',policy='anything')
            context.assert_not_called()
        service.close();self.transport.command.assert_not_called()
    def test_unsupported_map_is_explicit_before_class_loading(self):
        service=self.service()
        with (patch('expedition33.enemy_spawning.controller_context',return_value=dict(world_path='/Game/Other.Other')),
              patch('expedition33.enemy_spawning.load_class') as load):
            with self.assertRaisesRegex(RuntimeError,'QA world only'):service.spawn('world')
            load.assert_not_called()
        service.close();self.transport.command.assert_not_called()
    def test_runtime_must_advertise_battle_aware_retirement(self):
        for value in (0,True,2):
            self.transport.enemy_retirement_protocol=value
            with self.assertRaisesRegex(RuntimeError,'battle-aware'):self.service()
        self.assertEqual(self.scope._enemy_spawn_owners,[]);self.transport.command.assert_not_called()
    def test_catalog_duplicate_ids_and_implicit_availability_are_rejected(self):
        self.data['entries'][1]['id']='world'
        self.catalog_path.write_text(json.dumps(self.data),encoding='utf8')
        with self.assertRaises(ValueError):load_catalog(self.catalog_path)
        self.data['entries'][1]['id']='review';self.data['entries'][0]['spawn_available']=1
        self.catalog_path.write_text(json.dumps(self.data),encoding='utf8')
        with self.assertRaises(ValueError):load_catalog(self.catalog_path)
    def test_bundled_catalog_preserves_existing_counts(self):
        data=load_catalog();self.assertEqual(len(data['entries']),683)
        self.assertEqual(sum(r['spawn_available'] for r in data['entries']),193)

class EnemyModLifecycleTests(unittest.TestCase):
    def model(self):
        mod=runpy.run_path(str(Path(__file__).resolve().parents[1]/'mods/EnemySpawner/mod.py'))['Mod']()
        mod.spawner=NS(poll_expanded_formation=Mock(),helper_encounter=None,_owner=NS(has_native_work=False),remove=Mock(),spawn=Mock(),close=Mock(return_value=True),status=Mock(return_value={}))
        mod.native=NS(parent=NS(close_menu=Mock()),close=Mock())
        return mod
    def test_menu_closes_before_queued_spawn_and_does_not_replay_failures(self):
        mod=self.model();events=[]
        mod.native.parent.close_menu.side_effect=lambda:events.append('close')
        mod.spawner.remove.side_effect=lambda:events.append('remove')
        def fail(*args,**kwargs):events.append('spawn');raise RuntimeError('unknown outcome')
        mod.catalog={'entries':[{'id':'world'}]}
        mod.spawner.spawn.side_effect=fail
        with patch('expedition33.enemy_authored_routes.authored_spawn_profile',return_value=None), patch('expedition33.enemy_encounter_preflight.validate_default_encounter'):
            mod.queue('isolated','world');mod.poll();mod.poll()
        self.assertEqual(events,['close','remove','spawn']);self.assertEqual(mod._last_error,'unknown outcome')
    def test_disable_closes_native_view_after_owned_enemy(self):
        mod=self.model();events=[]
        mod.spawner.close.side_effect=lambda:events.append('enemy') or True
        mod.native.close.side_effect=lambda:events.append('view')
        mod.disable();self.assertEqual(events,['enemy','view'])
