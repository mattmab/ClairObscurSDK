import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock
p=Path(__file__).resolve().parents[1]/'src/expedition33/process_console.py'
spec=importlib.util.spec_from_file_location('expedition33._startup_state_candidate',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class ConsoleStartupStateTests(unittest.TestCase):
    def setUp(self):
        self.console=N(_enabled=True,write=Mock())
        loader=N(status=lambda:(),discover=lambda:(),_startup_preparations={},_preparation_failures={},
            registry=N(_startup_progress=dict(finished=False)))
        self.info=m.StartupConsoleInfo(self.console,loader,'0.1.0-test')
    def text(self):return ''.join(call.args[0] for call in self.console.write.call_args_list)
    def test_initializing_then_observed_title_emits_once_without_count_change(self):
        self.info.poll(title_ready=None)
        self.info.poll(title_ready=None)
        for _ in range(20):self.info.poll(title_ready=True)
        self.assertEqual(self.text().count('Game state: INITIALIZING'),1)
        self.assertEqual(self.text().count('Game state: TITLE_SCREEN'),1)
        self.assertEqual(self.text().count('Title screen detected'),1)
        self.assertEqual(self.text().count('Mods: prepared'),1)
    def test_initial_title_is_not_printed_again_or_demoted_by_uncertainty(self):
        self.info.poll(title_ready=True)
        for ready in (None,False,True,None,True):self.info.poll(title_ready=ready)
        self.assertEqual(self.text().count('Game state: TITLE_SCREEN'),1)
        self.assertNotIn('Game state: INITIALIZING',self.text())
    def test_world_readiness_wins_stale_title_flag_and_emits_once(self):
        self.info.poll(title_ready=None)
        self.info.poll(title_ready=True)
        for _ in range(20):self.info.poll(title_ready=True,world_active=True)
        self.assertEqual(self.text().count('Game state: WORLD_READY'),1)
        self.assertEqual(self.text().count('Game state: TITLE_SCREEN'),1)
    def test_initial_world_does_not_claim_title_from_old_copy(self):
        self.info.poll(title_ready=True,world_active=True)
        self.assertIn('Game state: WORLD_READY',self.text())
        self.assertNotIn('Game state: TITLE_SCREEN',self.text())

if __name__=='__main__':unittest.main()
