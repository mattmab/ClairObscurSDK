import struct
import unittest
from types import SimpleNamespace
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner

class Transport:
    enemy_spawn_protocol=3
    def __init__(self):self.calls=[];self.fail=None
    def command(self,name,request):
        op=struct.unpack_from('<I',request,4)[0];self.calls.append(op)
        if self.fail==op:raise OSError('Unknown dispatch outcome')
        reply=bytearray(request);struct.pack_into('<I',reply,12,0 if op==111 else 1)
        if op in (110,112):struct.pack_into('<iiQ',reply,4096,10,1001,0x20000)
        return dict(mesh_packet=reply.hex())

class EnemySpawnOwnerTests(unittest.TestCase):
    def setUp(self):
        self.transport=Transport();self.aborted=False
        session=SimpleNamespace(_transport=self.transport,_check=lambda:None,
            console=SimpleNamespace(dispatcher=SimpleNamespace(namespace={})),_abort_ownership=self.abort)
        self.scope=SessionScope(session)
        self.ids=tuple(SimpleNamespace(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(12))
        self.pose=(0,0,0,1,100,200,300,0,1,1,1,0)
    def abort(self):self.aborted=True
    def test_acknowledgement_is_owned_before_caller_readback(self):
        owner=EnemySpawnOwner(self.scope);raw=owner.spawn(self.ids,self.pose)
        self.assertEqual(owner.actor_identity,(10,1001,0x20000));self.assertEqual(owner.last_response,raw)
        self.assertEqual(owner.phase,'spawned')
        self.scope.close();self.assertEqual(self.transport.calls,[110,111]);self.assertEqual(owner.phase,'closed')
    def test_unknown_spawn_is_not_replayed_and_can_be_cleaned(self):
        owner=EnemySpawnOwner(self.scope);self.transport.fail=110
        with self.assertRaises(OSError):owner.spawn(self.ids,self.pose)
        with self.assertRaises(RuntimeError):owner.spawn(self.ids,self.pose)
        self.assertEqual(owner.phase,'unknown');self.assertTrue(owner.has_native_work)
        self.scope.close();self.assertEqual(self.transport.calls,[110,111])
    def test_scope_cleanup_failure_escalates_native_ownership_without_replay(self):
        owner=EnemySpawnOwner(self.scope);owner.spawn(self.ids,self.pose);self.transport.fail=111
        with self.assertRaises(RuntimeError):self.scope.close()
        self.assertTrue(self.aborted);self.assertEqual(owner.phase,'cleanup_unknown')
        with self.assertRaises(RuntimeError):owner.close()
        self.assertEqual(self.transport.calls,[110,111])
    def test_one_owner_per_shared_session_and_unspawned_close_is_local(self):
        owner=EnemySpawnOwner(self.scope)
        with self.assertRaises(RuntimeError):EnemySpawnOwner(self.scope)
        owner.close();owner.close();self.assertEqual(self.transport.calls,[])
        replacement=EnemySpawnOwner(self.scope);replacement.close()
    def test_invalid_input_never_marks_dispatch_or_requires_cleanup(self):
        owner=EnemySpawnOwner(self.scope)
        with self.assertRaises(ValueError):owner.spawn(self.ids[:-1],self.pose)
        self.assertEqual(owner.phase,'ready');self.assertFalse(owner.has_native_work)
        self.scope.close();self.assertEqual(self.transport.calls,[])
    def test_remove_allows_a_new_owned_spawn_without_new_transport(self):
        owner=EnemySpawnOwner(self.scope);owner.spawn(self.ids,self.pose);owner.remove()
        self.assertIsNone(owner.actor_identity);owner.spawn(self.ids,self.pose);self.scope.close()
        self.assertEqual(self.transport.calls,[110,111,110,111])
    def test_initialization_order_and_capabilities_are_checked(self):
        owner=EnemySpawnOwner(self.scope)
        with self.assertRaises(RuntimeError):owner.activate(self.ids[0])
        owner.spawn(self.ids,self.pose);owner.initialize(*self.ids[:2]);owner.activate(self.ids[0])
        with self.assertRaises(RuntimeError):owner.initialize(*self.ids[:2])
        self.scope.close();self.assertEqual(self.transport.calls,[110,112,113,111])
