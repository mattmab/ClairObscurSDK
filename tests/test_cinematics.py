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
        mod = module.Mod()
        mod.stop = Mock(return_value=True)
        mod.discover = Mock()
        mod.discovery = {'confirmed': [dict(id='actor-scene', unlocked=True,
            supported=False, reason='In-engine replay is not implemented for this definition.')]}
        with self.assertRaisesRegex(ManagementError, 'unlocked, but replay is unavailable'):
            mod.control('actor-scene', 1)
        self.assertIsNone(mod.video)
        mod.discover.assert_called_once()

    def test_non_boolean_unlock_cannot_admit_playback(self):
        for value in (False, None, 1, 'true'):
            mod = module.Mod()
            mod.stop = Mock(return_value=True)
            mod.discover = Mock()
            mod.discovery = {'confirmed': [dict(id='actor-scene', unlocked=value, supported=True)]}
            with self.assertRaisesRegex(ManagementError, 'not unlocked'):
                mod.control('actor-scene', 1)
            self.assertIsNone(mod.video)

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
        mod = module.Mod()
        mod.title_replay = Mock()
        mod.title_replay.stop.return_value = {'state': 'cleanup_pending', 'active': True}
        mod.native = Mock()
        mod.pause = Mock()
        self.assertFalse(mod.stop())
        with self.assertRaises(SequenceCleanupDeferred):
            mod.disable()
        mod.native.close.assert_not_called()
        mod.pause.close.assert_not_called()

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
