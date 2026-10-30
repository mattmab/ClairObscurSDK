"""Readiness changes during dependency reads must block either original graph."""
import unittest

from expedition33 import simon_original,paired_original
from expedition33 import _paired_phase_observation
from expedition33.values import StoredMap
from test_simon_original import Scope,Provider as SimonProvider
from test_paired_original import Provider as PairProvider


class FinalReadinessTests(unittest.TestCase):
    def scenarios(self):
        return ((simon_original,SimonProvider,'SimonIntro'),
                (paired_original,PairProvider,_paired_phase_observation.CINEMATIC_ID))

    def prepare(self,module,provider):
        prepared = module.prepare(Scope(),disposable_test=True,_provider=provider)
        self.addCleanup(prepared.close)
        return prepared

    def change_during_dependencies(self,provider,change):
        original = provider.dependencies
        def read(*args):
            result = original(*args)
            change()
            return result
        provider.dependencies = read

    def test_other_action_becoming_active_during_reads_blocks_dispatch(self):
        for module,constructor,_ in self.scenarios():
            with self.subTest(adapter=module.__name__):
                provider = constructor()
                prepared = self.prepare(module,provider)
                self.change_during_dependencies(provider,lambda:setattr(provider.monitor_value,'idle',False))
                with self.assertRaisesRegex(RuntimeError,'readiness changed during final'):
                    prepared.start()
                self.assertFalse(prepared.dispatch_attempted)
                self.assertEqual(provider.invocations,0)

    def test_played_history_change_during_reads_uses_original_policy(self):
        for module,constructor,cinematic_id in self.scenarios():
            with self.subTest(adapter=module.__name__):
                provider = constructor()
                prepared = self.prepare(module,provider)
                self.change_during_dependencies(provider,
                    lambda:provider.current_history.update(history=StoredMap({cinematic_id:True})))
                prepared.start()
                self.assertTrue(prepared.dispatch_attempted)
                self.assertEqual(provider.invocations,1)
                self.assertTrue(provider.current_history['history'].items[cinematic_id])

    def test_unreadable_history_during_reads_blocks_dispatch(self):
        for module,constructor,_ in self.scenarios():
            with self.subTest(adapter=module.__name__):
                provider = constructor()
                prepared = self.prepare(module,provider)
                self.change_during_dependencies(provider,
                    lambda:provider.current_history.update(decoded=False))
                with self.assertRaisesRegex(RuntimeError,'Readable'):
                    prepared.start()
                self.assertFalse(prepared.dispatch_attempted)
                self.assertEqual(provider.invocations,0)

    def test_slot_change_during_reads_blocks_dispatch(self):
        for module,constructor,_ in self.scenarios():
            with self.subTest(adapter=module.__name__):
                provider = constructor()
                prepared = self.prepare(module,provider)
                self.change_during_dependencies(provider,
                    lambda:provider.current_history.update(selected_slot=9))
                with self.assertRaisesRegex(RuntimeError,'history/readiness changed during final'):
                    prepared.start()
                self.assertFalse(prepared.dispatch_attempted)
                self.assertEqual(provider.invocations,0)

    def test_unchanged_readiness_is_observed_again_before_one_shot_dispatch(self):
        for module,constructor,_ in self.scenarios():
            with self.subTest(adapter=module.__name__):
                provider = constructor()
                prepared = self.prepare(module,provider)
                prepared.start()
                self.assertEqual(provider.monitor_object.observe.call_count,3)
                self.assertTrue(prepared.dispatch_attempted)
                self.assertEqual(provider.invocations,1)
                with self.assertRaisesRegex(RuntimeError,'one-shot'):
                    prepared.start()
                self.assertEqual(provider.invocations,1)
