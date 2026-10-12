import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
import inspect_actor_cinematic_imports as probe


class ActorImportTests(unittest.TestCase):
    def model(self):
        return N(video=None, title_replay=None, session=object(), discover=Mock(),
                 discovery={'confirmed': [dict(id=d, sequence=s,
                    definition_sha256=h, unlocked=True) for d,s,h in probe.PROFILES]})

    def test_unlock_hash_and_duplicates_refuse_before_retention(self):
        for mutation in ('locked', 'hash', 'duplicate'):
            model = self.model()
            row = model.discovery['confirmed'][0]
            if mutation == 'locked': row['unlocked'] = False
            elif mutation == 'hash': row['definition_sha256'] = 'wrong'
            else: model.discovery['confirmed'].append(row.copy())
            with patch.object(probe, 'SessionScope') as scope:
                with self.assertRaisesRegex(RuntimeError, 'freshly unlocked'):
                    probe.run(model)
                scope.assert_not_called()

    def test_active_playback_refuses_loading(self):
        model = self.model(); model.video = object()
        with patch.object(probe, 'load_asset') as load:
            with self.assertRaisesRegex(RuntimeError, 'Stop playback'): probe.run(model)
            load.assert_not_called()

    def test_wrong_asset_class_closes_scope(self):
        scope = Mock(pid=12)
        with patch.object(probe, 'SessionScope', return_value=scope), \
             patch.object(probe, 'load_asset', return_value=N(return_value=N(class_name='Actor'))), \
             patch.object(probe, 'capture') as capture:
            with self.assertRaisesRegex(RuntimeError, 'definition class'): probe.run(self.model())
            scope.close.assert_called_once(); capture.assert_not_called()

    def test_game_identity_change_closes_scope(self):
        scope = Mock(pid=12)
        values = [N(return_value=N(class_name=name)) for name in
                  ['BP_GameAction_CinematicWithLightingScenario_C'] * 2 + ['LevelSequence'] * 2]
        with patch.object(probe, 'SessionScope', return_value=scope), \
             patch.object(probe, 'load_asset', side_effect=values), \
             patch.object(probe, 'capture', return_value=N(pid=13)):
            with self.assertRaisesRegex(RuntimeError, 'identity changed'): probe.run(self.model())
            scope.close.assert_called_once()


if __name__ == '__main__': unittest.main()
