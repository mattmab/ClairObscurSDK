from contextlib import nullcontext
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError
from expedition33._npc_encounter_preparation import ARENA_CLASS, bind_original_arena


class SelectedArenaBindingTests(unittest.TestCase):
    def setUp(self):
        self.world = N(index=1, serial=3, address=100, class_name='World')
        self.original = N(index=2, serial=4, address=200, class_index=90, object_flags=0x10)
        self.arena = N(index=3, serial=5, address=300, class_index=2, object_flags=0)
        self.library = N(index=4, serial=6, address=400, class_index=91, object_flags=0x10)
        self.to_soft = N(index=5, serial=7, address=500, class_index=92, object_flags=0)
        self.from_soft = N(index=6, serial=8, address=600, class_index=92, object_flags=0)
        self.identity = (3, 5, 300)
        paths = {2: ARENA_CLASS, 4: '/Script/Engine.Default__KismetSystemLibrary',
                 5: '/Script/Engine.KismetSystemLibrary:Conv_ObjectToSoftObjectReference',
                 6: '/Script/Engine.KismetSystemLibrary:Conv_SoftObjectReferenceToObject'}
        objects = [self.original, self.arena, self.library, self.to_soft, self.from_soft]
        self.catalog = N(objects=objects, by_index={obj.index: obj for obj in objects},
                         classes={2: self.original}, ancestors=lambda i: (i,),
                         outer_chain=lambda obj: (self.world,), path_name=lambda obj: paths.get(obj.index, 'arena'))
        self.catalog.with_observations = lambda other: self.catalog
        self.context = dict(world=(7, 1, 3, 100), controller=(7, 20, 1, 2000), world_path='World')
        self.scope = N(pid=7, _session=N(_transport=N(_executable='reader')))
        self.owner = N(bind_arena=Mock(return_value='native-ACK'))
        self.observer = Mock(return_value=self.context)

    def run_bind(self,*,retained=False):
        with (patch('expedition33._npc_encounter_preparation.ReadBatch', return_value=nullcontext()),
              patch('expedition33.cinematics.controller_anchor.context_observer', return_value=self.observer),
              patch('expedition33._npc_encounter_preparation.capture_selected', return_value=self.catalog) as selected,
              patch('expedition33._npc_encounter_preparation.capture_matching', return_value=self.catalog) as metadata,
              patch('expedition33._enemy_arenas.observe_battle_arenas', side_effect=AssertionError('No arena enumeration'))):
            result = bind_original_arena(self.scope, self.owner, self.identity,
                metadata_catalog=self.catalog if retained else None)
            selected.assert_called_once_with(7, (self.identity, (1, 3, 100)))
            if retained:metadata.assert_not_called()
            else:metadata.assert_called_once_with(7, names=('Default__KismetSystemLibrary',
                'Conv_ObjectToSoftObjectReference', 'Conv_SoftObjectReferenceToObject'))
            return result

    def test_exact_arena_uses_selected_read_and_brackets_native_binding(self):
        self.assertEqual(self.run_bind(), 'native-ACK')
        self.assertEqual(self.observer.call_count, 2)
        self.owner.bind_arena.assert_called_once_with((self.arena, self.library, self.to_soft, self.from_soft))

    def test_retained_function_selection_keeps_fresh_arena_and_context_checks(self):
        self.assertEqual(self.run_bind(retained=True),'native-ACK')
        self.assertEqual(self.observer.call_count,2)
        self.owner.bind_arena.assert_called_once_with((self.arena,self.library,self.to_soft,self.from_soft))

    def test_retained_functions_do_not_admit_foreign_world_or_changed_context(self):
        self.world.serial=99
        with self.assertRaisesRegex(ValueError,'current world'):self.run_bind(retained=True)
        self.owner.bind_arena.assert_not_called()
        self.world.serial=3
        self.observer.side_effect=[self.context,dict(self.context,controller=(7,20,99,2000))]
        with self.assertRaisesRegex(RuntimeError,'World/controller changed'):self.run_bind(retained=True)
        self.owner.bind_arena.assert_not_called()

    def test_foreign_world_and_reused_identity_are_rejected_before_binding(self):
        for mutate in (lambda: setattr(self.world, 'serial', 99), lambda: setattr(self.arena, 'serial', 99),
                       lambda: setattr(self.arena, 'address', 999)):
            with self.subTest(mutate=mutate):
                self.setUp(); mutate()
                with self.assertRaisesRegex(ValueError, 'current world'):
                    self.run_bind()
                self.owner.bind_arena.assert_not_called()

    def test_retiring_arena_is_rejected_before_binding(self):
        for flags in (0x10, 0x20, 0x8000, 0x10000, 0x40000000):
            with self.subTest(flags=flags):
                self.arena.object_flags = flags
                with self.assertRaises(ValueError):
                    self.run_bind()
                self.owner.bind_arena.assert_not_called()

    def test_world_or_controller_change_rejects_after_preparation(self):
        for change in (dict(world=(7, 1, 9, 100)), dict(controller=(7, 20, 9, 2000))):
            with self.subTest(change=change):
                self.observer.side_effect = [self.context, dict(self.context, **change)]
                with self.assertRaisesRegex(RuntimeError, 'World/controller changed'):
                    self.run_bind()
                self.owner.bind_arena.assert_not_called()

    def test_selected_read_failure_does_not_dispatch(self):
        with (patch('expedition33._npc_encounter_preparation.ReadBatch', return_value=nullcontext()),
              patch('expedition33.cinematics.controller_anchor.context_observer', return_value=self.observer),
              patch('expedition33._npc_encounter_preparation.capture_selected', side_effect=RuntimeQueryError('stale'))):
            with self.assertRaises(RuntimeQueryError):
                bind_original_arena(self.scope, self.owner, self.identity)
        self.owner.bind_arena.assert_not_called()

    def test_unknown_native_ack_propagates_without_replay(self):
        self.owner.bind_arena.side_effect = RuntimeError('Unknown native acknowledgement')
        with self.assertRaisesRegex(RuntimeError, 'Unknown native acknowledgement'):
            self.run_bind()
        self.assertEqual(self.owner.bind_arena.call_count, 1)


if __name__ == '__main__':
    unittest.main()
