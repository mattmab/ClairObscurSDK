"""Catalog snapshot and transaction interaction, without native game access."""
import unittest
from concurrent.futures import Future
from types import SimpleNamespace as NS
from unittest.mock import patch

from expedition33.picto_catalog import CatalogView, NativeCatalog
from expedition33.picto_transactions import UnlockTransaction


class FailureFlowTests(unittest.TestCase):
    def test_reported_unlock_failure_then_filters_and_second_selection(self):
        rows={key:{'name':key,'normal':key!='Experimental',
                   'asset':NS(index=i,serial=1,address=100+i)}
              for i,key in enumerate(('Already','First','Second','Experimental'))}
        actual={'Already':object()}
        owner=NS(rows=rows,owned=dict(actual),scope=NS(_check=lambda:None),
            manager=object(),table=object(),gi=object(),function=lambda *args:object())
        owner.refresh=lambda:dict(actual)
        def submit(callback):
            future=Future()
            try:future.set_result(callback())
            except Exception as error:future.set_exception(error)
            return future
        tx=UnlockTransaction(owner,submit)
        view=CatalogView(rows,actual)
        editor=NS(catalog_selection='First',call=lambda *args,**kwargs:0.)
        catalog=NativeCatalog(editor);catalog.view=view
        catalog.extent=object();catalog.scroll=object();catalog.poll=lambda:None
        self.assertEqual(view.filter,'all')
        with patch('expedition33.picto_transactions.change',side_effect=RuntimeError('error=1753')) as mutation:
            tx.start(editor.catalog_selection);tx.poll();tx.poll()
            self.assertEqual(tx.state,'Failed');self.assertFalse(tx.busy)
            for selected_filter in ('all','locked','owned','all','locked'):
                view.filter=selected_filter;catalog.reset()
                self.assertIn(editor.catalog_selection,view.ids)
            editor.catalog_selection='Second';catalog.reset()
            self.assertEqual(editor.catalog_selection,'Second')
            self.assertEqual(view.ids,['First','Second'])
            self.assertEqual(mutation.call_count,1)
            self.assertTrue(tx.start('Second'))


if __name__=='__main__':unittest.main()
