import io,struct,threading,unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33._scope import SessionScope
from expedition33._session import SessionTransport
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_response,EnemyOperationError
from expedition33.enemy_spawning import EnemySpawner

class EnemyClearanceTests(unittest.TestCase):
    def ids(self):return tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(6))
    def scope(self,command,capability=1):
        transport=NS(enemy_spawn_protocol=1,enemy_pose_protocol=1,enemy_retirement_protocol=1,enemy_clearance_protocol=capability,command=command)
        return SessionScope(NS(_transport=transport,_check=lambda:None,console=NS(dispatcher=NS(namespace={}))))
    def test_read_query_does_not_claim_actor_or_cleanup(self):
        def command(name,request):
            response=bytearray(request);struct.pack_into('<I',response,12,1);struct.pack_into('<I',response,4096,1)
            return dict(mesh_packet=response.hex())
        command=Mock(side_effect=command);scope=self.scope(command);owner=EnemySpawnOwner(scope)
        raw=owner.inspect_clearance(self.ids(),(10,20,30,40,50,60))
        self.assertEqual(struct.unpack_from('<I',raw,4096)[0],1)
        self.assertEqual(owner.phase,'ready');self.assertFalse(owner.has_native_work);self.assertIsNone(owner.actor_identity)
        scope.close();self.assertEqual(command.call_count,1)
    def test_read_failure_stays_ready_and_is_not_retried(self):
        def command(name,request):
            response=bytearray(request);struct.pack_into('<I',response,8,2961)
            return dict(mesh_packet=response.hex())
        command=Mock(side_effect=command);scope=self.scope(command);owner=EnemySpawnOwner(scope)
        with self.assertRaises(EnemyOperationError):owner.inspect_clearance(self.ids(),(10,20,30,40,50,60))
        self.assertEqual(owner.phase,'ready');scope.close();self.assertEqual(command.call_count,1)
    def test_invalid_volume_never_dispatches(self):
        command=Mock();scope=self.scope(command);owner=EnemySpawnOwner(scope)
        for probe in ((0,0,0,0,1,1),(0,0,0,-1,1,1),(float('nan'),0,0,1,1,1),(0,0,0,1e6,1,1)):
            with self.assertRaises(ValueError):owner.inspect_clearance(self.ids(),probe)
        command.assert_not_called();scope.close()
    def test_exact_acknowledgement_and_boolean_result(self):
        request=build_request(123,119,self.ids(),(0,0,100,50,50,50))
        response=bytearray(request);struct.pack_into('<I',response,12,1)
        self.assertTrue(validate_response(request,bytes(response)))
        for offset in (88,2000,4100,len(response)-1):
            bad=bytearray(response);bad[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
        struct.pack_into('<I',response,4096,2)
        with self.assertRaises(RuntimeError):validate_response(request,bytes(response))
    def test_capability_is_required_before_dispatch(self):
        for value in (0,2,True):
            command=Mock();scope=self.scope(command,value);owner=EnemySpawnOwner(scope)
            with self.assertRaisesRegex(RuntimeError,'capability unavailable'):owner.inspect_clearance(self.ids(),(0,0,0,1,1,1))
            command.assert_not_called();scope.close()
    def test_old_transport_rejects_before_pipe_write(self):
        transport=object.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=1;transport.enemy_clearance_protocol=0
        transport._process=NS(stdin=io.StringIO())
        with self.assertRaises(ValueError):transport._command('mesh',build_request(123,119,self.ids(),(0,0,0,1,1,1)))
        self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_public_invalid_volume_rejects_before_context_read(self):
        scope=self.scope(Mock());service=EnemySpawner(scope)
        with patch('expedition33.enemy_spawning.controller_context') as context:
            with self.assertRaises(ValueError):service.inspect_placement_clearance((0,0,0),(0,1,1))
            context.assert_not_called()
        service.close();scope.close()
