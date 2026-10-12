import runpy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

class DetachedCinematicProbeTests(unittest.TestCase):
    def test_reflected_keys_use_owner_index_not_name(self):
        scripts=Path(__file__).resolve().parents[1]/'scripts'
        sys.path.insert(0,str(scripts))
        try: select=runpy.run_path(str(scripts/'verify_detached_cinematic_component.py'))['selected_values']
        finally: sys.path.pop(0)
        values=SimpleNamespace(values={(60350,'IsPlayingCinematic'):False,
            (7,'IsPlayingCinematic'):True,('BP_CinematicSystem_C','IsPlayingCinematic'):True})
        self.assertEqual(select(values,60350),{'IsPlayingCinematic':False})
        self.assertEqual(select(values,99),{})
