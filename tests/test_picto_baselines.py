import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from expedition33.picto_baselines import Baselines
from expedition33.picto_preferences import MOD_ID

class BaselineTests(unittest.TestCase):
    def test_old_baseline_cannot_guess_original_stat_membership(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Baselines(Path(folder)/'baseline.json')
            b.data={'pid':5,'profiles':{'Cheater':{'owned':True,'multipliers':{'6':0.}}}}
            with self.assertRaisesRegex(RuntimeError,'Exact stat baseline'):b.targets(5,['Cheater'])

    def test_reloads_do_not_replace_originals_and_targets_are_detached(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'baseline.json'
            b=Baselines(path)
            b.store.save(MOD_ID,{'options':{'schema':1,'pid':5,'profiles':{'Cheater':{'cost':40}},'mastery_steps':{'Cheater':4}}})
            b=Baselines(path)
            self.assertEqual(b.capture(SimpleNamespace(pid=5),None),{'Cheater':{'cost':40}})
            result=b.targets(5,['Cheater']);result['Cheater']['cost']=2
            self.assertEqual(b.targets(5,['Cheater']),{'Cheater':{'cost':40,'mastery_steps':4}})
            with self.assertRaises(RuntimeError):b.targets(6,['Cheater'])
            with self.assertRaises(RuntimeError):b.targets(5,['Missing'])

    def test_existing_modified_session_is_not_a_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            b=Baselines(Path(folder)/'baseline.json')
            b.store.save(MOD_ID,{'options':{'schema':1,'pid':5,'profiles':{},'source':'already modified; restart required'}})
            b=Baselines(b.store.path)
            self.assertEqual(b.capture(SimpleNamespace(pid=5),None),{})
            with self.assertRaises(RuntimeError):b.targets(5,['Cheater'])
