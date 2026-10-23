import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.cinematics import history

SOURCE = Path(__file__).resolve().parents[1] / 'src/expedition33/release_startup.py'
spec = importlib.util.spec_from_file_location('expedition33._startup_candidate', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
history_spec = importlib.util.spec_from_file_location('projected_history_candidate',
    SOURCE.parent/'cinematics/history.py')
projected_history = importlib.util.module_from_spec(history_spec)
history_spec.loader.exec_module(projected_history)
m.anchor = projected_history.anchor


def obj(index, cls):
    return N(pid=7, index=index, serial=1, address=0x10000+index*0x100,
             class_name=cls, object_flags=0)


class AnchorCatalog:
    pid = 7
    def __init__(self, *, missing=None, world_index=3):
        self.engine = obj(1, 'GameEngine')
        self.viewport = obj(2, 'CustomGameViewportClient')
        self.world = obj(world_index, 'World')
        self.gi = obj(4, 'BP_jRPG_GI_Custom_C')
        self.missing = missing
        self.by_index = {10: obj(10, 'Class'), 11: obj(11, 'Class'), 12: obj(12, 'Class')}
    def select(self, name):
        assert name == 'GameEngine'
        return () if self.missing == 'engine' else (self.engine,)
    def find_class(self, name):
        return N(index={'Engine': 10, 'GameViewportClient': 11, 'World': 12}[name])
    def reference(self, catalog, owner, cls, field):
        value = {'GameViewport': self.viewport, 'World': self.world,
                 'OwningGameInstance': self.gi}[field]
        if field == self.missing: value = None
        return value, self


class BootstrapTests(unittest.TestCase):
    def ready(self, first, second=None):
        second = first if second is None else second
        def read(catalog, owner, cls, field, *, project=False):
            self.assertTrue(project)
            return catalog.reference(catalog, owner, cls, field)
        with patch.object(m, 'ReadBatch') as batch, \
             patch('expedition33.catalog.capture_matching', side_effect=(first, second)) as capture, \
             patch.object(projected_history, 'read_object_reference', side_effect=read), \
             patch.object(m, 'controller_context', side_effect=AssertionError('no controller')):
            result = m.bootstrap_ready(7)
            batch.assert_called_once_with(7)
            return result, capture.call_count

    def test_title_gi_accepted_without_controller_pawn_or_save(self):
        self.assertEqual(self.ready(AnchorCatalog()), (True, 2))

    def test_each_null_anchor_rejected_without_second_observation(self):
        for missing in ('engine', 'GameViewport', 'World', 'OwningGameInstance'):
            with self.subTest(missing=missing):
                self.assertEqual(self.ready(AnchorCatalog(missing=missing)), (False, 1))

    def test_world_identity_change_rejected(self):
        self.assertEqual(self.ready(AnchorCatalog(), AnchorCatalog(world_index=5)), (False, 2))

    def test_each_identity_member_checked(self):
        for member in ('engine', 'viewport', 'world', 'gi'):
            second = AnchorCatalog()
            getattr(second, member).serial += 1
            with self.subTest(member=member):
                self.assertFalse(self.ready(AnchorCatalog(), second)[0])

    def test_wrong_game_instance_is_not_ready(self):
        first = AnchorCatalog()
        first.gi.class_name = 'OtherGameInstance'
        self.assertEqual(self.ready(first), (False, 1))

    def test_decode_errors_visible_and_not_retried(self):
        error = RuntimeQueryError('Malformed native property payload')
        with patch.object(m, 'ReadBatch'), \
             patch('expedition33.catalog.capture_matching', side_effect=error) as capture:
            with self.assertRaises(RuntimeQueryError) as raised:
                m.bootstrap_ready(7)
            self.assertIs(raised.exception, error)
            self.assertEqual(capture.call_count, 1)

    def test_catalog_wrong_process_visible(self):
        first = AnchorCatalog()
        first.pid = 8
        with self.assertRaisesRegex(RuntimeError, 'process mismatch'):
            self.ready(first)

    def test_known_identity_race_not_ready(self):
        with patch.object(m, 'ReadBatch'), patch('expedition33.catalog.capture_matching',
                side_effect=RuntimeQueryError('Object identity changed or belongs to another process')):
            self.assertFalse(m.bootstrap_ready(7))


if __name__ == '__main__': unittest.main()
