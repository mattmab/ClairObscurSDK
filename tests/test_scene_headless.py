"""Story consumers use the bundled scene engine with no editor activation."""
import importlib,subprocess,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.scene_packs import Playback,register_provider,_provider
from expedition33.scene_runtime.runtime import Runtime
from expedition33.scene_runtime.scene import sample,validate

WORLD='/Game/Test/Test.Test'

class HeadlessSceneTests(unittest.TestCase):
    def test_playback_constructs_without_an_editor_provider(self):
        session=N();scope=N(_check=lambda:None,_session=session,_reference_owners=[])
        playback=Playback(scope,sample(WORLD))
        self.assertIsInstance(playback.runtime,Runtime)
        self.assertIs(playback.runtime.session,scope)
        self.assertEqual(session._scene_pack_provider,(Runtime,validate))
        self.assertFalse(playback.started)
        self.assertEqual(scope._reference_owners,[playback])
        self.assertTrue(playback.close())

    def test_editor_registration_of_shared_provider_preserves_live_owner(self):
        session=N();scope=N(_check=lambda:None,_session=session,_reference_owners=[])
        playback=Playback(scope,sample(WORLD))
        register_provider(session,Runtime,validate)
        self.assertIs(session._scene_pack_playbacks[0],playback)
        with self.assertRaisesRegex(RuntimeError,'previous provider'):
            register_provider(session,Mock(),validate)
        self.assertTrue(playback.close())
        alternate=Mock();register_provider(session,alternate,validate)
        self.assertEqual(_provider(session),(alternate,validate))

    def test_standalone_process_loads_only_sdk_scene_modules(self):
        source=Path(__file__).resolve().parents[1]/'src'
        code='''
import sys
sys.path.insert(0,sys.argv[1])
from types import SimpleNamespace as N
from expedition33.scene_packs import Playback
from expedition33.scene_runtime.scene import sample
scope=N(_check=lambda:None,_session=N(),_reference_owners=[])
p=Playback(scope,sample('/Game/Test/Test.Test'))
assert p.runtime.__class__.__module__=='expedition33.scene_runtime.runtime'
assert not any('SceneEditor' in k or 'scene_editor' in k for k in sys.modules)
assert not any(k.endswith('.hud') or k.endswith('.timeline') or k.endswith('.view') for k in sys.modules if k.startswith('expedition33.scene_runtime'))
assert p.close()
'''
        with tempfile.TemporaryDirectory() as cwd:
            result=subprocess.run([sys.executable,'-I','-c',code,str(source)],cwd=cwd,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_editor_module_aliases_share_runtime_and_mutable_palette(self):
        # Test the compatibility modules using the real package's import tree.
        from test_runtime_scene_editor import package
        old_runtime=importlib.import_module(package.__name__+'.runtime')
        old_scene=importlib.import_module(package.__name__+'.scene')
        old_palette=importlib.import_module(package.__name__+'.palette')
        from expedition33.scene_runtime import runtime,scene,palette
        self.assertIs(old_runtime,runtime)
        self.assertIs(old_scene,scene)
        self.assertIs(old_palette,palette)
        self.assertIs(old_palette.ANIMATIONS,palette.ANIMATIONS)

if __name__=='__main__':unittest.main()
