import struct,unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import _sequencer_object_array as q
from expedition33.invocation import InvocationError


class SequencerObjectArrayTests(unittest.TestCase):
    def fixture(self):
        class Owner:pass
        session=Owner();scope=Owner();obj=N(index=1,serial=2,address=0x10000)
        session._leases=set();session._abort_ownership=Mock();session.pid=99
        session._transport=N(sequencer_object_array_protocol=1)
        scope._session=session;scope.pid=99;scope._leases=[];scope._check=Mock()
        scope._lease_context=lambda:nullcontext()
        scope._sequencer_array_functions={'MovieSceneSectionExtensions':(obj,obj)}
        return scope,session,obj

    def test_outputs_are_adopted_before_reader_failure_and_released_normally(self):
        scope,session,obj=self.fixture();row=(2,3,0x20000,101)
        session._transport.command=lambda tag,request:{'mesh_packet':self.reply(request,(row,)).hex()}
        def capture(*args):
            self.assertEqual([lease._token for lease in session._leases],[101])
            self.assertEqual([lease._token for lease in scope._leases],[101])
            raise RuntimeError('reader failed')
        def release(lease):
            lease._state='released';session._leases.remove(lease);return True
        session._release_lease=release;session._check=Mock();session._closed=False
        session._transport._check_thread=Mock()
        with patch.object(q,'_hold',return_value=N(object=obj,_token=123)),patch.object(q,'capture_selected',side_effect=capture):
            with self.assertRaisesRegex(RuntimeError,'reader failed'):q.channels(scope,obj)
        self.assertFalse(session._leases);session._abort_ownership.assert_not_called()

    def test_known_reject_preserves_owner_but_unknown_reply_aborts(self):
        for error,state,outcome,abort in ((3741,0,0,False),(3743,2,2,True)):
            scope,session,obj=self.fixture()
            session._transport.command=lambda tag,request:{'mesh_packet':self.reply(request,error=error,state=state,outcome=outcome).hex()}
            with patch.object(q,'_hold',return_value=N(object=obj,_token=123)):
                with self.assertRaises(InvocationError):q.channels(scope,obj)
            self.assertEqual(session._abort_ownership.called,abort)

    def test_unassigned_input_serial_uses_atomic_stable_lease_and_caches_both_identities(self):
        old=N(index=1,serial=0,address=0x10000)
        current=N(index=1,serial=1001,address=0x10000)
        scope=N();lease=N(active=True,object=current)
        with patch('expedition33._stable_lease.acquire_stable',return_value=(lease,Mock())) as acquire:
            self.assertIs(q._hold(scope,old),lease)
            self.assertIs(q._hold(scope,old),lease)
            self.assertIs(q._hold(scope,current),lease)
        acquire.assert_called_once_with(scope,old)

    def request(self,mode=1,index=0):
        obj=N(index=1,serial=2,address=0x10000)
        return q.encode(mode,index,obj,obj,obj,123)
    def reply(self,request,rows=(),total=None,error=0,state=1,outcome=1):
        data=bytearray(request);struct.pack_into('<2I',data,8,error,state)
        struct.pack_into('<4I',data,88,len(rows) if total is None else total,len(rows),outcome,0)
        for i,row in enumerate(rows):q.ROW.pack_into(data,104+i*q.ROW.size,*row)
        return bytes(data)
    def test_all_channels_and_selected_key_keep_total_and_exact_leases(self):
        request=self.request();rows=((2,3,0x20000,101),(4,5,0x30000,102))
        self.assertEqual(q.decode(request,self.reply(request,rows)),(rows,2))
        request=self.request(2,4999)
        self.assertEqual(q.decode(request,self.reply(request,rows[:1],5000)),(rows[:1],5000))
        request=self.request();self.assertEqual(q.decode(request,self.reply(request)),((),0))
    def test_request_padding_stability_mode_and_subject_correlation(self):
        request=self.request()
        for offset in (8,12,88,104,3176,20983):
            bad=bytearray(request);bad[offset]=1
            with self.assertRaises(ValueError):q.validate_request(bytes(bad))
        bad=bytearray(self.request(2));struct.pack_into('<i',bad,32,9)
        with self.assertRaises(ValueError):q.validate_request(bytes(bad))
        for mode,index in ((0,0),(1,1),(2,65536)):
            with self.assertRaises(ValueError):self.request(mode,index)
    def test_known_rejection_range_and_unknown_outcomes_are_distinct(self):
        request=self.request()
        with self.assertRaises(InvocationError) as error:q.decode(request,self.reply(request,error=3741,state=0,outcome=0))
        self.assertEqual(error.exception.outcome,'not_dispatched')
        with self.assertRaises(InvocationError) as error:q.decode(request,self.reply(request,error=3743,state=2,outcome=2))
        self.assertEqual(error.exception.outcome,'unknown')
        with self.assertRaises(IndexError):q.decode(request,self.reply(request,error=3744,total=129))
        request=self.request(2,4)
        with self.assertRaises(IndexError):q.decode(request,self.reply(request,error=3744,total=4))
    def test_result_correlation_aliases_and_impossible_counts_reject(self):
        request=self.request();row=(2,3,0x20000,101)
        for rows in ((row,row),((2,0,0x20000,101),),((2,3,0x20001,101),),((2,3,0x20000,0),)):
            with self.assertRaises(ValueError):q.decode(request,self.reply(request,rows))
        good=self.reply(request,(row,))
        for offset in (16,32,96,100,128,3176,20983):
            bad=bytearray(good);bad[offset]^=1
            with self.assertRaises(ValueError):q.decode(request,bytes(bad))
