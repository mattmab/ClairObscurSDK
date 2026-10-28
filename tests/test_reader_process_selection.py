"""Portable selection policy and native CLI rejection; no live game required."""
from pathlib import Path
import json
import subprocess
import unittest

BUILD = Path(__file__).resolve().parents[1] / 'build/reader-pid-selection'


class ReaderProcessSelectionTests(unittest.TestCase):
    def test_native_explicit_and_ambiguous_selection_fixture(self):
        executable = BUILD / 'reader_process_selection_fixture.exe'
        if not executable.exists():
            self.skipTest('Build reader process selection fixture first')
        result = subprocess.run([str(executable)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('ambiguous discovery rejection passed',result.stdout)

    def test_explicit_read_pid_rejects_zero_trailing_and_overflow_before_discovery(self):
        executable = BUILD / 'research_probe.exe'
        if not executable.exists():
            self.skipTest('Build explicit PID read-only research probe first')
        for pid in ('0','-1','10x','4294967296'):
            with self.subTest(pid=pid):
                result = subprocess.run([str(executable),'--catalog-match',pid,'c=GameEngine'],
                                        capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,'')
                self.assertEqual(json.loads(result.stderr)['message'],'READER_PID_INVALID')
