import hashlib,importlib.util,json,struct,tempfile,unittest,zlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('catalog_models_reader',ROOT/'mods/CatalogModels/catalog.py')
catalog=importlib.util.module_from_spec(spec);spec.loader.exec_module(catalog)

class CatalogTests(unittest.TestCase):
    def test_quarantined_entries_are_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            path=root/'catalog.json';data=json.loads(path.read_text())
            data['assets'].append(dict(id='quarantined',state='QUARANTINED',path='../never-read'))
            path.write_text(json.dumps(data))
            self.assertEqual([row['id'] for row in catalog.entries(root)],['test'])
            with self.assertRaisesRegex(ValueError,'unavailable'):
                catalog.prepare(root,'quarantined',root/'output')
    def fixture(self,root,back=False):
        buffers={};payload=bytearray()
        def array(key,fmt,values,shape):
            raw=struct.pack('<'+fmt*len(values),*values);block=zlib.compress(raw)
            buffers[key]=dict(offset=len(payload),compressed_bytes=len(block),bytes=len(raw),dtype='<'+fmt+str(struct.calcsize(fmt)),shape=shape,sha256=hashlib.sha256(raw).hexdigest())
            payload.extend(block);return {'buffer':key}
        section=dict(positions=array('p','f',[0,0,0,1,0,0,0,1,0],[3,3]),normals=array('n','f',[0,0,1]*3,[3,3]),
                     uv=array('uv','f',[0,0,1,0,0,1],[3,2]),indices=array('i','i',[0,1,2],[3]),material=0)
        sections=[section]
        if back:
            sections.append(dict(section,normals=array('back_n','f',[0,0,-1]*3,[3,3]),indices=array('back_i','i',[0,2,1],[3])))
        folder=root/'asset';folder.mkdir();(folder/'source.bin').write_bytes(payload)
        manifest=dict(schema='normalized-asset/1',asset=dict(uvConvention='prepared-runtime-v1',parts=[dict(sections=sections)],materials=[{}],clips=[{'buffer':'MUST_NOT_LOAD_ANIMATION'}]),
                      buffers=buffers,payload=dict(path='source.bin',bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest()),resources={})
        (folder/'manifest.json').write_text(json.dumps(manifest))
        (root/'catalog.json').write_text(json.dumps({'assets':[dict(id='test',path='asset',state='READY')]}))
        return manifest,folder
    def test_baseline_preserves_source_sections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root,back=True)
            result=catalog.prepare(root,'test',root/'output')
            self.assertEqual(len(result['sections']),2)
            self.assertEqual(result['vertices'],6)

    def test_static_import_never_loads_clips(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.fixture(root)
            result=catalog.prepare(root,'test',root/'output')
            self.assertEqual(result['vertices'],3)
            data=Path(result['sections'][0]['mesh']).read_bytes()
            self.assertEqual(struct.unpack_from('<8sII',data),(b'E33MESH1',3,3))
    def test_hash_and_path_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,folder=self.fixture(root)
            with self.assertRaises(ValueError):catalog.inside(root,'../outside')
            (folder/'source.bin').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'Payload size'):catalog.prepare(root,'test',root/'output')
    def test_decompression_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);m,folder=self.fixture(root)
            m['buffers']['p']['shape']=[2,3]
            (folder/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError,'Buffer bounds'):catalog.prepare(root,'test',root/'output')
