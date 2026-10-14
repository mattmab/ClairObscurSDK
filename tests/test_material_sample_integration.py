import unittest
from types import SimpleNamespace
from unittest.mock import patch
from mods.CatalogModels.mod import Mod

class SampleIntegrationTests(unittest.TestCase):
    def begin(self,data):
        mod=Mod();mod.session=SimpleNamespace(pid=1)
        with patch('mods.CatalogModels.mod.SessionScope'),patch('mods.CatalogModels.mod.Tetrahedron'),patch('mods.CatalogModels.mod.capture_matching'):
            mod._begin(data)
        return mod
    def test_bone_mapping_does_not_become_sample_map(self):
        mod=self.begin(dict(skin='skin.bin',mapping={'pelvis':5},id='2b',sections=[],vertices=3))
        self.assertEqual(mod.last['samples'],[])
        self.assertEqual(mod.sample_mapping,[])
        self.assertEqual(mod.skin_path,'skin.bin')
    def test_lit_batch_retains_candidate_numbers(self):
        mod=self.begin(dict(id='lit-materials-1',sections=[],vertices=3,batch=1,sample_mapping=[{'id':2}]))
        self.assertEqual(mod.last['samples'],[2])
        self.assertEqual(mod.last['batch'],1)
if __name__=='__main__':unittest.main()
