from types import SimpleNamespace as N
from unittest.mock import patch
import unittest
from expedition33 import release_startup as m


class StartupTests(unittest.TestCase):
    def test_core_menu_waits_for_current_pause_widget_not_gameplay_pawn(self):
        for pause, expected in ((None, False), (N(class_name='OtherWidget'), False),
                                (N(class_name='WBP_PauseMenu_C'), True)):
            catalog=N(by_index={1: object(), 2: object()})
            with self.subTest(pause=pause), patch.object(m, 'ReadBatch'), patch.object(m, 'controller_context', return_value={'controller': (7, 1, 2, 3)}), patch.object(m, 'capture_selected', return_value=catalog), patch.object(m, 'read_values', return_value=N(types={(2,'PauseMenuWidget'): 'ObjectProperty'})), patch.object(m, 'read_object_reference', return_value=(pause, catalog)) as read:
                self.assertEqual(m.menu_ready(7), expected)
                read.assert_called_once_with(catalog, catalog.by_index[1], catalog.by_index[2], 'PauseMenuWidget', project=True)

    def test_title_screen_is_not_ready_for_saved_gameplay_mods(self):
        for pawn, expected in ((None, False), (N(class_name='SpectatorPawn'), False),
                               (N(class_name='BP_jRPG_Character_World_C'), True),
                               (N(class_name='BP_jRPG_Character_WorldMap_pawn_C'), True)):
            catalog=N(by_index={1: object(), 2: object()})
            with self.subTest(pawn=pawn), patch.object(m, 'ReadBatch'), patch.object(m, 'controller_context', return_value={'controller': (7, 1, 2, 3)}), patch.object(m, 'capture_selected', return_value=catalog), patch.object(m, 'read_values', return_value=N(types={(2,'Pawn'): 'ObjectProperty'}, values={}, errors={(2,'Pawn'): 'Reference changed since catalog; refresh required'})), patch.object(m, 'read_object_reference', return_value=(pawn, catalog)) as read:
                self.assertEqual(m.gameplay_ready(7), expected)
                read.assert_called_once_with(catalog, catalog.by_index[1], catalog.by_index[2], 'Pawn')


if __name__ == '__main__':
    unittest.main()
