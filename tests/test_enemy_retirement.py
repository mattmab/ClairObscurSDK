import struct
import unittest
from types import SimpleNamespace as NS
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import EnemyCleanupDeferred,EnemyOperationError

class Transport:
    enemy_spawn_protocol=3
    def __init__(self):self.calls=[];self.defer=True;self.corrupt=False;self.defer_spawn=False
    def command(self,name,request):
        op=struct.unpack_from('<I',request,4)[0];self.calls.append(op);reply=bytearray(request)
        if op==111 and self.defer or op==110 and self.defer_spawn:
            struct.pack_into('<I',reply,8,407)
            if self.corrupt:reply[-1]=1
        else:
            struct.pack_into('<I',reply,12,0 if op==111 else 1)
            if op in (110,112):struct.pack_into('<iiQ',reply,4096,10,1001,0x20000)
        return dict(mesh_packet=reply.hex())

class EnemyRetirementTests(unittest.TestCase):
    def setUp(self):
        self.transport=Transport();self.aborted=False
        self.scope=SessionScope(NS(_transport=self.transport,_check=lambda:None,
            console=NS(dispatcher=NS(namespace={})),_abort_ownership=self.abort))
        self.ids=tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(12))
        self.pose=(0,0,0,1,100,200,300,0,1,1,1,0)
        self.owner=EnemySpawnOwner(self.scope)
    def abort(self):self.aborted=True
    def test_acknowledged_deferral_retains_owner_and_can_complete_later(self):
        self.owner.spawn(self.ids,self.pose);identity=self.owner.actor_identity
        with self.assertRaises(EnemyCleanupDeferred):self.owner.remove()
        self.assertEqual(self.owner.phase,'spawned');self.assertEqual(self.owner.actor_identity,identity)
        self.assertTrue(self.owner.has_native_work);self.assertFalse(self.owner._closed)
        self.assertIs(self.transport._enemy_spawn_owner,self.owner)
        self.transport.defer=False;self.assertTrue(self.owner.close())
        self.assertEqual(self.transport.calls,[110,111,111]);self.assertEqual(self.owner.phase,'closed')
    def test_scope_revocation_hands_deferred_cleanup_to_native_watcher(self):
        self.owner.spawn(self.ids,self.pose)
        with self.assertRaisesRegex(RuntimeError,'native enemy cleanup deferred'):self.scope.close()
        self.assertTrue(self.aborted);self.assertEqual(self.transport.calls,[110,111])
        self.assertTrue(self.owner.has_native_work);self.assertFalse(self.owner._closed)
    def test_corrupt_deferred_acknowledgement_is_unknown_not_retryable(self):
        self.owner.spawn(self.ids,self.pose);self.transport.corrupt=True
        with self.assertRaises(RuntimeError) as error:self.owner.remove()
        self.assertNotIsInstance(error.exception,EnemyCleanupDeferred)
        self.assertEqual(self.owner.phase,'cleanup_unknown')
        with self.assertRaises(RuntimeError):self.owner.close()
        self.assertEqual(self.transport.calls,[110,111])
    def test_deferral_code_on_spawn_is_not_safe_cleanup_deferral(self):
        self.transport.defer_spawn=True
        with self.assertRaises(EnemyOperationError) as error:self.owner.spawn(self.ids,self.pose)
        self.assertNotIsInstance(error.exception,EnemyCleanupDeferred)
        self.assertEqual(self.owner.phase,'unknown')
    def test_unsupported_scope_does_not_reserve_shared_owner(self):
        self.owner.close()
        old_scope=NS(_check=lambda:None,_session=NS(_transport=self.transport))
        with self.assertRaisesRegex(RuntimeError,'scope does not support'):EnemySpawnOwner(old_scope)
        self.assertIsNone(self.transport._enemy_spawn_owner);self.assertEqual(self.transport.calls,[])
