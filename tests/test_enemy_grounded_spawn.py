import io,struct,threading,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33._session import SessionTransport
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_response,EnemyOperationError
from expedition33.enemy_spawning import EnemySpawner

class GroundedSpawnTests(unittest.TestCase):
    def ids(self,n):return tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(n))
    pose=(0,0,0,1,1600,500,50000,0,1,1,1,0)
    def scope(self,command,capability=2):
        transport=NS(enemy_spawn_protocol=1,enemy_grounded_spawn_protocol=capability,enemy_retirement_protocol=1,
                     enemy_pose_protocol=1,enemy_arena_binding_protocol=1,command=command)
        return SessionScope(NS(_transport=transport,_check=lambda:None,console=NS(dispatcher=NS(namespace={}))))
    def response(self,request):
        response=bytearray(request);op=struct.unpack_from('<I',request,4)[0]
        struct.pack_into('<I',response,12,0 if op==111 else 1)
        if op in (120,112,118):struct.pack_into('<iiQ',response,4096,31,1010,0x30000)
        if op==118:struct.pack_into('<iiQ',response,4112,41,1020,0x40000)
        if op==121:struct.pack_into('<2d',response,4096+28*8,9,1)
        return dict(mesh_packet=response.hex())
    def test_prepared_flow_requires_ground_and_arena_before_initialization(self):
        command=Mock(side_effect=lambda name,request:self.response(request));scope=self.scope(command);owner=EnemySpawnOwner(scope)
        owner.spawn_prepared(self.ids(13),self.pose)
        with self.assertRaisesRegex(RuntimeError,'requires'):owner.initialize(*self.ids(2))
        owner.place_prepared(self.ids(9))
        with self.assertRaisesRegex(RuntimeError,'requires'):owner.initialize(*self.ids(2))
        with self.assertRaisesRegex(RuntimeError,'already placed'):owner.place_prepared(self.ids(9))
        owner.bind_arena(self.ids(4));owner.initialize(*self.ids(2));owner.activate(self.ids(1)[0])
        self.assertEqual(owner.phase,'active');scope.close()
        self.assertEqual([struct.unpack_from('<I',c.args[1],4)[0] for c in command.call_args_list],[120,121,118,112,113,111])
    def test_failed_ground_check_preserves_actor_for_cleanup_without_replay(self):
        def command(name,request):
            if struct.unpack_from('<I',request,4)[0]==121:
                response=bytearray(request);struct.pack_into('<I',response,8,2974);return dict(mesh_packet=response.hex())
            return self.response(request)
        command=Mock(side_effect=command);scope=self.scope(command);owner=EnemySpawnOwner(scope)
        owner.spawn_prepared(self.ids(13),self.pose)
        with self.assertRaises(EnemyOperationError):owner.place_prepared(self.ids(9))
        self.assertEqual(owner.phase,'unknown');self.assertEqual(owner.actor_identity,(31,1010,0x30000))
        with self.assertRaisesRegex(RuntimeError,'lifecycle'):owner.place_prepared(self.ids(9))
        scope.close();self.assertEqual(command.call_count,3)
    def test_old_capability_rejects_before_attempt(self):
        for capability in (0,1,True):
            command=Mock();scope=self.scope(command,capability);owner=EnemySpawnOwner(scope)
            with self.assertRaisesRegex(RuntimeError,'capability unavailable'):owner.spawn_prepared(self.ids(13),self.pose)
            self.assertFalse(owner.has_native_work);command.assert_not_called();scope.close()
    def test_ground_result_bounds_and_reserved_bytes(self):
        request=build_request(123,121,self.ids(9));response=bytes.fromhex(self.response(request)['mesh_packet'])
        self.assertTrue(validate_response(request,response))
        for offset in (88,4336,len(response)-1):
            bad=bytearray(response);bad[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
        for at,value in ((0,float('nan')),(28,0),(29,0)):
            bad=bytearray(response);struct.pack_into('<d',bad,4096+at*8,value)
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
    def test_public_grounded_request_needs_arena_before_loading(self):
        scope=self.scope(Mock());service=EnemySpawner(scope)
        with patch('expedition33.enemy_spawning.controller_context') as context:
            with self.assertRaisesRegex(ValueError,'arena identity'):service.spawn('unused',grounded=True)
            context.assert_not_called()
        service.close();scope.close()

    def test_old_grounded_native_contract_is_rejected_before_pipe_write(self):
        transport=object.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=1;transport.enemy_grounded_spawn_protocol=1
        transport._process=NS(stdin=io.StringIO())
        with self.assertRaises(ValueError):transport._command('mesh',build_request(123,121,self.ids(9)))
        self.assertEqual(transport._process.stdin.getvalue(),'')
