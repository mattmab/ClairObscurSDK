"""Public module metadata must be usable before world activation."""
from pathlib import Path
import tempfile
from unittest import TestCase
from unittest.mock import patch
from expedition33 import sdk
from expedition33.mods import ModLoader

PUBLIC = "SDKManagement SceneEditor EnemySpawner WorldBuilderMapLoader Cinematics E33WorldBuilder ContinentFlight MapTravel PictoEditor Statistics CatalogModels IntrospectionHarness LiveObjectViewer ConsoleExample KeybindExample ExampleMod ManagementExample".split()

class PublicMetadataStartupTests(TestCase):
    def test_opted_in_public_metadata_never_creates_session_or_queries_process(self):
        root=Path(__file__).resolve().parents[1]/"mods"
        with tempfile.TemporaryDirectory() as temporary:
            game=Path(temporary)
            (game/'Manifest_UFSFiles_Win64.txt').write_text('Sandfall/Content/Levels/Test/Level_Test.umap\tdate\n')
            self._assert_preparation(root,game)

    def _assert_preparation(self,root,game):
        with patch("subprocess.Popen",side_effect=AssertionError("No process access during preparation")), patch.object(sdk,"Session",side_effect=AssertionError("No Session during preparation")), patch('expedition33.paths.game_root',return_value=game):
            with ModLoader(root) as loader:
                for name in PUBLIC:
                    with self.subTest(folder=name):
                        self.assertTrue(loader.prepare_startup(name,sdk_version="test"))
                        record=loader._loaded[name]
                        self.assertIsNone(record[2],"Preparation must not create an enabled scope")
                self.assertEqual(len(loader.registry.views()),len(PUBLIC))
                self.assertFalse(any(view["enabled"] for view in loader.registry.views()))
