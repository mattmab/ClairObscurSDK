import unittest
from types import SimpleNamespace
from weakref import WeakSet
from unittest.mock import patch

from expedition33.pause_menu import PauseMenuEntry


class PauseOrderTests(unittest.TestCase):
    def entry(self, label, grid):
        entry = PauseMenuEntry(SimpleNamespace(pid=123), None, label=label)
        entry.grid = grid
        entry.state = 'building'
        return entry

    def test_both_attachment_orders_and_rebuilds(self):
        for labels in (('Mods', 'Map Travel'), ('Map Travel', 'Mods')):
            with self.subTest(labels=labels), patch.object(PauseMenuEntry, '_entries', WeakSet()):
                grid = object()
                first = self.entry(labels[0], grid)
                first.row = first._choose_row([0, 1, 2, 3])
                first.state = 'attached'
                second = self.entry(labels[1], grid)
                second.row = second._choose_row([0, 1, 2, 3, first.row])
                second.state = 'attached'
                self.assertEqual({first.label: first.row, second.label: second.row},
                                 {'Mods': 4, 'Map Travel': 5})
                first.state = 'closed'
                replacement = self.entry(first.label, grid)
                self.assertEqual(replacement._choose_row([0, 1, 2, 3, second.row]), first.row)

    def test_new_world_uses_its_own_grid_boundary(self):
        with patch.object(PauseMenuEntry, '_entries', WeakSet()):
            old = self.entry('Mods', object())
            old._choose_row([0, 1, 2, 3])
            old.state = 'attached'
            new = self.entry('Map Travel', object())
            self.assertEqual(new._choose_row([0, 1, 2]), 4)


if __name__ == '__main__':
    unittest.main()
