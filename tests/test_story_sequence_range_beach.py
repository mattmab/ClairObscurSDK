import unittest,struct
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33 import story_sequence_range as wire

class BeachRangeTests(unittest.TestCase):
    def held(self,n):return N(object=N(index=n,serial=2,address=0x10000+n*16),_token=n+10)
    def packet(self,sequence='departure-beach',mode=0):return wire.packet(5,self.held(1),self.held(2),'e33c5701000000010000000200000003',mode,sequence=sequence)
    def test_exact_beach_range_apply_observe_restore(self):
        for mode in range(3):
            sent=self.packet(mode=mode);wire.validate(sent)
            self.assertEqual(struct.unpack_from('<2I',sent,92),(5501600,5885600))
            reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
            expected=5501600 if mode==2 else 5885600
            struct.pack_into('<I',reply,100,expected)
            self.assertEqual(wire.decode(sent,bytes(reply)),expected)
            reply[100]^=1
            with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
    def test_mixed_profile_or_uninspected_range_is_rejected(self):
        for old,new in ((5501600,7261600),(6493600,5885600),(5501601,5885600)):
            sent=bytearray(self.packet());struct.pack_into('<2I',sent,92,old,new)
            with self.assertRaises(ValueError):wire.validate(bytes(sent))
    def test_old_native_capability_cannot_begin_beach_owner(self):
        parent=N(_session=N(_transport=N(story_sequence_range_protocol=1)))
        with patch.object(wire._Owner,'__init__') as init:
            with self.assertRaisesRegex(RuntimeError,'protocol 2'):wire.StorySequenceRange(parent,'key',sequence='departure-beach')
            init.assert_not_called()
            wire.StorySequenceRange(parent,'key')
            init.assert_called_once()
    def test_profile_is_selected_before_resources_or_game_work(self):
        parent=N(_session=N(_transport=N(story_sequence_range_protocol=2)))
        with patch.object(wire._Owner,'__init__') as init:
            owner=wire.StorySequenceRange(parent,'key',sequence='departure-beach')
            self.assertEqual(owner.sequence,'departure-beach')
            init.assert_called_once_with(parent,'key',resources=None)
            with self.assertRaises(ValueError):wire.StorySequenceRange(parent,'key',sequence='uninspected')
    def test_native_restore_receipt_is_only_valid_for_inspection(self):
        for mode in range(3):
            sent=self.packet(mode=mode);reply=bytearray(sent)
            struct.pack_into('<I',reply,12,4);struct.pack_into('<I',reply,100,5501600)
            if mode==1:self.assertEqual(wire.decode(sent,bytes(reply)),5501600)
            else:
                with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))


class ProcessRangeTests(unittest.TestCase):
    def setUp(self):
        self.session=N(_transport=N(story_sequence_range_protocol=2),_check=lambda:None)
        self.world_scope=N(_session=self.session)
        self.process_scope=object();self.resources=object()
        self.preparation=patch('expedition33._metadata_stabilization.process_preparation',return_value=N(scope=self.process_scope))
        self.preparation.start();self.addCleanup(self.preparation.stop)
        self.created=[]
        outer=self
        class FakeOwner:
            def __init__(self,parent,key,**kwargs):
                self.parent=parent;self.key=key;self.closed=False;self.started=False;self.unknown=False;self.selected=True
                self.close_calls=0;self.kwargs=kwargs;outer.created.append(self)
            def prepare(self):self.started=True;return self
            def active(self):return self.selected
            def close(self):self.close_calls+=1;self.closed=True;return True
        self.factory=patch.object(wire,'StorySequenceRange',FakeOwner);self.factory.start();self.addCleanup(self.factory.stop)
    def ensure(self,key='selected'):
        return wire.ensure_process_range(self.world_scope,key,resources=self.resources)
    def test_world_replacement_reuses_process_owner(self):
        first=self.ensure();self.assertIs(first.parent,self.process_scope)
        self.world_scope=N(_session=self.session)
        self.assertIs(self.ensure(),first);self.assertEqual(len(self.created),1);self.assertFalse(first.closed)
        self.assertTrue(wire.close_process_ranges(self.world_scope));self.assertTrue(first.closed)
        self.assertFalse(self.session._story_process_ranges)
    def test_native_restoration_is_acknowledged_before_rearming(self):
        first=self.ensure();first.selected=False
        second=self.ensure();self.assertIsNot(first,second);self.assertEqual(first.close_calls,1)
        third=self.ensure('other-custom-save');self.assertIsNot(third,second);self.assertEqual(second.close_calls,1)
    def test_failed_preparation_is_retained_not_replayed(self):
        first=self.ensure();first.started=False
        with self.assertRaisesRegex(RuntimeError,'no automatic retry'):self.ensure()
        self.assertEqual(len(self.created),1);self.assertEqual(first.close_calls,0)
    def test_old_protocol_cannot_create_persistent_owner(self):
        self.session._transport.story_sequence_range_protocol=1
        with self.assertRaisesRegex(RuntimeError,'protocol 2'):self.ensure()
        self.assertFalse(self.created)
