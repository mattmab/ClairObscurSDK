import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33.picto_catalog import CatalogView, NativeCatalog, details_text


class CatalogTests(unittest.TestCase):
    def view(self):
        rows={f'p{i:03}':{'name':f'Picto {i:03}','normal':True} for i in range(210)}
        rows['test']={'name':'TEST','normal':False}
        return CatalogView(rows,{'p000':object()})

    def test_scroll_reaches_every_definition_with_bounded_rows(self):
        v=self.view();seen=set()
        for offset in range(0,int(v.height),30):
            start,ids=v.window(offset)
            self.assertEqual(start%2,0)
            self.assertLessEqual(len(ids),CatalogView.POOL_SIZE)
            seen.update(ids)
        self.assertEqual(seen,set(v.ids));self.assertEqual(len(seen),210)

    def test_owned_locked_and_experimental_are_independent(self):
        v=self.view();v.filter='owned';v.rebuild();self.assertEqual(v.ids,['p000'])
        v.filter='locked';v.rebuild();self.assertEqual(len(v.ids),209)
        v.experimental=True;v.rebuild();self.assertEqual(v.ids,['test'])
        self.assertEqual(len(v.owned),1)

    def test_search_is_case_insensitive_and_does_not_mutate_definitions(self):
        v=self.view();v.query='PICTO 209';v.rebuild();self.assertEqual(v.ids,['p209'])
        self.assertEqual(len(v.definitions),211)
        v.query='no match';v.rebuild();self.assertEqual(v.window(9999),(0,[]))

    def test_invalid_scroll_rejected(self):
        with self.assertRaises(ValueError):self.view().window(float('nan'))

    def test_repeated_four_filter_transitions_use_cached_snapshot(self):
        v=self.view();original=dict(v.definitions)
        for _ in range(20):
            for experimental,kind,count,label in ((False,'all',210,'All Pictos'),
                    (False,'owned',1,'Owned Only'),(False,'locked',209,'Locked Only'),
                    (True,'all',1,'Experimental')):
                v.experimental=experimental;v.filter=kind;v.rebuild()
                self.assertEqual(len(v.ids),count);self.assertEqual(v.filter_label,label)
                self.assertEqual(v.ids,sorted(v.ids,key=lambda k:(v.definitions[k]['name'].casefold(),k)))
        self.assertEqual(v.definitions,original)

    def test_verified_unlock_updates_counts_and_selects_next_locked(self):
        v=self.view();v.filter='locked';v.rebuild();previous=tuple(v.ids)
        selected='p001';v.owned[selected]=object();v.rebuild()
        self.assertEqual(v.reconcile_selection(selected,previous),'p002')
        self.assertEqual(v.counts,{'gameplay':210,'owned':2,'locked':208,'experimental':1})
        self.assertNotIn(selected,v.ids)
        v.owned['test']=object();v.owned['unknown']=object()
        self.assertEqual(v.counts['owned'],2)

    def test_selection_preserved_then_last_removed_falls_back_without_wrap(self):
        v=self.view();v.filter='locked';v.rebuild();previous=tuple(v.ids)
        self.assertEqual(v.reconcile_selection('p117',previous),'p117')
        v.owned['p209']=object();v.rebuild()
        self.assertEqual(v.reconcile_selection('p209',previous),'p208')
        v.query='no matches';v.rebuild();self.assertIsNone(v.reconcile_selection('p208',previous))

    def test_locked_details_do_not_fabricate_inventory_values(self):
        text=details_text({'name':'Test Picto','identity':'test','owned':False,'normal':True,
            'level':33,'mastery':'Mastered','cost':0,'health':0})
        self.assertIn('Level: Unavailable (not owned)',text)
        self.assertIn('Mastery: Unavailable (not owned)',text)
        self.assertIn('Lumina cost: 0',text);self.assertIn('Health: 0',text)
        self.assertIn('Effect: Unavailable',text);self.assertIn('Acquisition: Unavailable',text)
        self.assertNotIn('Mastered',text)

    def test_details_reports_failure_and_experimental_separately(self):
        text=details_text({'name':'TEST','normal':False,'owned':False,
            'state':'Timed Out','message':'Ownership must be re-read'})
        self.assertIn('EXPERIMENTAL',text)
        self.assertIn('Timed Out: Ownership must be re-read',text)

    def test_selection_only_updates_changed_labels_and_unchanged_poll_is_idle(self):
        editor=SimpleNamespace(catalog_selection='a',call=Mock(return_value=0.),
            defer_layout=Mock(),flush_layout=Mock(),observers=[],_text={})
        catalog=NativeCatalog(editor)
        catalog.view=CatalogView({'a':{'name':'A','normal':True},'b':{'name':'B','normal':True}}, {})
        catalog.visible=True;catalog.scroll=object();catalog.first_button=12
        catalog.hidden_value=object();catalog.visible_value=object()
        catalog.rows=[(object(),SimpleNamespace(index=i),object()) for i in range(2)]
        catalog.poll()
        editor.defer_layout.reset_mock();editor.flush_layout.reset_mock()
        catalog.poll()
        editor.defer_layout.assert_not_called();editor.flush_layout.assert_not_called()
        editor.catalog_selection='b';catalog.poll()
        self.assertEqual([call.args[2] for call in editor.defer_layout.call_args_list],['SetText','SetText'])
        self.assertEqual(catalog.mapping,{12:'a',13:'b'})

    def test_filter_reset_selects_a_visible_entry(self):
        editor=SimpleNamespace(catalog_selection='a',call=Mock())
        catalog=NativeCatalog(editor);catalog.extent=object();catalog.scroll=object()
        catalog.view=CatalogView({'a':{'name':'A','normal':True},'b':{'name':'B','normal':True}}, {'a':object()})
        catalog.view.filter='locked';catalog.poll=Mock();catalog.reset()
        self.assertEqual(editor.catalog_selection,'b')

    def test_refresh_preserves_scroll_and_filter_roundtrip_restores_offset(self):
        e=SimpleNamespace(catalog_selection='p100',call=Mock(return_value=1920.))
        n=NativeCatalog(e);n.view=self.view();n.extent=object();n.scroll=object()
        n.visible=True;n.poll=Mock();n.filter_key=(False,'all','')
        n.reset()
        self.assertFalse(any(c.args[2]=='SetScrollOffset' for c in e.call.call_args_list))
        e.call.reset_mock();n.view.filter='owned';n.reset()
        self.assertEqual(e.catalog_selection,'p000')
        self.assertTrue(any(c.args[2]=='SetScrollOffset' and c.kwargs['NewScrollOffset']==0. for c in e.call.call_args_list))
        e.call.reset_mock();e.call.return_value=0.;n.view.filter='all';n.reset()
        self.assertTrue(any(c.args[2]=='SetScrollOffset' and c.kwargs['NewScrollOffset']==1920. for c in e.call.call_args_list))

    def test_ownership_refresh_changes_only_affected_row_status(self):
        e=SimpleNamespace(catalog_selection='a',call=Mock(return_value=0.),
            defer_layout=Mock(),flush_layout=Mock(),observers=[],_text={})
        n=NativeCatalog(e);n.view=CatalogView({'a':{'name':'A','normal':True},'b':{'name':'B','normal':True}}, {})
        n.visible=True;n.scroll=object();n.first_button=12
        n.hidden_value=object();n.visible_value=object()
        n.rows=[(object(),SimpleNamespace(index=i),object()) for i in range(2)]
        n.poll();e.defer_layout.reset_mock();n.view.owned['a']=object();n.poll()
        self.assertEqual(len(e.defer_layout.call_args_list),1)
        call=e.defer_layout.call_args_list[0]
        self.assertEqual(call.args[2],'SetText');self.assertEqual(call.kwargs['InText'],'> A\nOwned')

    def test_small_scroll_rebinds_only_entering_rows_and_keeps_click_identity(self):
        v=self.view()
        e=SimpleNamespace(catalog_selection=None,call=Mock(return_value=960.),
            defer_layout=Mock(),flush_layout=Mock(),observers=[],_text={})
        n=NativeCatalog(e);n.view=v;n.visible=True;n.scroll=object();n.first_button=12
        n.hidden_value=object();n.visible_value=object()
        n.rows=[(object(),SimpleNamespace(index=i),object()) for i in range(v.POOL_SIZE)]
        n.poll();before=dict(n.mapping);e.defer_layout.reset_mock()
        e.call.return_value=1056.;n.poll()
        calls=e.defer_layout.call_args_list
        self.assertEqual(sum(c.args[2]=='SetText' for c in calls),2)
        self.assertEqual(sum(c.args[2]=='SetPosition' for c in calls),2)
        for button,identity in before.items():
            if identity in n.mapping.values():self.assertEqual(n.mapping[button],identity)
        start,ids=v.window(1056.)
        self.assertEqual(set(n.mapping.values()),set(ids))
        self.assertLessEqual(start, 2*(11-v.PRELOAD_ROWS))
