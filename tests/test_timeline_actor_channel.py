import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33._timeline_actor_channel import TimelineActorOwner,validate_count,validate_request,_operation,REVERSE
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import EnemyOperationError,build_request
from expedition33._scope import SessionScope
from test_timeline_blueprint_actor import TimelineTransport


class PoolTransport(TimelineTransport):
    timeline_actor_pool_protocol=1
    def __init__(self):super().__init__();self.pool_calls=[];self.failure=0;self.corrupt=False
    def command(self,name,packet):
        op=struct.unpack_from('<I',packet,4)[0]
        if op not in REVERSE:return super().command(name,packet)
        self.pool_calls.append(op);validate_request(packet)
        if self.failure:
            response=bytearray(packet);struct.pack_into('<I',response,8,self.failure)
            if self.corrupt:response[-1]=1
            return dict(mesh_packet=response.hex())
        response=super().command(name,_operation(packet,REVERSE[op]))
        return dict(response,mesh_packet=_operation(bytes.fromhex(response['mesh_packet']),op).hex())


class TimelineActorChannelTests(unittest.TestCase):
    def scope(self,transport):
        return SessionScope(N(_transport=transport,_check=lambda:None,console=N(dispatcher=N(namespace={})),_abort_ownership=Mock()))
    def spawn(self,owner):
        ids=tuple(N(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(13))
        owner.spawn_timeline_prepared(ids,(0,0,0,1,0,0,0,0,1,1,1,0))
    def test_distinct_timeline_owners_coexist_with_legacy_encounter_owner(self):
        transport=PoolTransport();scope=self.scope(transport)
        encounter=EnemySpawnOwner(scope);first=TimelineActorOwner(scope);second=TimelineActorOwner(scope)
        self.spawn(first);self.spawn(second);first.reveal_timeline();second.reveal_timeline()
        self.assertIs(transport._enemy_spawn_owner,encounter)
        self.assertTrue(first.close());self.assertFalse(second._closed)
        self.assertTrue(second.close());self.assertTrue(encounter.close())
        self.assertEqual(transport.pool_calls,[223,223,224,224,225,225])
    def test_exact_capacity_rejection_needs_no_native_retirement(self):
        transport=PoolTransport();transport.failure=3769;owner=TimelineActorOwner(self.scope(transport))
        with self.assertRaises(EnemyOperationError):self.spawn(owner)
        self.assertFalse(owner.has_native_work);self.assertTrue(owner.close())
        self.assertEqual(transport.pool_calls,[223])
    def test_duplicate_and_malformed_capacity_ack_preserve_uncertain_ownership(self):
        for error,corrupt in ((3773,False),(3769,True)):
            transport=PoolTransport();transport.failure=error;transport.corrupt=corrupt
            owner=TimelineActorOwner(self.scope(transport))
            with self.assertRaises(RuntimeError):self.spawn(owner)
            self.assertTrue(owner.has_native_work);self.assertEqual(owner.phase,'unknown')
            self.assertEqual(transport.pool_calls,[223])
    def test_only_reviewed_channel_operations_and_strict_capabilities(self):
        packet=build_request(123,111)
        with self.assertRaises(ValueError):validate_request(packet)
        for cap in (True,'1',2):
            transport=PoolTransport();transport.timeline_actor_pool_protocol=cap
            with self.assertRaises(RuntimeError):TimelineActorOwner(self.scope(transport))
            with self.assertRaises(RuntimeError):validate_count([],transport)
        validate_count([None]*32,N(timeline_actor_pool_protocol=1))
        with self.assertRaises(ValueError):validate_count([None]*33,N(timeline_actor_pool_protocol=1))
        with self.assertRaises(ValueError):validate_count([None]*2,None)
