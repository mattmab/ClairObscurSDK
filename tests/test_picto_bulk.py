import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33.picto_bulk import PictoBulkJob


class Bulk(unittest.TestCase):
    def job(self):
        job=PictoBulkJob.__new__(PictoBulkJob)
        item=NS(index=1,serial=2,address=3)
        job.scope=NS(pid=123);job.mode='level';job.value=32;job.preferences=Mock()
        job.catalog=object();job.planner=Mock();job.owned={'Cheater':(item,33)}
        job.queue=['Cheater'];job.total=1;job.completed=0;job.done=False;job.error=None;job.confirmed=[]
        job.fn=Mock();job.characters=[]
        return job,item

    def test_confirmed_edit_is_saved_before_next_item(self):
        job,item=self.job()
        with patch('expedition33.picto_bulk.owned_pictos',return_value=(job.catalog,job.owned)),patch('expedition33.picto_bulk.change',return_value=32) as change:
            job.tick()
        change.assert_called_once()
        job.preferences.remember.assert_called_once_with('Cheater','level',32)
        self.assertEqual(job.completed,1);self.assertEqual(job.queue,[])
        job.tick();self.assertTrue(job.done)

    def test_removed_item_stops_without_mutation(self):
        job,item=self.job()
        with patch('expedition33.picto_bulk.owned_pictos',return_value=(job.catalog,{})),patch('expedition33.picto_bulk.change') as change:
            with self.assertRaisesRegex(RuntimeError,'ownership changed'):job.tick()
            job.tick()
        change.assert_not_called();job.preferences.remember.assert_not_called();self.assertTrue(job.done)

    def test_uncertain_mutation_never_retries_or_saves(self):
        job,item=self.job()
        with patch('expedition33.picto_bulk.owned_pictos',return_value=(job.catalog,job.owned)),patch('expedition33.picto_bulk.change',side_effect=RuntimeError('uncertain')) as change:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):job.tick()
            job.tick()
        change.assert_called_once();job.preferences.remember.assert_not_called()

    def test_level_bounds_checked_before_discovery(self):
        for level in (0,34,True,2.5):
            with self.assertRaises(ValueError):PictoBulkJob(None,None,'level',level,None)
