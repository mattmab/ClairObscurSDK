import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch

from expedition33 import RuntimeQueryError
from expedition33 import save_story_ui as ui


class RowBindingTests(unittest.TestCase):
    def setUp(self):
        self.events=[]
        self.rows=[N(index=i,serial=2,address=100+i,class_name='WBP_MM_SaveSlot_C',object_flags=0) for i in range(3)]
        self.bindings={ui.ident(row):((10+i,3,1000+i),i) for i,row in enumerate(self.rows)}
        self.service=object.__new__(ui.SaveStoryUI)
        self.service.session=N(pid=1);self.service.labels={};self.service.cache={};self.service.titles={}
        self.service._closed=False;self.service.failed=None;self.service.next_poll=0.
        self.service._binding=Mock(side_effect=lambda row,c:self.bindings[ui.ident(row)])
        self.service._label=Mock(side_effect=lambda slot:'Vanilla' if slot==0 else 'Story '+str(slot))

    def owner(self,key,binding,*,verified=True):
        owner=Mock(unknown=False,added=True,verified=verified,binding=binding)
        owner.close.side_effect=lambda:self.events.append(('close',key)) or True
        def build(row,c,text,*,still_bound):
            self.events.append(('build',ui.ident(row)))
            if not still_bound():return False
            owner.verified=True;return True
        owner.build.side_effect=build
        return owner

    def poll(self,factory=None):
        with patch.object(ui,'capture_matching',return_value=N(objects=self.rows)),patch.object(ui.time,'monotonic',return_value=1),patch.object(ui,'Label',side_effect=factory or (lambda session:self.owner('new',None,verified=False))):
            self.service.next_poll=0.;self.service.poll(N(kind='title'))

    def add_existing(self,row,binding,text):
        key=ui.ident(row);owner=self.owner(key,binding)
        self.service.labels[key]=(owner,binding[1],text);return owner

    def test_all_recycled_rows_retire_before_one_replacement_builds(self):
        for row in self.rows:self.add_existing(row,((99,1,999),9),'Former save')
        self.poll()
        self.assertEqual(self.events[:3],[('close',ui.ident(row)) for row in self.rows])
        self.assertEqual(self.events[3:],[('build',ui.ident(self.rows[0]))])
        self.assertEqual(len(self.service.labels),1)
        self.assertIsNone(self.service.failed)

    def test_unassigned_row_loses_its_old_label_without_building(self):
        row=self.rows[0];self.rows=[row];owner=self.add_existing(row,self.bindings[ui.ident(row)],'Vanilla')
        self.bindings[ui.ident(row)]=None
        self.poll()
        owner.close.assert_called_once();self.assertEqual(self.service.labels,{})

    def test_new_model_identity_is_reconciled_even_when_slot_and_text_match(self):
        row=self.rows[0];self.rows=[row];key=ui.ident(row)
        owner=self.add_existing(row,((999,1,9999),0),'Vanilla')
        self.poll()
        owner.close.assert_called_once();self.assertEqual(self.service.labels[key][0].binding,self.bindings[key])

    def test_row_rebound_between_snapshot_and_build_never_keeps_wrong_label(self):
        row=self.rows[0];self.rows=[row];key=ui.ident(row)
        def factory(session):
            self.bindings[key]=((55,5,555),5)
            return self.owner('new',None,verified=False)
        self.poll(factory)
        self.assertEqual(self.service.labels,{})
        self.assertEqual(self.events[-1],('close','new'))

    def test_incomplete_binding_read_retires_unproven_labels(self):
        row=self.rows[0];self.rows=[row];owner=self.add_existing(row,self.bindings[ui.ident(row)],'Vanilla')
        self.service._binding.side_effect=RuntimeQueryError('Recycled while reading')
        self.poll()
        owner.close.assert_called_once();self.assertEqual(self.service.labels,{})
        self.assertIsNone(self.service.failed)

    def test_read_failure_after_attachment_removes_the_unverified_widget(self):
        row=self.rows[0];self.rows=[row];binding=self.bindings[ui.ident(row)]
        self.service._binding.side_effect=[binding,binding,binding,RuntimeQueryError('Changed after attachment')]
        owner=self.owner('new',None,verified=False);owner.widget=object();owner.frame=object();owner.cell=dict(Row=0,Column=0,RowSpan=5,ColumnSpan=1,Layer=0);owner.added=False
        publish=ui.Label.publish
        owner.build.side_effect=lambda row,c,text,still_bound:publish(owner,object(),text,lambda *a,**k:nullcontext(N(return_value=object())),still_bound)
        self.poll(lambda session:owner)
        owner.close.assert_called_once();self.assertEqual(self.service.labels,{})
        self.assertIsNone(self.service.failed)

    def test_pending_retirement_retains_owner_and_prevents_new_builds(self):
        row=self.rows[0];self.rows=[row];owner=self.add_existing(row,((99,1,999),9),'Former save')
        owner.close.side_effect=None;owner.close.return_value=False
        factory=Mock()
        self.poll(factory)
        factory.assert_not_called();self.assertIs(self.service.labels[ui.ident(row)][0],owner)

    def test_title_registration_invalidates_fallback_without_file_changes(self):
        self.service.cache={'same-file-and-store':'Custom story: pack'};self.service.next_poll=5.
        self.service.register('pack','Named story')
        self.assertEqual(self.service.cache,{});self.assertEqual(self.service.next_poll,0.)
        self.service.cache={'stable':'Named story'};self.service.register('pack','Named story')
        self.assertEqual(self.service.cache,{'stable':'Named story'})


class PublicationTests(unittest.TestCase):
    def owner(self):
        owner=object.__new__(ui.Label);owner.widget=object();owner.frame=object();owner.added=False;owner.verified=False
        owner.cell=dict(Row=0,Column=0,RowSpan=5,ColumnSpan=1,Layer=0);owner._adopt=Mock()
        return owner

    def test_rebind_during_text_preparation_prevents_attachment(self):
        owner=self.owner();calls=[];bound=[True]
        def call(target,path,**args):
            calls.append(path);bound[0]=False;return nullcontext()
        self.assertFalse(owner.publish(object(),'Vanilla',call,lambda:bound[0]))
        self.assertEqual(calls,['/Script/UMG.TextBlock:SetText'])
        self.assertFalse(owner.added);self.assertFalse(owner.verified)

    def test_rebind_during_attachment_is_unverified_and_requires_retirement(self):
        owner=self.owner();bound=[True]
        def call(target,path,**args):
            if path.endswith('AddChildToGrid'):bound[0]=False
            return nullcontext(N(return_value=object()))
        self.assertFalse(owner.publish(object(),'Vanilla',call,lambda:bound[0]))
        self.assertTrue(owner.added);self.assertFalse(owner.verified)

    def test_stable_binding_publishes_verified_label(self):
        owner=self.owner()
        calls=[]
        def call(target,path,**arguments):
            calls.append((target,path,arguments));return nullcontext(N(return_value=object()))
        self.assertTrue(owner.publish(object(),'Named story',call,lambda:True))
        self.assertTrue(owner.added);self.assertTrue(owner.verified)
        attachment=next(row for row in calls if row[1].endswith(':AddChildToGrid'))
        self.assertEqual(attachment[2],dict(Content=owner.frame,InRow=0,InColumn=0))
        self.assertIn('/Script/UMG.GridSlot:SetRowSpan',[row[1] for row in calls])


if __name__=='__main__':unittest.main()
