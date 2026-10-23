import io,struct,threading,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from expedition33._scope import SessionScope
from expedition33._session import SessionTransport
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_response,EnemyOperationError

class ArenaAssignmentTests(unittest.TestCase):
    def ids(self,count=4):return tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(count))
    def reply(self,request,actor=(31,1010,0x30000)):
        response=bytearray(request);struct.pack_into('<I',response,12,1)
        struct.pack_into('<iiQ',response,4096,*actor);struct.pack_into('<iiQ',response,4112,41,1020,0x40000)
        return response
    def scope(self,command,capability=1):
        transport=NS(enemy_spawn_protocol=1,enemy_arena_binding_protocol=capability,command=command)
        return SessionScope(NS(_transport=transport,_check=lambda:None,console=NS(dispatcher=NS(namespace={}))))
    def owner(self,scope):
        owner=EnemySpawnOwner(scope);owner._attempted=True;owner.phase='spawned';owner.actor_identity=(31,1010,0x30000)
        return owner
    def test_binding_journals_current_arena_identity_without_replacing_actor(self):
        command=Mock(side_effect=lambda name,request:dict(mesh_packet=self.reply(request).hex()))
        scope=self.scope(command);owner=self.owner(scope)
        owner.bind_arena(self.ids())
        self.assertEqual(owner.phase,'spawned');self.assertEqual(owner.actor_identity,(31,1010,0x30000))
        self.assertEqual(owner.arena_identity,(41,1020,0x40000));self.assertTrue(owner.has_native_work)
        with self.assertRaisesRegex(RuntimeError,'already bound'):owner.bind_arena(self.ids())
        self.assertEqual(command.call_count,1)
        owner._attempted=False;scope.close()
    def test_unavailable_capability_rejected_before_dispatch(self):
        for value in (0,2,True):
            command=Mock();scope=self.scope(command,value);owner=self.owner(scope)
            with self.assertRaisesRegex(RuntimeError,'capability unavailable'):owner.bind_arena(self.ids())
            command.assert_not_called();self.assertEqual(owner.phase,'spawned')
            owner._attempted=False;scope.close()
    def test_acknowledged_wrong_actor_is_not_adopted_or_replayed(self):
        scope=self.scope(Mock(side_effect=lambda name,request:dict(mesh_packet=self.reply(request,(99,1,0x90000)).hex())))
        owner=self.owner(scope)
        with self.assertRaisesRegex(RuntimeError,'different actor'):owner.bind_arena(self.ids())
        self.assertEqual(owner.phase,'unknown');self.assertEqual(owner.actor_identity,(31,1010,0x30000))
        self.assertIsNotNone(owner.last_response);self.assertIsNone(owner.arena_identity)
        owner._attempted=False;scope.close()
    def test_failure_preserves_owned_actor_and_prevents_replay(self):
        def fail(name,request):
            response=bytearray(request);struct.pack_into('<I',response,8,2956)
            return dict(mesh_packet=response.hex())
        command=Mock(side_effect=fail);scope=self.scope(command);owner=self.owner(scope)
        with self.assertRaises(EnemyOperationError):owner.bind_arena(self.ids())
        with self.assertRaisesRegex(RuntimeError,'lifecycle'):owner.bind_arena(self.ids())
        self.assertEqual(command.call_count,1);self.assertEqual(owner.actor_identity,(31,1010,0x30000))
        owner._attempted=False;scope.close()
    def test_old_transport_rejects_before_pipe_write(self):
        transport=object.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=1;transport.enemy_arena_binding_protocol=0
        transport._process=NS(stdin=io.StringIO())
        with self.assertRaises(ValueError):transport._command('mesh',build_request(123,118,self.ids()))
        self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_exact_acknowledgement_bounds(self):
        request=build_request(123,118,self.ids());response=self.reply(request)
        self.assertTrue(validate_response(request,bytes(response)))
        for offset in (88,4128,len(response)-1):
            bad=bytearray(response);bad[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
        for offset in (4096,4112):
            bad=bytearray(response);bad[offset:offset+16]=bytes(16)
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
