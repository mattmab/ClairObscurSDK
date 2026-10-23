import io,struct,threading,unittest
from types import SimpleNamespace as NS
from expedition33._session import SessionTransport
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from expedition33._enemy_spawn_wire import build_request,validate_response

class EnemyPoseTests(unittest.TestCase):
    def ids(self):return tuple(NS(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(14))
    def test_pose_query_has_no_actor_ownership_or_cleanup_side_effect(self):
        calls=[]
        def command(name,request):
            calls.append(struct.unpack_from('<I',request,4)[0]);reply=bytearray(request)
            struct.pack_into('<I',reply,12,1);struct.pack_into('<6d',reply,4096,10,20,30,0,90,0)
            return dict(mesh_packet=reply.hex())
        transport=NS(enemy_spawn_protocol=1,enemy_pose_protocol=1,command=command)
        scope=SessionScope(NS(_transport=transport,_check=lambda:None,console=NS(dispatcher=NS(namespace={}))))
        owner=EnemySpawnOwner(scope);raw=owner.pawn_pose(self.ids())
        self.assertEqual(struct.unpack_from('<6d',raw,4096),(10,20,30,0,90,0))
        self.assertEqual(owner.phase,'ready');self.assertFalse(owner.has_native_work);self.assertIsNone(owner.actor_identity)
        scope.close();self.assertEqual(calls,[116])
    def test_old_native_runtime_rejects_pose_query_before_pipe_write(self):
        transport=object.__new__(SessionTransport);transport._owner=threading.get_ident();transport._closed=False
        transport.mesh_protocol=3;transport.enemy_spawn_protocol=1;transport.enemy_pose_protocol=0
        transport._process=NS(stdin=io.StringIO())
        with self.assertRaises(ValueError):transport._command('mesh',build_request(123,116,self.ids()))
        self.assertEqual(transport._process.stdin.getvalue(),'')
    def test_pose_result_cannot_modify_inputs_reserved_bytes_or_return_nonfinite(self):
        request=build_request(123,116,self.ids());reply=bytearray(request);struct.pack_into('<I',reply,12,1)
        self.assertTrue(validate_response(request,bytes(reply)))
        for offset in (88,4144,len(reply)-1):
            bad=bytearray(reply);bad[offset]^=1
            with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
        bad=bytearray(reply);struct.pack_into('<d',bad,4096,float('nan'))
        with self.assertRaises(RuntimeError):validate_response(request,bytes(bad))
