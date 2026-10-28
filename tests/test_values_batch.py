import unittest
from dataclasses import replace
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.values import read_values_many
import test_values


class ValueBatchTests(unittest.TestCase):
    def test_reference_batch_limit_accepts_256_unique_targets_and_rejects_more(self):
        from expedition33.catalog import Catalog
        from expedition33.values import read_values_many_with_references
        original=self.fixture.obj
        targets=[replace(original,index=1000+i,address=0x100000+i*256,name='Target'+str(i)) for i in range(257)]
        catalog=Catalog(123,list(self.fixture.catalog.objects)+targets,list(self.fixture.catalog.classes.values()))
        rows=[dict(event='object',index=o.index,serial=o.serial,address=hex(o.address),
                   class_index=o.class_index,name=o.name) for o in targets[:256]]
        with patch('expedition33.values._query',return_value=({'pid':123},rows)) as query:
            result,observed=read_values_many_with_references(catalog,targets[:256])
        self.assertEqual(set(result),{o.index for o in targets[:256]})
        self.assertIs(observed,catalog)
        self.assertEqual(query.call_count,1)
        bad_rows=rows[:200]+[dict(rows[200],serial=999)]+rows[201:]
        for response in (bad_rows,rows[:-1]):
            with patch('expedition33.values._query',return_value=({'pid':123},response)):
                with self.assertRaises(RuntimeQueryError):
                    read_values_many_with_references(catalog,targets[:256])
        with patch('expedition33.values._query',side_effect=AssertionError('must not query')):
            with self.assertRaises(ValueError):read_values_many_with_references(catalog,targets)
            with self.assertRaises(ValueError):read_values_many_with_references(catalog,[targets[0],targets[0]])

    def test_reference_extension_redecodes_only_affected_groups_if_catalog_stable(self):
        from expedition33.catalog import Catalog
        from expedition33.values import read_values_many_with_references,_decode_values
        objects=list(self.fixture.catalog.objects);classes=list(self.fixture.catalog.classes.values())
        first,second=objects[4],objects[5]
        added=replace(second,index=6,address=0x9000,name='NewObject',outer_index=-1,outer_serial=0)
        initial=Catalog(123,objects,classes);extended=Catalog(123,objects+[added],classes)
        def target(obj):return dict(event='object',index=obj.index,serial=obj.serial,address=hex(obj.address),class_index=obj.class_index,name=obj.name)
        def prop(name,kind):return dict(event='property_metadata',owner_index=2,name=name,type=kind,dimension=1)
        def value(name,data):return dict(event='stored_value',owner_index=2,name=name,element=0,value=data)
        ref=dict(index=added.index,serial=added.serial,address=hex(added.address),name=added.name)
        rows=[target(first),prop('Level','IntProperty'),value('Level',33),
              target(second),prop('Child','ObjectProperty'),value('Child',{'$reference':ref})]
        def run(selected,metrics=None):
            with patch('expedition33.values._query',return_value=({'pid':123},rows)), \
                 patch('expedition33.catalog.capture_selected',return_value=selected), \
                 patch('expedition33.values._decode_values',wraps=_decode_values) as decoded:
                result,combined=read_values_many_with_references(initial,(first,second),metrics=metrics)
            return result,combined,decoded
        metrics={}
        result,combined,decoded=run(extended,metrics)
        self.assertEqual(decoded.call_count,3)
        for key in ('source_values_query_ms','source_values_decode_ms','source_reference_scan_ms','source_reference_capture_ms'):
            self.assertGreaterEqual(metrics[key],0.)
        self.assertEqual(result[first.index].values[2,'Level'],33)
        self.assertEqual(result[second.index].values[2,'Child'],added)
        self.assertIs(result[first.index].target,combined.by_index[first.index])
        # A changed outer/flags requires a fresh decode of every group.
        changed=Catalog(123,[replace(o,object_flags=1) if o.index==first.index else o
                             for o in objects+[added]],classes)
        result,combined,decoded=run(changed)
        self.assertEqual(decoded.call_count,4)
        self.assertEqual(result[first.index].target.object_flags,1)
        # New class relations also force the conservative path.
        classes.append(replace(classes[-1],index=7,name='NewClass'))
        class_object=replace(objects[1],index=7,address=0xa000,name='NewClass')
        _,_,decoded=run(Catalog(123,objects+[added,class_object],classes))
        self.assertEqual(decoded.call_count,4)
        with patch('expedition33.values._query',return_value=({'pid':123},rows)), \
             patch('expedition33.catalog.capture_selected',side_effect=RuntimeQueryError('recycled')):
            with self.assertRaisesRegex(RuntimeQueryError,'recycled'):
                read_values_many_with_references(initial,(first,second))
    def test_large_reference_closure_uses_bounded_queries_and_revalidates_targets(self):
        from expedition33.values import _extend_reference_catalog,_missing_references
        f=self.fixture;target=(f.obj.index,f.obj.serial,f.obj.address)
        missing={(10000+i,7,0x100000+i*256) for i in range(1300)}
        rows=[dict(event='stored_value',value={'$array':dict(length=1300,items=[
            {'$reference':dict(index=i,serial=s,address=hex(a),name='Actor')} for i,s,a in sorted(missing)])})]
        self.assertEqual(_missing_references(f.catalog,rows),missing)
        with patch('expedition33.catalog.capture_selected',return_value=f.catalog) as selected:
            result=_extend_reference_catalog(f.catalog,(target,),missing)
        self.assertIn(f.obj.index,result.by_index)
        self.assertEqual(selected.call_count,2)
        calls=[c.args[1] for c in selected.call_args_list]
        self.assertTrue(all(len(c)<=1023 and c[0]==target for c in calls))
        self.assertEqual({row for call in calls for row in call[1:]},missing)
        with patch('expedition33.catalog.capture_selected',side_effect=(f.catalog,RuntimeQueryError('recycled'))) as selected:
            with self.assertRaisesRegex(RuntimeQueryError,'recycled'):
                _extend_reference_catalog(f.catalog,(target,),missing)
        self.assertEqual(selected.call_count,2)
    def setUp(self):
        self.fixture = test_values.ValueTests()
        self.fixture.setUp()
        self.fixture.property('CurrentLevel', 'IntProperty')
        self.fixture.value('CurrentLevel', 33)

    def test_projection_uses_validated_identity_and_one_query(self):
        f = self.fixture
        with patch('expedition33.values._query', return_value=({'pid': 123}, f.rows)) as query:
            result = read_values_many(f.catalog, [f.obj], fields=('CurrentLevel',))
        self.assertEqual(result[f.obj.index].values[2, 'CurrentLevel'], 33)
        query.assert_called_once_with(['--read-values', '123',
            f'{f.obj.index}:{f.obj.serial}:{f.obj.address:x};CurrentLevel'])

    def test_missing_duplicate_and_recycled_responses_fail(self):
        f = self.fixture
        for rows in ([], f.rows + f.rows, [dict(f.rows[0], serial=999), *f.rows[1:]]):
            with self.subTest(rows=rows), patch('expedition33.values._query', return_value=({'pid':123}, rows)):
                with self.assertRaises(RuntimeQueryError):
                    read_values_many(f.catalog, [f.obj])

    def test_invalid_projection_and_duplicate_targets_never_query(self):
        f = self.fixture
        with patch('expedition33.values._query', side_effect=AssertionError('must not query')):
            for fields in ((), ('A', 'A'), ('A|B',), ('A\n',)):
                with self.assertRaises(ValueError):
                    read_values_many(f.catalog, [f.obj], fields=fields)
            with self.assertRaises(ValueError):
                read_values_many(f.catalog, [f.obj, f.obj])
