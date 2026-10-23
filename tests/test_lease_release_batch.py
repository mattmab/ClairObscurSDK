import pathlib,sys,unittest,struct,threading,io
from types import SimpleNamespace
from unittest.mock import patch
from expedition33.sdk import Session
from expedition33._scope import SessionScope
from expedition33 import _lease_release_batch as batch
from expedition33.ownership import LeaseError
from test_ownership import Transport
class BatchTransport(Transport):
    def __init__(self):
        super().__init__();self.lease_release_batch_protocol=1;self.lease_limit=8192
        self.effects={};self.protected=set();self.bad_batch=False
    def command(self,command,packet=None):
        if command!='lease-release-batch':return super().command(command,packet)
        self._check_thread();self.calls.append(command);batch.validate_request(packet)
        raw=bytearray(packet);version,count,*_=batch.HEADER.unpack_from(packet);completed=error=failed=0
        tokens=[batch.ROW.unpack_from(raw,batch.HEADER.size+i*batch.ROW.size)[0] for i in range(count)]
        for i,token in enumerate(tokens):
            if token not in self.tokens or token in self.protected:
                error=403 if token in self.protected else 402;failed=i+1;break
        if not error:
            for i,token in enumerate(tokens):
                effect=self.effects.get(token,407 if self.defer else 0)
                outcome=batch.RELEASED if not effect else batch.DEFERRED if effect==407 else batch.UNKNOWN if effect==408 else batch.REJECTED
                batch.ROW.pack_into(raw,batch.HEADER.size+i*batch.ROW.size,token,effect,outcome);completed=i+1
                if not effect:self.tokens.remove(token)
                if effect not in (0,407):error=effect;failed=i+1;break
        batch.HEADER.pack_into(raw,0,version,count,error,completed,len(self.tokens),failed)
        return {'lease_release_batch_packet':'bad' if self.bad_batch else raw.hex()}
class Tests(unittest.TestCase):
    def setUp(self):
        self.transport=BatchTransport();self.p=patch('expedition33.sdk.SessionTransport',return_value=self.transport);self.p.start();self.addCleanup(self.p.stop)
        self.session=Session(leases=True);self.addCleanup(self.session.close)
    def leases(self,n):return [self.session.retain(self.session._object) for _ in range(n)]
    def test_large_scope_uses_bounded_batches_after_owner_close(self):
        scope=SessionScope(self.session);leases=[scope.retain(self.session._object) for _ in range(544)]
        self.transport.calls.clear();scope.close()
        self.assertEqual(self.transport.calls,['lease-release-batch']*5)
        self.assertTrue(all(x._state=='released' for x in leases));self.assertFalse(self.session._leases)
    def test_scope_close_with_gc_deferred_retains_session_ownership_without_ack(self):
        scope=SessionScope(self.session);leases=[scope.retain(self.session._object) for _ in range(544)]
        deferred=leases[255];self.transport.effects[deferred._token]=407
        self.transport.calls.clear();result=scope.close()
        self.assertIsNone(result)  # Legacy scope close is not an ownership ACK.
        self.assertEqual(self.transport.calls,['lease-release-batch']*5)
        self.assertEqual(deferred._state,'pending_release');self.assertIn(deferred,self.session._leases)
        self.assertTrue(all(x._state=='released' for x in leases if x is not deferred))
        self.assertFalse(self.session._release_leases([deferred]))
        self.transport.effects.clear();self.session._release_pending_leases()
        self.assertEqual(deferred._state,'released');self.assertNotIn(deferred,self.session._leases)
    def test_deferred_tokens_remain_and_pending_poll_batches_only_known_deferred(self):
        leases=self.leases(4);self.transport.effects[leases[1]._token]=407
        self.assertFalse(self.session._release_leases(leases));self.assertEqual(leases[1]._state,'pending_release')
        self.assertEqual(len(self.session._leases),1);self.transport.effects.clear();self.transport.calls.clear()
        self.session._release_pending_leases();self.assertEqual(self.transport.calls,['lease-release-batch']);self.assertFalse(self.session._leases)
    def test_whole_list_native_protection_preflight_releases_nothing(self):
        leases=self.leases(3);self.transport.protected.add(leases[1]._token)
        with self.assertRaises(LeaseError) as caught:self.session._release_leases(leases)
        self.assertEqual(caught.exception.outcome,'not_dispatched');self.assertTrue(all(x._state=='active' for x in leases))
        self.assertEqual(len(self.transport.tokens),3)
    def test_unknown_partial_applies_confirmed_prefix_then_aborts_no_replay(self):
        leases=self.leases(3);self.transport.effects[leases[1]._token]=408;self.transport.calls.clear()
        with self.assertRaises(LeaseError):self.session._release_leases(leases)
        self.assertEqual(leases[0]._state,'released');self.assertNotIn(leases[0],self.session._leases)
        self.assertTrue(all(x._state=='unknown' for x in leases[1:]));self.assertEqual(self.transport.abort_count,1)
        self.assertEqual(self.transport.calls,['lease-release-batch'])
        with self.assertRaises(LeaseError):leases[1].release()
        self.assertEqual(self.transport.calls,['lease-release-batch'])
    def test_malformed_ack_after_release_marks_unknown_without_individual_fallback(self):
        leases=self.leases(3);self.transport.bad_batch=True;self.transport.calls.clear()
        with self.assertRaises(LeaseError):self.session._release_leases(leases)
        self.assertTrue(all(x._state=='unknown' for x in leases));self.assertEqual(self.transport.calls,['lease-release-batch'])
    def test_unknown_source_lease_prevents_any_batch_dispatch(self):
        leases=self.leases(3);leases[1]._state='unknown';self.transport.calls.clear()
        with self.assertRaises(LeaseError):self.session._release_leases(leases)
        self.assertFalse(self.transport.calls);self.assertEqual(leases[1]._state,'unknown')
    def test_legacy_capability_absent_preserves_individual_release(self):
        scope=SessionScope(self.session);leases=[scope.retain(self.session._object) for _ in range(3)]
        self.transport.lease_release_batch_protocol=0;self.transport.calls.clear();scope.close()
        self.assertEqual(self.transport.calls,['lease-release']*3);self.assertTrue(all(x._state=='released' for x in leases))
    def test_confirmed_target_exit_does_not_claim_native_release_ack(self):
        leases=self.leases(2);self.transport.calls.clear();self.transport.target_exit_code=0
        self.assertFalse(self.session._release_leases(leases));self.assertTrue(all(x._state=='target_exited' for x in leases));self.assertFalse(self.transport.calls)
    def test_pending_native_owner_blocks_batch_and_retains_ownership(self):
        scope=SessionScope(self.session);lease=scope.retain(self.session._object)
        class Owner:
            def close(self):return False
        scope._native_owners.append(Owner());self.transport.calls.clear()
        with self.assertRaises(RuntimeError):scope.close()
        self.assertNotIn('lease-release-batch',self.transport.calls);self.assertEqual(lease._state,'unknown')
    def test_decoder_rejects_token_echo_and_false_complete(self):
        sent=batch.request([1,2]);raw=bytearray(sent);batch.HEADER.pack_into(raw,0,1,2,0,1,0,0)
        batch.ROW.pack_into(raw,batch.HEADER.size,1,0,batch.RELEASED)
        with self.assertRaises(ValueError):batch.decode(sent,raw.hex())
        with self.assertRaises(ValueError):batch.request([1,1])
        raw=bytearray(sent);batch.HEADER.pack_into(raw,0,1,2,0,2,0,0)
        for i,t in enumerate([1,9]):batch.ROW.pack_into(raw,batch.HEADER.size+i*batch.ROW.size,t,0,batch.RELEASED)
        with self.assertRaises(ValueError):batch.decode(sent,raw.hex())
class TransportContractTests(unittest.TestCase):
    def transport(self,capability):
        from expedition33._session import SessionTransport
        transport=SessionTransport.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.lease_release_batch_protocol=capability;transport._process=SimpleNamespace(stdin=io.StringIO())
        transport._read=lambda:dict(event='session_response',command='lease-release-batch',closed=False)
        transport._abort=lambda:None
        return transport
    def test_command_requires_explicit_capability_and_validates_before_pipe(self):
        for capability in [0,True]:
            transport=self.transport(capability)
            with self.assertRaises(ValueError):transport._command('lease-release-batch',batch.request([1]))
            self.assertEqual(transport._process.stdin.getvalue(),'')
        transport=self.transport(1)
        with self.assertRaises(ValueError):transport._command('lease-release-batch',b'bad')
        self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_command_routes_one_exact_packet(self):
        transport=self.transport(1);sent=batch.request([1,2])
        transport._command('lease-release-batch',sent)
        self.assertEqual(transport._process.stdin.getvalue(),'lease-release-batch '+sent.hex()+'\n')
if __name__=='__main__':unittest.main()
