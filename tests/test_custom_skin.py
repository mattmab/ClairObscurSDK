import hashlib,json,struct,tempfile,unittest
from pathlib import Path
from mods.CatalogModels.custom_skin import prepare_custom_skin

class CustomSkinTests(unittest.TestCase):
    def fixture(self,root):
        mesh=struct.pack('<8sII',b'E33MESH1',3,3)+struct.pack('<24d',*([0,0,0,0,0,1,0,0]*3))+struct.pack('<3i',0,1,2)
        weights=(struct.pack('<If6f',0,1,0,0,0,0,0,1)+bytes(96))*3
        files={'mesh':mesh,'weights':weights,'texture':b'fixture'}
        for name,raw in files.items():(root/name).write_bytes(raw)
        manifest=dict(schema='e33-weighted-model/1',bones=[dict(name='root',parent=-1,point=[0,0,0])],sections=[dict(mesh='mesh',weights='weights',texture='texture')],hashes={k:hashlib.sha256(v).hexdigest() for k,v in files.items()})
        (root/'manifest.json').write_text(json.dumps(manifest));return manifest
    def test_target_identity_uses_current_character_bone_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p)
            rows=[dict(name='Root',index=17,parent='None',reference=(0,0,0,1,0,0,0))]
            result=prepare_custom_skin(p/'out',rows,p)
            self.assertEqual(struct.unpack_from('<I',Path(result['skin']).read_bytes(),16)[0],17)
    def test_modified_weights_are_rejected_before_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.fixture(p);(p/'weights').write_bytes(b'bad')
            rows=[dict(name='Root',index=17,parent='None',reference=(0,0,0,1,0,0,0))]
            with self.assertRaisesRegex(ValueError,'hash'):prepare_custom_skin(p/'out',rows,p)
    def test_unweighted_vertices_rejected_even_with_matching_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);m=self.fixture(p);raw=bytes(384);(p/'weights').write_bytes(raw)
            m['hashes']['weights']=hashlib.sha256(raw).hexdigest();(p/'manifest.json').write_text(json.dumps(m))
            rows=[dict(name='Root',index=17,parent='None',reference=(0,0,0,1,0,0,0))]
            with self.assertRaisesRegex(ValueError,'Non-normalized'):prepare_custom_skin(p/'out',rows,p)
