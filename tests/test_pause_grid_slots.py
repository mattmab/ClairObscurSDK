import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.pause_menu import PauseMenuEntry
from expedition33.values import StoredArray

class PauseGridSlotsTests(unittest.TestCase):
    def setUp(self):
        self.entry=PauseMenuEntry.__new__(PauseMenuEntry)
        self.entry.grid=N(index=20,serial=3)
        self.entry.planner=N(_catalog=object(),adopt_observations=Mock())
        self.slot=N(index=30,serial=4,address=0x10000,class_name='GridSlot',
            outer_index=20,outer_serial=3,object_flags=0)

    def read(self,array):
        catalog=object()
        values=N(values={(10,'Slots'):array})
        with patch('expedition33.pause_menu.read_values_with_references',return_value=(values,catalog)) as read:
            result=self.entry.grid_slots()
        read.assert_called_once_with(self.entry.planner._catalog,self.entry.grid,fields=('Slots',))
        self.entry.planner.adopt_observations.assert_called_once_with(catalog)
        return result

    def test_complete_owned_grid_uses_one_stored_array_read(self):
        self.assertEqual(self.read(StoredArray((self.slot,),1)),(self.slot,))

    def test_truncated_grid_rejects_without_adopting_partial_observations(self):
        with self.assertRaisesRegex(RuntimeError,'incomplete'):self.read(StoredArray((self.slot,),2))
        self.entry.planner.adopt_observations.assert_not_called()

    def test_recycled_outer_or_duplicate_slots_reject(self):
        for array in (StoredArray((self.slot,self.slot),2),StoredArray((N(**{**vars(self.slot),'outer_serial':9}),),1)):
            with self.assertRaisesRegex(RuntimeError,'ownership'):self.read(array)
        self.entry.planner.adopt_observations.assert_not_called()

    def test_unbounded_grid_rejects_before_any_native_calls(self):
        with self.assertRaisesRegex(RuntimeError,'outside bounds'):self.read(StoredArray((),17))

if __name__=='__main__':unittest.main()
