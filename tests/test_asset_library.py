import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from mods.CatalogModels import library
from mods.CatalogModels.browser import BrowserView

class AssetLibraryTests(unittest.TestCase):
    def test_missing_downloads_remain_visible_but_disabled(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(library,'ASSET_ROOT',Path(tmp)):
            rows=library.entries()
            self.assertEqual([r['id'] for r in rows],['ayane','2b'])
            self.assertFalse(any(r['available'] for r in rows))
    def test_browser_exposes_replacement_action(self):
        calls=[]
        model=SimpleNamespace(entries=[dict(id='ayane',name='Ayane',available=True,replacement='ayane',reason='local')],busy=False,summary=lambda:'',select_replacement=calls.append)
        view=BrowserView(SimpleNamespace(_check=lambda:None),model)
        frame=view.render();frame=view.activate(frame.revision,100)
        self.assertTrue(any(c.token==8 and c.enabled for c in frame.controls))
        view.activate(frame.revision,8)
        self.assertEqual(calls,['ayane'])

if __name__=='__main__':unittest.main()
