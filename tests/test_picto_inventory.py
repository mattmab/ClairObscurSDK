import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
from expedition33.picto_inventory import owned_pictos


def values(**fields):
    return NS(types={(0,k):None for k in fields},values={(0,k):v for k,v in fields.items()},errors={})


class OwnedPictos(unittest.TestCase):
    def setUp(self):
        self.system=NS(class_name='BP_ItemUpgradeSystem_C',object_flags=0)
        self.item=NS(index=1,class_name='BP_ItemInstance_Gear_Pictos_C',object_flags=0)
        self.catalog=NS(select=lambda cls:[self.system])

    def read(self, entries, **fields):
        with patch('expedition33.picto_inventory.read_values_with_references',return_value=(values(ItemInstances=NS(items=entries)),self.catalog)), \
             patch('expedition33.picto_inventory.read_values_many',return_value={1:values(**fields)}):
            return owned_pictos(123,catalog=self.catalog)[1]

    def test_only_authoritative_positive_quantity_entries_are_owned(self):
        self.assertEqual(self.read({'Cheater':self.item},ItemDefinitionID='Cheater',Quantity=1,CurrentLevel=33),{'Cheater':(self.item,33)})
        self.assertEqual(self.read({'Cheater':self.item},ItemDefinitionID='Cheater',Quantity=0,CurrentLevel=33),{})

    def test_mismatched_definition_and_duplicate_object_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'identity mismatch'):
            self.read({'Cheater':self.item},ItemDefinitionID='Other',Quantity=1,CurrentLevel=33)
        with self.assertRaisesRegex(RuntimeError,'Duplicate'):
            self.read({'Cheater':self.item,'Other':self.item},ItemDefinitionID='Cheater',Quantity=1,CurrentLevel=33)

    def test_non_picto_map_entries_are_not_bulk_targets(self):
        self.assertEqual(self.read({'Weapon':NS(class_name='BP_ItemInstance_Gear_Weapon_C')}),{})
