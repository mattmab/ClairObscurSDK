"""Run SDK and standalone World Builder tests from the repository runtime."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'tests'), str(ROOT / 'scripts')]
temporary = ROOT / 'build/test-temp'
temporary.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(temporary)

if __name__ == '__main__':
    success = True
    for folder in ('tests', 'tests/world_builder'):
        suite = unittest.TestLoader().discover(str(ROOT / folder))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        success &= result.wasSuccessful()
    raise SystemExit(not success)
