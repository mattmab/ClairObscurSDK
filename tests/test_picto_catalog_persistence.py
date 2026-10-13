"""SDK settings restart coverage; real game inventory persistence is live-tested."""
import tempfile
import unittest
from pathlib import Path

from expedition33.picto_catalog import CatalogView
from expedition33.picto_preferences import PictoPreferences


class CatalogPersistenceTests(unittest.TestCase):
    def test_unlock_setting_roundtrip_preserves_existing_editor_overrides(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            before=PictoPreferences(path)
            before.remember_many('Cheater', [('level',22,None),('stat',.8,1),
                ('cost',2,None),('mastery',True,None)])
            before.remember('Cheater','owned',True)
            restarted=PictoPreferences(path)
            self.assertEqual(restarted.profiles['Cheater'],{
                'level':22,'multipliers':{'1':.8},'cost':2,'mastered':True,'owned':True})
            # Persisted desired ownership does not itself prove live ownership.
            view=CatalogView({'Cheater':{'name':'Cheater','normal':True}}, {})
            self.assertEqual(view.counts['owned'],0)
            view.owned={'Cheater':object()};view.rebuild()
            self.assertEqual(view.counts['owned'],1)


if __name__=='__main__':
    unittest.main()
