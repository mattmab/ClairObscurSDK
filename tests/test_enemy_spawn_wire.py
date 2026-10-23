import io
import struct
import threading
import unittest
from types import SimpleNamespace
from expedition33._enemy_spawn_wire import validate_request,SIZE,OPERATIONS
from expedition33._session import SessionTransport


def packet(operation):
    data=bytearray(SIZE)
    struct.pack_into('<4IQ',data,0,3,operation,0,0,123)
    for i in range(OPERATIONS[operation]):struct.pack_into('<iiQ',data,88+i*16,i+1,i+2,0x10000+i*0x100)
    if operation in (110,120,133):struct.pack_into('<12d',data,2000,0,0,0,1,100,200,300,0,1,1,1,0)
    if operation==119:struct.pack_into('<6d',data,2000,0,0,100,50,50,50)
    if operation==122:struct.pack_into('<I',data,32,10)
    if operation==133:struct.pack_into('<I',data,32,1)
    return bytes(data)


class EnemySpawnWireTests(unittest.TestCase):
    def transport(self,capability=3):
        t=object.__new__(SessionTransport)
        t._owner=threading.get_ident();t._closed=False;t.mesh_protocol=3;t.enemy_spawn_protocol=capability;t.enemy_pose_protocol=1;t.enemy_arena_protocol=1;t.enemy_arena_binding_protocol=1;t.enemy_clearance_protocol=1;t.enemy_grounded_spawn_protocol=2;t.enemy_extra_spots_protocol=1
        t._process=SimpleNamespace(stdin=io.StringIO())
        t.enemy_combat_placement_protocol=1
        t.enemy_helper_lookup_research_protocol=1;t.enemy_geometry_placement_research_protocol=1;t.enemy_authored_encounter_research_protocol=7
        t._read=lambda:dict(event='session_response',command='mesh',closed=False)
        return t

    def test_all_owned_operations_route_through_validated_transport(self):
        for op in OPERATIONS:
            with self.subTest(operation=op):
                t=self.transport();t._command('mesh',packet(op))
                self.assertEqual(t._process.stdin.getvalue(),'mesh '+packet(op).hex()+'\n')

    def test_combat_placement_requires_its_negotiated_capability(self):
        for capability in (0,True,2):
            t=self.transport();t.enemy_combat_placement_protocol=capability
            with self.assertRaises(ValueError):t._command('mesh',packet(123))
            self.assertEqual(t._process.stdin.getvalue(),'')

    def test_missing_research_capabilities_reject_without_transport_write(self):
        for operation,name in ((131,'enemy_helper_lookup_research_protocol'),
                (132,'enemy_geometry_placement_research_protocol'),(133,'enemy_authored_encounter_research_protocol')):
            with self.subTest(operation=operation):
                t=self.transport();delattr(t,name)
                with self.assertRaises(ValueError):t._command('mesh',packet(operation))
                self.assertEqual(t._process.stdin.getvalue(),'')

    def test_original_capability_accepts_original_ops_but_rejects_visual_tick(self):
        for op in (110,111,112,113):self.transport(1)._command('mesh',packet(op))
        t=self.transport(1)
        with self.assertRaises(ValueError):t._command('mesh',packet(114))
        self.assertEqual(t._process.stdin.getvalue(),'')

    def test_old_runtime_cannot_accept_new_adapter_requests(self):
        t=self.transport(0)
        with self.assertRaises(ValueError):t._command('mesh',packet(110))
        self.assertEqual(t._process.stdin.getvalue(),'')

    def test_corrupt_requests_do_not_reach_pipe(self):
        for offset in (0,8,12,24,72,4096,SIZE-1):
            with self.subTest(offset=offset):
                data=bytearray(packet(110));data[offset]^=1
                t=self.transport()
                with self.assertRaises(ValueError):t._command('mesh',bytes(data))
                self.assertEqual(t._process.stdin.getvalue(),'')

    def test_invalid_policy_and_pose_are_rejected(self):
        invalid=[]
        data=bytearray(packet(112));struct.pack_into('<I',data,32,2);invalid.append(bytes(data))
        data=bytearray(packet(110));struct.pack_into('<d',data,2000,float('nan'));invalid.append(bytes(data))
        data=bytearray(packet(110));struct.pack_into('<d',data,2064,5);invalid.append(bytes(data))
        for data in invalid:
            with self.assertRaises(ValueError):validate_request(data)


if __name__=='__main__':unittest.main()
