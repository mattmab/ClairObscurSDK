"""Bounded selected schema/type closure, without live calls or registry scans."""
from dataclasses import replace
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.reflection import describe_selected
from test_catalog import fixture


class SelectedReflectionTests(unittest.TestCase):
    def setUp(self):
        self.complete = Catalog(123, *fixture())
        self.root = self.complete.by_index[2]
        self.reference = self.complete.by_index[3]
        self.selected = self.complete.subset((self.root,))
        self.identity = (self.root.index, self.root.serial, self.root.address)

    def rows(self, prefix='struct', address=True):
        root, ref = self.root, self.reference
        prop = dict(event='property_metadata', name='Element', type='StructProperty', flags='0x0')
        prop.update({prefix + '_index': ref.index, prefix + '_serial': ref.serial,
                     prefix + '_name': ref.name})
        if address:
            prop[prefix + '_address'] = hex(ref.address)
        return [dict(event='object', index=root.index, serial=root.serial,
                     address=hex(root.address), name=root.name, class_index=root.class_index),
                dict(event='struct_metadata', index=root.index, serial=root.serial,
                     address=hex(root.address), name=root.name), prop]

    def test_selected_function_type_closure_never_uses_name_or_registry_search(self):
        ref = self.reference
        with patch('expedition33.catalog.capture_selected', side_effect=[self.selected, self.complete]) as selected, \
             patch('expedition33.reflection._query', return_value=({'pid':123}, self.rows())) as query:
            result = describe_selected(123, (self.identity,))
        self.assertEqual(selected.call_args_list[0].args, (123, (self.identity,)))
        self.assertEqual(selected.call_args_list[1].args,
                         (123, ((ref.index, ref.serial, ref.address),)))
        query.assert_called_once_with(['--describe', '123', f'{self.root.index}:{self.root.serial}:{self.root.address:x}'])
        self.assertEqual(result.catalog.resolve(ref), ref)
        self.assertEqual(set(result.descriptors), {self.root.index})
        with self.assertRaises(TypeError):
            result.descriptors[0] = None

    def test_existing_closure_needs_no_extra_native_selection(self):
        with patch('expedition33.catalog.capture_selected', return_value=self.complete) as selected, \
             patch('expedition33.reflection._query', return_value=({'pid':123}, self.rows(address=False))):
            result = describe_selected(123, (self.identity,))
        self.assertEqual(selected.call_count, 1)
        self.assertIn(self.root.index, result.descriptors)
    def test_inherited_declaring_owner_is_selected_without_repeating_descriptor_query(self):
        ref=self.reference
        rows=self.rows()[:2]+[dict(event='struct_metadata',index=ref.index,serial=ref.serial,
                                  address=hex(ref.address),name=ref.name)]
        with patch('expedition33.catalog.capture_selected',side_effect=[self.selected,self.complete]) as selected,\
             patch('expedition33.reflection._query',return_value=({'pid':123},rows)) as query:
            result=describe_selected(123,(self.identity,))
        self.assertEqual(selected.call_args_list[1].args,(123,((ref.index,ref.serial,ref.address),)))
        self.assertEqual(len(result.descriptors[self.root.index].owners),2)
        query.assert_called_once()

    def test_legacy_missing_type_address_is_explicitly_rejected(self):
        with patch('expedition33.catalog.capture_selected', return_value=self.selected) as selected, \
             patch('expedition33.reflection._query', return_value=({'pid':123}, self.rows(address=False))):
            with self.assertRaisesRegex(RuntimeQueryError, 'update reader or use describe'):
                describe_selected(123, (self.identity,))
        self.assertEqual(selected.call_count, 1)

    def test_reference_changes_do_not_substitute_new_identity_or_retry(self):
        for change in (dict(serial=99), dict(address=0x9999), dict(name='Recycled')):
            changed = replace(self.reference, **change)
            # A minimal observed mock is enough to exercise the strict shared
            # descriptor decoder after a matching native selected response.
            class Fresh:
                pid=123
                by_index={changed.index:changed}
                objects=(changed,)
                classes={}
                _ancestors={}
                _classes_by_name={}
            with patch('expedition33.catalog.capture_selected', side_effect=[self.selected, Fresh()]), \
                 patch('expedition33.reflection._query', return_value=({'pid':123}, self.rows())) as query:
                with self.assertRaises(RuntimeQueryError):
                    describe_selected(123, (self.identity,))
            self.assertEqual(query.call_count, 1)

    def test_conflicting_dependency_selectors_reject_before_selection(self):
        rows = self.rows()
        rows.append(dict(rows[-1], struct_address='0x9999'))
        with patch('expedition33.catalog.capture_selected', return_value=self.selected) as selected, \
             patch('expedition33.reflection._query', return_value=({'pid':123}, rows)):
            with self.assertRaisesRegex(RuntimeQueryError, 'Conflicting'):
                describe_selected(123, (self.identity,))
        self.assertEqual(selected.call_count, 1)

    def test_all_native_reference_metadata_forms_resolve(self):
        from expedition33.reflection import REFERENCE_KINDS
        for prefix in REFERENCE_KINDS:
            with self.subTest(prefix=prefix), \
                 patch('expedition33.catalog.capture_selected', side_effect=[self.selected, self.complete]), \
                 patch('expedition33.reflection._query', return_value=({'pid':123}, self.rows(prefix))):
                self.assertEqual(describe_selected(123, (self.identity,)).descriptors[self.root.index].properties[0][prefix+'_index'], self.reference.index)

    def test_wrong_process_or_malformed_metadata_is_rejected(self):
        for start, rows in (({'pid':124}, self.rows()), ({'pid':123}, self.rows()+[{'event':'unexpected'}])):
            with patch('expedition33.catalog.capture_selected', side_effect=[self.selected, self.complete]), \
                 patch('expedition33.reflection._query', return_value=(start, rows)):
                with self.assertRaises(RuntimeQueryError):
                    describe_selected(123, (self.identity,))

    def test_dependency_budget_rejects_before_unbounded_selection(self):
        rows=self.rows()[:2]
        for index in range(1000,2025):
            rows.append(dict(event='property_metadata',name='Ref',flags='0x0',
                             struct_index=index,struct_serial=1,struct_name='Type',struct_address=hex(0x10000+index*8)))
        with patch('expedition33.catalog.capture_selected', return_value=self.selected) as selected, \
             patch('expedition33.reflection._query', return_value=({'pid':123}, rows)):
            with self.assertRaisesRegex(RuntimeQueryError, 'type limit'):
                describe_selected(123, (self.identity,))
        self.assertEqual(selected.call_count, 1)


if __name__ == '__main__':
    unittest.main()
