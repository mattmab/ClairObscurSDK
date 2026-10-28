import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock
import json
import hashlib
from expedition33.management import ManagementError

spec = importlib.util.spec_from_file_location('cinematics_test', Path(__file__).resolve().parents[1] / 'mods/Cinematics/mod.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class CinematicsViewTests(TestCase):
    def test_unlocked_unsupported_scene_reports_adapter_not_unlock(self):
        from cinematics_v2_fixtures import ready_model
        mod=ready_model(module,dict(id='actor-scene',title='Actor',unlocked=True,
            supported=False,replay_kind=None,reason='Replay adapter unavailable'))
        with self.assertRaisesRegex(ManagementError,'route is unavailable'):mod.control('actor-scene',1)
        self.assertFalse(mod.controller.status().busy)
        mod._refresh_now.assert_not_called()

    def test_non_boolean_unlock_cannot_admit_playback(self):
        from cinematics_v2_fixtures import ready_model
        for value in (False,None,1,'true'):
            mod=ready_model(module,dict(id='actor-scene',title='Actor',unlocked=value,supported=True,replay_kind='title'))
            with self.subTest(value=value),self.assertRaisesRegex(ManagementError,'unavailable'):mod.control('actor-scene',1)
            self.assertFalse(mod.controller.status().busy)
            mod._refresh_now.assert_not_called()

    def test_definition_catalog_preserves_unlock_and_playback_guards(self):
        catalog=json.loads((Path(__file__).resolve().parents[1]/'mods/Cinematics/catalog.json').read_text())
        catalog['manifest_sha256']=hashlib.sha256(b'fixture').hexdigest()
        scenes=module.catalog_scenes({'MyFlowerP1':True},True,catalog,b'fixture')
        self.assertEqual(len(scenes),155)
        self.assertEqual(len({s['id'] for s in scenes}),155)
        playable=[s for s in scenes if s['supported']]
        self.assertEqual(len(playable),1)
        self.assertEqual(playable[0]['saved_id'],'MyFlowerP1')
        for history in ({},{'MyFlowerP1':False},{'MyFlowerP1':1}):
            self.assertFalse(any(s['supported'] for s in module.catalog_scenes(history,True,catalog,b'fixture')))
        self.assertFalse(any(s['supported'] for s in module.catalog_scenes({'MyFlowerP1':True},False,catalog,b'fixture')))
        with self.assertRaisesRegex(ValueError,'manifest'):
            module.catalog_scenes({'MyFlowerP1':True},True,catalog,b'changed')

    def setUp(self):
        self.registry = SimpleNamespace(_check=Mock())
        self.model = SimpleNamespace(reason='History cannot be decoded', discover=Mock(), discovery={'confirmed': [], 'all': []}, show_all=False)
        self.view = module.BrowserView(self.registry, self.model)

    def test_no_unverified_playback_is_callable(self):
        frame = self.view.render()
        for token in range(1, 6):
            with self.assertRaises(ManagementError):
                self.view.activate(frame.revision, token)
        self.model.discover.assert_not_called()

    def test_confirmed_list_selection_and_paging(self):
        self.model.discovery['confirmed'] = [dict(id=str(i), title=f'Scene {i}', reason='Isolation unverified') for i in range(7)]
        frame = self.view.render()
        self.assertEqual(sum(c.token >= 100 for c in frame.controls), 6)
        frame = self.view.activate(frame.revision, 8)
        self.assertEqual([c.token for c in frame.controls if c.token >= 100], [106])
        frame = self.view.activate(frame.revision, 106)
        self.assertIn('Scene 6', frame.description)
        for control in frame.controls:
            if 1 <= control.token <= 5:
                self.assertFalse(control.enabled)

    def test_refresh_and_close_revoke_old_controls(self):
        frame = self.view.render()
        new = self.view.activate(frame.revision, 0)
        self.model.discover.assert_called_once()
        with self.assertRaises(ManagementError):
            self.view.activate(frame.revision, 6)
        self.assertTrue(self.view.activate(new.revision, 6).closed)
        with self.assertRaises(ManagementError):
            self.view.render()

    def test_pending_cleanup_keeps_browser_open(self):
        self.model.stop = Mock(return_value=False)
        frame = self.view.render()
        with self.assertRaisesRegex(ManagementError, 'cleanup'):
            self.view.activate(frame.revision, 6)
        self.assertFalse(self.view.closed)
        self.model.stop.return_value = True
        self.assertTrue(self.view.activate(self.view.render().revision, 6).closed)

    def test_pending_title_prevents_mod_and_menu_release(self):
        from expedition33._sequence_owner import SequenceCleanupDeferred
        from expedition33.cinematics.controller import StopResult
        from cinematics_v2_fixtures import Backend,ready_model
        mod=ready_model(module,dict(id='title',title='Title',replay_kind='title',supported=True,unlocked=True))
        backend=Backend();backend.stop.return_value=StopResult.DEFERRED;backend.close.return_value=False
        mod.controller.queue('title',lambda:backend,mod._last_epoch);mod.controller.poll(mod._last_epoch)
        mod.pause=Mock();self.assertFalse(mod.stop())
        with self.assertRaises(SequenceCleanupDeferred):mod.disable()
        mod.native.close.assert_not_called();mod.pause.close.assert_not_called()
        self.assertTrue(mod.controller.status().busy)

    def test_filter_resets_selection_and_revokes_controls(self):
        self.model.discovery['all'] = [dict(id='unknown', title='Unknown', reason='Unlock unknown')]
        old = self.view.render()
        new = self.view.activate(old.revision, 10)
        self.assertTrue(self.model.show_all)
        self.assertTrue(any(c.token == 100 for c in new.controls))
        with self.assertRaises(ManagementError):
            self.view.activate(old.revision, 100)
        back = self.view.activate(new.revision, 10)
        self.assertFalse(self.model.show_all)
        self.assertFalse(any(c.token >= 100 for c in back.controls))

    def test_manifest_candidates_are_never_treated_as_unlocked(self):
        scenes = module.installed_cinematics([
            'Sandfall/Content/Movies/CS_MyFlower_P1_Intro.mp4\t123',
            'Sandfall/Content/Cinematics/MyFlower/DA_GA_CIN_MyFlower_P1.uasset\t123',
            'Sandfall/Content/Cinematics/MyFlower/DA_GA_CIN_MyFlower_P1.uasset\t123',
            'Sandfall/Content/Movies/LoadingScreen.mp4\t123',
            'Sandfall/Content/Cinematics/MyFlower/DA_GA_CIN_MyFlower_P1.uexp\t123'])
        self.assertEqual(len(scenes), 2)
        for scene in scenes:
            self.assertIsNone(scene['unlocked'])
            self.assertFalse(scene['supported'])
            self.assertIn('unlock unknown', scene['title'])


class StaticPreparationTests(TestCase):
    def test_startup_caches_only_files_and_rechecks_changed_installation(self):
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);manifest=root/'Manifest_UFSFiles_Win64.txt';source=root/'catalog.json'
            def write(data):
                manifest.write_bytes(data)
                source.write_text(json.dumps({'version':1,'manifest_sha256':hashlib.sha256(data).hexdigest(),'scenes':[]}))
            write(b'fixture');model=module.Mod()
            with patch.object(module,'game_root',return_value=root),patch.object(module,'__file__',str(root/'mod.py')),patch('subprocess.Popen',side_effect=AssertionError('process access')):
                model.prepare_startup(None);first=model._catalog_inputs()
                self.assertIsNone(model.session);self.assertIsNone(model.static_preparation_error)
                self.assertIs(model._catalog_inputs()[0],first[0]);self.assertEqual(first[1],b'fixture')
                write(b'changed fixture')
                current=model._catalog_inputs();self.assertIsNot(current[0],first[0]);self.assertEqual(current[1],b'changed fixture')
    def test_missing_manifest_does_not_fail_pure_preparation(self):
        from unittest.mock import patch
        model=module.Mod()
        with patch.object(module,'game_root',side_effect=RuntimeError('unavailable installation')):
            model.prepare_startup(None)
        self.assertEqual(model.static_preparation_error,'unavailable installation');self.assertIsNone(model.session)
