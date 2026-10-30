import io
import tempfile
import unittest
import zipfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from runtime_snapshot import verify_sources,verify_mod

class RuntimeSnapshotTests(unittest.TestCase):
    def test_caller_and_callee_must_both_match_release_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir()
            names=('src/caller.py','src/callee.py')
            blobs=(b'apply(latency=timings)',b'def apply(*,latency=None): pass')
            entries={}
            for name,data in zip(names,blobs):
                (root/name).write_bytes(data);entries['SDK/'+name]=data
            verify_sources(root,entries,names)
            entries['SDK/src/callee.py']=b'def apply(): pass'
            with self.assertRaisesRegex(ValueError,'differs from release source'):verify_sources(root,entries,names)
    def test_missing_dependency_and_extra_module_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'src').mkdir();(root/'src/a.py').write_bytes(b'a')
            for entries in ({},{'SDK/src/a.py':b'a','SDK/src/extra.py':b'x'}):
                with self.assertRaisesRegex(ValueError,'inventory'):verify_sources(root,entries,['src/a.py'])
    def test_mod_archive_must_match_source_content_and_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'mod.py').write_bytes(b'current')
            def archive(rows):
                stream=io.BytesIO()
                with zipfile.ZipFile(stream,'w') as z:
                    for name,data in rows:z.writestr(name,data)
                return stream.getvalue()
            verify_mod(root,archive([('mod.py',b'current')]),['mod.py'])
            with self.assertRaisesRegex(ValueError,'differs from release source'):
                verify_mod(root,archive([('mod.py',b'old')]),['mod.py'])
            with self.assertRaisesRegex(ValueError,'inventory'):
                verify_mod(root,archive([('mod.py',b'current'),('extra.py',b'x')]),['mod.py'])
