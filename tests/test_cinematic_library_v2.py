import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

from expedition33.cinematics import library

ROOT = Path(__file__).resolve().parents[1]
WORLD = '/Game/Levels/WorldMap/Level_WorldMap_Main_V2.Level_WorldMap_Main_V2'


class CinematicLibraryTests(unittest.TestCase):
    def test_movie_profile_does_not_hide_an_admitted_original_map_route(self):
        original = next(p for key,p in library.original_profiles().items() if key in library.MEDIA_PROFILES)
        scene = next(s for s in self.scenes(original_action_available=True,
            allow_original_actions=True,current_world_path=original['world_path']) if s['id']==original['id'])
        self.assertEqual(scene['replay_kind'],'movie')
        self.assertFalse(scene['supported'])
        self.assertTrue(scene['original_supported'])
        for allow,world in ((False,original['world_path']),(True,'/Game/Other.Other')):
            scene = next(s for s in self.scenes(original_action_available=True,
                allow_original_actions=allow,current_world_path=world) if s['id']==original['id'])
            self.assertFalse(scene['original_supported'])

    def setUp(self):
        self.catalog = json.loads((ROOT / 'mods/Cinematics/catalog.json').read_text())
        self.catalog['manifest_sha256'] = hashlib.sha256(b'fixture').hexdigest()
        self.profile = next(p for p in library.PREVIEW_PROFILES.values() if p.saved_id=='SimonPhaseTransition')

    def scenes(self, history=None, **options):
        return library.catalog_scenes(history or {}, False, self.catalog, b'fixture', **options)

    def preview(self, history=None, **options):
        return next(s for s in self.scenes(history, **options) if s['id'] == self.profile.definition)

    def test_original_story_requires_explicit_setting_and_original_map(self):
        profiles = library.original_profiles()
        profile = next(p for p in profiles.values() if p['id'] not in library.PREVIEW_PROFILES and
                       p['id'] not in library.TITLE_PROFILES and p['id'] not in library.MEDIA_PROFILES)
        for allow, world, expected in ((False, profile['world_path'], False),
                                       (True, WORLD, False), (True, profile['world_path'], True)):
            scene = next(s for s in self.scenes(original_action_available=True,
                allow_original_actions=allow, current_world_path=world) if s['id'] == profile['id'])
            self.assertIs(scene['original_supported'], expected)
            self.assertEqual(scene['controls'], (1,))
            self.assertIn('campaign callbacks', scene['reason'])
            self.assertIn('Stop is unavailable', scene['reason'])

    def test_preview_requires_exact_unlock_runtime_and_qualified_world(self):
        for unlock in (None, False, 1, 'true'):
            scene = self.preview({self.profile.saved_id: unlock}, owned_preview_available=True,
                                 current_world_path=WORLD)
            self.assertFalse(scene['preview_supported'])
        self.assertFalse(self.preview({self.profile.saved_id: True}, owned_preview_available=True,
                                      current_world_path='/Game/Other.Other')['preview_supported'])
        scene = self.preview({self.profile.saved_id: True}, owned_preview_available=True,
                             current_world_path=WORLD)
        self.assertTrue(scene['preview_supported'])
        self.assertEqual(scene['controls'], (11, 4))
        self.assertEqual(scene['validation'], 'live_partial')

    def test_changing_any_preview_identity_revokes_admission(self):
        for field, value in (('saved_id', 'Other'), ('sequence', '/Game/Other.Other'),
                             ('sha256', '0' * 64)):
            with self.subTest(field=field):
                catalog = copy.deepcopy(self.catalog)
                row = next(r for r in catalog['scenes'] if r['id'] == self.profile.definition)
                row[field] = value
                scenes = library.catalog_scenes({self.profile.saved_id: True}, False, catalog,
                    b'fixture', owned_preview_available=True, current_world_path=WORLD)
                scene = next(r for r in scenes if r['id'] == self.profile.definition)
                self.assertFalse(scene['preview_supported'])

    def test_manifest_or_duplicate_identity_rejects_entire_snapshot(self):
        with self.assertRaisesRegex(ValueError, 'manifest'):
            library.catalog_scenes({}, False, self.catalog, b'changed')
        self.catalog['scenes'].append(copy.deepcopy(self.catalog['scenes'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.scenes()

    def test_show_all_inventory_never_grants_playback(self):
        scene = library.installed_cinematics(['Sandfall/Content/Movies/CS_Unknown.mp4\t12'])[0]
        self.assertIsNone(scene['unlocked'])
        self.assertFalse(scene['supported'])

    def test_boolean_protocol_is_not_negotiated_version(self):
        names = ('sequence_player_protocol', 'sequence_camera_protocol', 'sequence_origin_protocol',
                 'frame_time_values_protocol', 'menu_protocol', 'sequence_retirement_protocol')
        transport = SimpleNamespace(**dict.fromkeys(names, 1))
        self.assertTrue(library.preview_available(transport))
        for name in names:
            setattr(transport, name, True)
            self.assertFalse(library.preview_available(transport))
            setattr(transport, name, 1)

    def test_boolean_catalog_version_is_rejected(self):
        self.catalog['version'] = True
        with self.assertRaises(ValueError):
            self.scenes()


if __name__ == '__main__':
    unittest.main()
