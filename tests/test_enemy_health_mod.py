"""Formatting, enemy ownership, visibility and cleanup contracts of Enemy HP."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


health = module('enemy_health_mod_test', 'mods/EnemyHealth/mod.py')
ui = module('enemy_health_ui_test', 'mods/EnemyHealth/ui.py')


class HealthTests(unittest.TestCase):
    def test_bars_can_prepare_during_intro_but_not_after_end_flow(self):
        self.assertTrue(health.may_prepare_bars(dict(IsBattleInitialized=False,
                                                   HasBattleStartedEndFlow=False)))
        self.assertFalse(health.may_prepare_bars(dict(IsBattleInitialized=True,
                                                    HasBattleStartedEndFlow=True)))
        self.assertFalse(health.may_prepare_bars({}))

    def test_real_hp_format_handles_fractional_dead_and_large_boss_values(self):
        cases = [(33727., '33,727 HP'), (1.01, '2 HP'), (0., '0 HP'),
                 (-20., '0 HP'), (115905000000., '115,905,000,000 HP')]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(health.hp_text(value), expected)
        for invalid in (None, True, '100', float('nan'), float('inf')):
            with self.subTest(invalid=invalid):
                self.assertEqual(health.hp_text(invalid), '')

    def test_enemy_class_ancestry_excludes_allies_and_accepts_boss_subclasses(self):
        catalog = SimpleNamespace(by_index={3: SimpleNamespace(class_index=4)},
            classes={4: SimpleNamespace(name='Boss_C'),
                     5: SimpleNamespace(name=health.ENEMY)}, ancestors=lambda _: (4, 5))
        stats = SimpleNamespace(outer_index=3)
        self.assertTrue(health.is_enemy(catalog, stats))
        catalog.ancestors = lambda _: (4,)
        self.assertFalse(health.is_enemy(catalog, stats))
        self.assertFalse(health.is_enemy(catalog, SimpleNamespace(outer_index=99)))

    def test_failed_read_is_not_a_zero_hp_observation(self):
        with self.assertRaises(health.RuntimeQueryError):
            health.fields(SimpleNamespace(errors={'CurrentHP': 'identity changed'}, values={}))

    def test_world_retirement_ack_requires_successful_label_removal(self):
        mod = health.Mod()
        owner = Mock()
        mod.labels['enemy'] = owner
        mod.revoke_world(None)
        self.assertTrue(mod.stopped)
        self.assertEqual(mod.begin_world_retirement(None), 'ack')
        owner.close.assert_called_once()
        self.assertEqual(mod.labels, {})
        self.assertEqual(mod.poll_world_retirement(None), 'ack')

    def test_cleanup_failure_keeps_the_owner_in_its_journal(self):
        mod = health.Mod()
        owner = Mock()
        owner.close.side_effect = RuntimeError('native cleanup pending')
        mod.labels['enemy'] = owner
        with self.assertRaises(RuntimeError):
            mod.begin_world_retirement(None)
        self.assertIs(mod.labels['enemy'], owner)

    def test_collector_deferral_retains_owner_until_release_is_acknowledged(self):
        mod = health.Mod()
        owner = Mock()
        owner.close.side_effect = (False, True)
        mod.labels['enemy'] = owner
        self.assertEqual(mod.begin_world_retirement(None), 'pending')
        self.assertIs(mod.labels['enemy'], owner)
        self.assertEqual(mod.poll_world_retirement(None), 'ack')
        self.assertEqual(mod.labels, {})

    def test_poll_rate_limits_discovery_and_value_reads(self):
        mod = health.Mod()
        mod.session = object()
        mod.reader = MagicMock()
        mod._discover = Mock()
        mod._update = Mock()
        with patch.object(health.time, 'monotonic', side_effect=(1., 1.01, 1.11, 1.8)):
            for _ in range(4):
                mod.poll()
        self.assertEqual(mod._discover.call_count, 3)
        self.assertEqual(mod._update.call_count, 3)

    def test_partial_label_waits_for_cleanup_without_dispatching_updates(self):
        mod = health.Mod()
        owner = Mock(ready=False)
        mod.labels['enemy'] = owner
        with patch.object(health, 'capture_selected_values') as capture:
            mod._update()
        capture.assert_not_called()
        owner.update.assert_not_called()

    def test_disable_waits_for_read_only_discovery_worker_to_exit(self):
        mod = health.Mod()
        monitor = Mock()
        monitor.close.side_effect = (False, True)
        mod.monitor = monitor
        mod.reader = Mock()
        reader = mod.reader
        self.assertFalse(mod.prepare_disable())
        self.assertIs(mod.monitor, monitor)
        reader.close.assert_called_once()
        self.assertTrue(mod.prepare_disable())
        self.assertIsNone(mod.monitor)

    def test_missing_discovery_sample_is_not_a_combat_end_signal(self):
        mod = health.Mod()
        mod.monitor = Mock()
        mod.monitor.snapshot.return_value = None
        owner = Mock()
        mod.labels['enemy'] = owner
        mod._discover()
        owner.close.assert_not_called()


class LabelTests(unittest.TestCase):
    def test_overlay_slot_setters_never_enter_widget_only_batch_dispatch(self):
        owner = self.owner()
        owner.scope = SimpleNamespace(_session=object())
        with patch('expedition33._ui_batch.extended_layout_available', return_value=True), \
                patch('expedition33._ui_batch.invoke_setters') as batch:
            owner._setters(((object(), 'OverlaySlot', 'SetHorizontalAlignment',
                             {'InHorizontalAlignment':1}),))
        batch.assert_not_called()
        owner._call.assert_called_once()

    def owner(self):
        owner = ui.HealthLabel.__new__(ui.HealthLabel)
        owner.label = object()
        owner.last = None
        owner._call = MagicMock()
        owner._enum = Mock(side_effect=lambda name, value: ('typed', name, value))
        return owner

    def test_visibility_and_opacity_follow_the_bar_without_intercepting_input(self):
        for original, expected in ((0, 3), (1, 1), (2, 2), (3, 3), (4, 3)):
            owner = self.owner()
            owner.update('9,000 HP', original, .25)
            calls = owner._call.call_args_list
            visibility = next(c.kwargs['InVisibility'] for c in calls if c.args[2] == 'SetVisibility')
            self.assertEqual(visibility, ('typed', 'ESlateVisibility', expected))
            opacity = next(c.kwargs['InOpacity'] for c in calls if c.args[2] == 'SetRenderOpacity')
            self.assertEqual(opacity, .25)

    def test_unchanged_hp_does_not_repeat_text_setters(self):
        owner = self.owner()
        owner.update('3 HP', 3, 1.)
        owner._call.reset_mock()
        owner.update('3 HP', 3, 1.)
        owner._call.assert_not_called()
        owner.update('2 HP', 3, 1.)
        self.assertEqual(owner._call.call_count, 1)
        self.assertEqual(owner._call.call_args.args[2], 'SetText')


if __name__ == '__main__':
    unittest.main()
