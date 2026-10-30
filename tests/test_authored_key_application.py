import copy,unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_authored_timeline import fixture,SECTION
from expedition33.cinematics.authored_timeline import create,edit_key
from expedition33.cinematics.authored_copy import apply_key_edits,seal_copy


class KeyApplicationTests(unittest.TestCase):
    def run_plan(self,*,changed=False,failure=None,missing=False,signature_changed=False):
        guid=dict(struct='/Script/CoreUObject.Guid',fields=dict(A=1,B=2,C=3,D=4),complete=True,errors={})
        graph=fixture()['source'];graph['nodes'][SECTION]['fields']['Signature']=guid
        document=edit_key(create(graph,'Native edit'),SECTION,['Translation',0],0,at=500,value=12.5)
        root=N(index=1,serial=1,address=0x10000,class_name='LevelSequence')
        outer=N(index=2,serial=1,address=0x20000,class_name='WidgetTree')
        target=N(index=3,serial=1,address=0x30000,name=SECTION.rsplit('.',1)[-1],class_name='MovieScene3DTransformSection')
        original=N(index=4,serial=1,address=0x40000,name=target.name,class_name=target.class_name)
        catalog=Mock();catalog.objects=(target,original);catalog.with_observations.return_value=catalog
        catalog.outer_chain.side_effect=lambda obj:(outer,root) if obj is target else (outer,) if obj is root else ()
        catalog.find_path.return_value=original
        record=dict(state='fresh',source=graph['sequence'],outer=(2,1,0x20000))
        scope=N(pid=99,_session=N(_transport=N(authored_curve_patch_protocol=1,_executable='reader')),
                _authored_copy_states={(1,1,0x10000):record})
        def read(c,obj,fields):
            values={name:copy.deepcopy(graph['nodes'][SECTION]['fields'][name]) for name in fields}
            if changed and obj is target and 'Translation' in fields:values['Translation']['static_array'][0]['fields']['Values']['array'][1]['fields']['Value']=99.
            if signature_changed and obj is target and 'Translation' in fields:values['Signature']['fields']['A']=99
            return N(errors={},truncated=(),values={(obj.index,k):v for k,v in values.items()}),catalog
        batches=[]
        def read_many(pid,identities,fields,references):
            self.assertEqual(pid,99);self.assertTrue(references)
            by_index={o.index:o for o in (target,original)}
            objects=tuple(by_index[row[0]] for row in identities)
            self.assertEqual(identities,tuple((o.index,o.serial,o.address) for o in objects))
            batches.append((tuple(obj.index for obj in objects),fields))
            rows={obj.index:read(catalog,obj,fields)[0] for obj in objects}
            if missing and len(objects)==2:rows.pop(target.index)
            return catalog,rows
        with patch('expedition33.cinematics.authored_copy.shared_operation',return_value=nullcontext()),\
             patch('expedition33.cinematics.authored_copy.capture_matching',return_value=catalog),\
             patch('expedition33.cinematics.authored_copy.capture_selected'),\
             patch('expedition33.cinematics.authored_copy.capture_selected_values',side_effect=read_many),\
             patch('expedition33.cinematics.authored_copy.copied',side_effect=lambda value,c:value),\
             patch('expedition33._authored_curve_patch.patch',side_effect=failure) as native:
            if changed or failure or missing or signature_changed:
                with self.assertRaises(RuntimeError):apply_key_edits(scope,root,outer,document)
            else:
                self.assertEqual(apply_key_edits(scope,root,outer,document),{(SECTION,('Translation',0)):1})
                self.assertEqual(record['state'],'ready')
                self.assertEqual(batches,[((3,),('Signature',)),((4,3),('Signature','Translation'))])
                self.assertEqual(native.call_args.args[-1],[dict(index=0,before_time=0,after_time=500,before=10.,after=12.5)])
                seal_copy(scope,root)
                with self.assertRaisesRegex(RuntimeError,'fresh private'):apply_key_edits(scope,root,outer,document)
            return native.call_count,record['state']
    def test_applies_imported_key_ordinals_only_inside_fresh_copy_window(self):
        self.assertEqual(self.run_plan(),(1,'sealed'))
    def test_changed_unedited_neighbor_rejects_before_native_write(self):
        self.assertEqual(self.run_plan(changed=True),(0,'fresh'))
    def test_failed_native_edit_never_leaves_copy_eligible_for_playback(self):
        self.assertEqual(self.run_plan(failure=RuntimeError('write outcome unknown')),(1,'rejected'))
    def test_missing_batch_target_rejects_before_native_write(self):
        self.assertEqual(self.run_plan(missing=True),(0,'fresh'))
    def test_private_signature_change_between_discovery_and_channel_read_rejects(self):
        self.assertEqual(self.run_plan(signature_changed=True),(0,'fresh'))


if __name__=='__main__':unittest.main()
