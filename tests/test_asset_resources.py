import hashlib,json,tempfile,unittest
from pathlib import Path
from expedition33 import asset_resources as resources

class AssetResourcesTests(unittest.TestCase):
    def fixture(self,root):
        entries=[]
        for i,ext in enumerate(('pak','ucas','utoc')):
            data=(ext+' resource').encode();name='chunk-'+str(i).zfill(3)+'.bin'
            (root/name).write_bytes(data);digest=hashlib.sha256(data).hexdigest()
            entries.append(dict(name='sdk_Test_P.'+ext,size=len(data),sha256=digest,chunks=[dict(path=name,size=len(data),sha256=digest)]))
        path=root/'assets.json';path.write_text(json.dumps(dict(schema=1,id='test',packages=['/Game/SDK/Test'],containers=entries)))
        (root/'Sandfall/Content/Paks').mkdir(parents=True)
        return path,root/'Sandfall/Content/Paks'

    def test_install_is_idempotent_and_never_replaces_different_container(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest,dest=self.fixture(root)
            self.assertTrue(resources.install(manifest,game_root=root))
            self.assertFalse(resources.install(manifest,game_root=root))
            target=dest/'sdk_Test_P.pak';target.write_bytes(b'existing')
            with self.assertRaises(ValueError):resources.install(manifest,game_root=root)
            self.assertEqual(target.read_bytes(),b'existing')

    def test_all_chunks_are_verified_before_any_container_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);manifest,dest=self.fixture(root)
            (root/'chunk-002.bin').write_bytes(b'corrupt')
            with self.assertRaises(ValueError):resources.install(manifest,game_root=root)
            self.assertEqual(list(dest.iterdir()),[])
