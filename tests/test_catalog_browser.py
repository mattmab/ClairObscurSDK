import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from expedition33.management import ManagementError

spec=importlib.util.spec_from_file_location('catalog_browser',Path(__file__).resolve().parents[1]/'mods/CatalogModels/browser.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class BrowserTests(unittest.TestCase):
    def model(self):
        self.calls=[]
        return SimpleNamespace(entries=[dict(id=str(i),name='Model'+str(i),available=True,reason='unverified') for i in range(17)],
            busy=False,summary=lambda:'Idle',spawn=lambda key:self.calls.append(('spawn',key)),destroy=lambda:self.calls.append(('destroy',None)))
    def test_select_spawn_and_stale_control(self):
        model=self.model();v=m.BrowserView(SimpleNamespace(_check=lambda:None),model)
        frame=v.render();detail=v.activate(frame.revision,100)
        self.assertEqual(v.selected,'0');self.assertTrue(any(c.token==3 for c in detail.controls))
        v.activate(detail.revision,3);self.assertEqual(self.calls,[('spawn','0')])
        with self.assertRaises(ManagementError):v.activate(detail.revision,3)
    def test_pagination_and_busy_spawn_guard(self):
        model=self.model();v=m.BrowserView(SimpleNamespace(_check=lambda:None),model)
        frame=v.render();self.assertEqual(frame.pages,3);self.assertLessEqual(len(frame.controls),12)
        frame=v.activate(frame.revision,2);self.assertEqual(frame.page,1)
        frame=v.activate(frame.revision,106);model.busy=True;frame=v.render()
        with self.assertRaises(ManagementError):v.activate(frame.revision,3)
        v.activate(frame.revision,5);self.assertEqual(self.calls,[('destroy',None)])
    def test_close_keeps_model_owned(self):
        model=self.model();v=m.BrowserView(SimpleNamespace(_check=lambda:None),model)
        frame=v.render();closed=v.activate(frame.revision,7)
        self.assertTrue(closed.closed);self.assertEqual(self.calls,[])
