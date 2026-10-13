import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch

from expedition33 import picto_details as module


def values(**fields):
    fields={(1,key):value for key,value in fields.items()}
    return NS(values=fields,types=fields,errors={})


class Array(list):
    @property
    def items(self):return self


def member(**fields):return NS(fields=fields,errors={},truncated=False)


class DetailsTests(unittest.TestCase):
    def setUp(self):
        self.asset=NS(index=10,serial=1,address=100)
        self.tables=[NS(index=i,class_name='DataTable',path=path) for i,path in enumerate(
            (module.DEFINITION_TABLE,module.STATIC_TABLE,module.PASSIVE_TABLE))]
        self.catalog=NS(objects=self.tables,path_name=lambda obj:obj.path)
        self.rows={'Picto':{'name':'Picto','normal':True,'asset':self.asset}}
        self.definition=values(**{module.ITEM_ID:'Picto',module.MULTIPLIERS:NS(items={1:.7,8:1.})})
        self.static=values(**{module.STATIC_ID:'Picto',module.STATIC_ASSET:self.asset})
        self.passive=values(**{module.COST:5,module.DESCRIPTION:'One extra hit.'})
        self.references=Array([member(**{module.PASSIVE_ROW:member(DataTable=self.tables[2],RowName='Effect')})])

    def read(self):
        with patch.object(module,'read_table_rows',side_effect=[{'Picto':self.definition},
                {'Picto':self.static},{'Effect':self.passive}]), \
             patch.object(module,'read_values_many',return_value={10:values(PassiveEffects=self.references)}):
            return module.definition_details(self.catalog,self.rows)['Picto']

    def test_verified_reference_resolves_cost_without_inventing_locked_stats(self):
        result=self.read()
        self.assertEqual(result['cost'],5);self.assertEqual(result['effect'],'One extra hit.')
        self.assertEqual(result['base_stat_multipliers'],{'health':.7,'speed':1.})
        self.assertIsNone(result['health']);self.assertIsNone(result['speed'])
        self.assertIsNone(result['acquisition'])
        self.assertEqual(result['effect_references'],[{'table':module.PASSIVE_TABLE,'row':'Effect'}])

    def test_undecoded_text_stays_unavailable_but_cost_is_readable(self):
        self.passive=values(**{module.COST:5,module.DESCRIPTION:object()})
        result=self.read()
        self.assertIsNone(result['effect']);self.assertEqual(result['cost'],5)
        self.assertIn('effect',result['unavailable'])

    def test_stale_static_asset_cannot_supply_passive_metadata(self):
        self.static=values(**{module.STATIC_ID:'Picto',module.STATIC_ASSET:NS(index=10,serial=2,address=100)})
        result=self.read()
        self.assertIsNone(result['cost']);self.assertIsNone(result['effect'])
        self.assertIn('identity mismatch',result['unavailable']['passive'])

    def test_multiple_passives_do_not_invent_aggregate_cost(self):
        self.references.append(self.references[0])
        result=self.read()
        self.assertIsNone(result['cost']);self.assertIn('cost',result['unavailable'])

    def test_native_table_read_failure_propagates_to_worker(self):
        with patch.object(module,'read_table_rows',side_effect=RuntimeError('stale identity')):
            with self.assertRaisesRegex(RuntimeError,'stale identity'):
                module.definition_details(self.catalog,self.rows)


if __name__=='__main__':unittest.main()
