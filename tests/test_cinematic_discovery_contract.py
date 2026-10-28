"""Exercise the real discovery producer and title consumer together."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace as N
from unittest import TestCase
from unittest.mock import Mock, patch

from test_cinematics import module as mod
from expedition33.cinematics.title_replay import ExactTitleReplay
from expedition33.values import StoredMap


class DiscoveryContractTests(TestCase):
    def setUp(self):
        self.model = mod.Mod()
        profiles = tuple(mod.TITLE_PROFILES.values())
        requirements = {name: 1 for profile in profiles for name in profile.required_protocols}
        transport = N(_executable='fixture', original_game_action_protocol=0,
                      cinematic_title_profiles=[p.profile_id for p in profiles], **requirements)
        self.model.session = N(pid=1, _check=Mock(), _session=N(_transport=transport))
        self.context = dict(world=(1,2,3,4), controller=(1,5,6,7), world_path='/Game/Fixture.Fixture')
        catalog = json.loads((Path(__file__).resolve().parents[1]/'mods/Cinematics/catalog.json').read_text())
        catalog['manifest_sha256'] = hashlib.sha256(b'fixture').hexdigest()
        self.model._catalog_inputs = Mock(return_value=(catalog, b'fixture'))
        self.stack = self.enterContext(ExitStack())
        self.stack.enter_context(patch.object(mod, 'shared_operation'))
        self.stack.enter_context(patch.object(mod, 'controller_context', return_value=self.context))
        self.history = self.stack.enter_context(patch.object(mod, 'read_current_history',
            side_effect=lambda _: dict(history=StoredMap({p.saved_id:True for p in profiles}),
                                      context_identities={'world':self.context['world']}, selected_slot=0)))

    def title(self, profile):
        return ExactTitleReplay(self.model.session, lambda: None, self.model._refresh_now,
                                adapter_factory=Mock(), profile=profile)

    def test_each_advertised_title_passes_real_discovery_contract(self):
        for profile in mod.TITLE_PROFILES.values():
            with self.subTest(profile=profile.profile_id):
                snapshot = self.model._refresh_now()
                row = next(r for r in snapshot['all'] if r['id']==profile.definition)
                self.assertTrue(row['supported'])
                self.assertIs(snapshot['definition_catalog_complete'], True)
                self.title(profile)._verify_unlock(profile.definition)

    def test_failed_catalog_does_not_inherit_previous_completeness(self):
        self.assertTrue(self.model._refresh_now()['definition_catalog_complete'])
        self.model._catalog_inputs.side_effect = ValueError('Manifest changed')
        snapshot = self.model._refresh_now()
        self.assertIs(snapshot['definition_catalog_complete'], False)
        self.assertEqual(snapshot['catalog_error'], 'Manifest changed')
        with self.assertRaisesRegex(RuntimeError, 'mapping and current-save unlock'):
            self.title(mod.PROLOGUE)._verify_unlock(mod.PROLOGUE.definition)

    def test_valid_catalog_does_not_substitute_for_current_history(self):
        self.history.side_effect = RuntimeError('Current game history has no loaded save context')
        with patch.object(mod.LOG, 'exception'):
            snapshot = self.model._refresh_now()
            self.assertIs(snapshot['definition_catalog_complete'], True)
            self.assertEqual(snapshot['state'], 'history_unavailable')
            self.assertEqual(snapshot['confirmed'], [])
            with self.assertRaisesRegex(RuntimeError, 'mapping and current-save unlock'):
                self.title(mod.PROLOGUE)._verify_unlock(mod.PROLOGUE.definition)
