import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
spec = importlib.util.spec_from_file_location('picto_preferences_test', ROOT / 'src/expedition33/picto_preferences.py')
prefs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prefs)


class Preferences(unittest.TestCase):
    def test_roundtrip_only_explicit_fields_and_other_pictos(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pictos.json'
            store = prefs.PictoPreferences(path)
            store.remember('Cheater', 'stat', 1.4, 1)
            store.remember('Cheater', 'cost', 30)
            store.remember('ComboAttack3', 'mastery', True)
            again = prefs.PictoPreferences(path)
            self.assertEqual(again.profiles, {'Cheater': {'multipliers': {'1': 1.4}, 'cost': 30}, 'ComboAttack3': {'mastered': True}})
            self.assertNotIn('address', path.read_text())

    def test_invalid_values_never_replace_valid_generation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pictos.json'
            store = prefs.PictoPreferences(path)
            store.remember('Cheater', 'cost', 30)
            before = path.read_bytes()
            for mode, value, key in [('cost', 101, None), ('level', 0, None), ('stat', float('nan'), 1), ('stat', .5, 22), ('mastery', 1, None)]:
                with self.assertRaises(prefs.SettingsError):
                    store.remember('Cheater', mode, value, key)
                self.assertEqual(path.read_bytes(), before)

    def test_stale_writer_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pictos.json'
            first, stale = prefs.PictoPreferences(path), prefs.PictoPreferences(path)
            first.remember('Cheater', 'cost', 30)
            with self.assertRaises(prefs.SettingsError):
                stale.remember('Cheater', 'cost', 5)
            self.assertEqual(prefs.PictoPreferences(path).profiles['Cheater']['cost'], 30)

    def test_clear_one_then_all_preserves_settings_and_other_profiles(self):
        from expedition33.picto_saved_changes import clear_saved
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pictos.json'
            store=prefs.PictoPreferences(path)
            store.remember('Cheater','cost',2)
            store.remember('ComboAttack3','level',26)
            clear_saved(store,'Cheater')
            self.assertEqual(prefs.PictoPreferences(path).profiles,{'ComboAttack3':{'level':26}})
            clear_saved(store)
            self.assertEqual(prefs.PictoPreferences(path).profiles,{})

    def test_failed_clear_keeps_in_memory_profiles(self):
        from expedition33.picto_saved_changes import clear_saved
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'pictos.json'
            store=prefs.PictoPreferences(path)
            store.remember('Cheater','cost',2)
            stale=prefs.PictoPreferences(path)
            store.remember('Cheater','cost',3)
            with self.assertRaises(prefs.SettingsError):clear_saved(stale)
            self.assertEqual(stale.profiles,{'Cheater':{'cost':2}})
            self.assertEqual(prefs.PictoPreferences(path).profiles,{'Cheater':{'cost':3}})

    def test_future_schema_does_not_get_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'pictos.json'
            path.write_text(json.dumps({'version': 1, 'revision': 0, 'mods': {prefs.MOD_ID: {'options': {'schema': 2, 'pictos': {}}}}}))
            with self.assertRaises(prefs.SettingsError):
                prefs.PictoPreferences(path)


if __name__ == '__main__':
    unittest.main()
