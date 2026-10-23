import io,struct,threading,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from expedition33._session import SessionTransport
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_response,EnemyOperationError


class EnemyArenaNativeTests(unittest.TestCase):
    def ids(self):return tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(5))
    def reply(self,request):
        reply=bytearray(request);struct.pack_into('<I',reply,12,1)
        struct.pack_into('<2Q4I',reply,4096,15,7,7,0,17,0)
        return reply
    def scope(self,command,capability=1):
        transport=NS(enemy_spawn_protocol=1,enemy_arena_protocol=capability,command=command)
        return SessionScope(NS(_transport=transport,_check=lambda:None,console=NS(dispatcher=NS(namespace={}))))
    def test_observation_does_not_claim_actor_or_cleanup(self):
        calls=[]
        def command(name,request):
            calls.append(struct.unpack_from('<I',request,4)[0]);return dict(mesh_packet=self.reply(request).hex())
        scope=self.scope(command);owner=EnemySpawnOwner(scope)
        owner.inspect_arena_assembly(self.ids())
        self.assertEqual(owner.phase,'ready');self.assertFalse(owner.has_native_work);self.assertIsNone(owner.actor_identity)
        scope.close();self.assertEqual(calls,[117])
    def test_read_failure_preserves_ready_without_retry(self):
        def command(name,request):
            response=bytearray(request);struct.pack_into('<I',response,8,2945)
            return dict(mesh_packet=response.hex())
        scope=self.scope(Mock(side_effect=command));owner=EnemySpawnOwner(scope)
        with self.assertRaises(EnemyOperationError):owner.inspect_arena_assembly(self.ids())
        self.assertEqual(owner.phase,'ready');self.assertFalse(owner.has_native_work)
        self.assertEqual(scope._session._transport.command.call_count,1);scope.close()
    def test_missing_capability_rejects_before_dispatch(self):
        for value in (0,2,True):
            command=Mock();scope=self.scope(command,value);owner=EnemySpawnOwner(scope)
            with self.assertRaisesRegex(RuntimeError,'capability unavailable'):owner.inspect_arena_assembly(self.ids())
            command.assert_not_called();scope.close()
    def test_old_transport_rejects_before_pipe_write(self):
        transport=object.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=1;transport.enemy_arena_protocol=0
        transport._process=NS(stdin=io.StringIO())
        with self.assertRaises(ValueError):transport._command('mesh',build_request(123,117,self.ids()))
        self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_exact_response_rejects_corruption_and_impossible_counts(self):
        request=build_request(123,117,self.ids());reply=self.reply(request)
        self.assertTrue(validate_response(request,bytes(reply)))
        for offset in (88,4128,len(reply)-1):
            bad=bytearray(reply);bad[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
        for offset,value in ((4096,0),(4104,0),(4112,6),(4116,2),(4120,16),(4124,1)):
            bad=bytearray(reply);struct.pack_into('<I',bad,offset,value)
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
