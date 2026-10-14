import struct
import unittest
from types import SimpleNamespace
from expedition33.procedural_mesh import Tetrahedron,validate_request,SIZE,HEADER
from expedition33._scope import SessionScope

class MeshTests(unittest.TestCase):
    def test_tint_gain_is_bounded_and_material_only(self):
        for gain in (0,1,16,64):
            p=bytearray(SIZE);HEADER.pack_into(p,0,3,5,0,0,17)
            struct.pack_into('<I',p,20980,gain);validate_request(bytes(p))
        for op,gain in ((5,65),(5,0xffffffff),(2,1),(6,1),(13,1)):
            p=bytearray(SIZE);HEADER.pack_into(p,0,3,op,0,0,17)
            struct.pack_into('<I',p,20980,gain)
            with self.assertRaises(ValueError):validate_request(bytes(p))
    def test_render_diagnostic_rejects_memory_and_mode_inputs(self):
        for op in (12,13):
            p=bytearray(SIZE);HEADER.pack_into(p,0,3,op,0,0,17);validate_request(bytes(p))
            for offset in (88,344,352,19808,20980):
                bad=p.copy();bad[offset]=1
                with self.assertRaises(ValueError):validate_request(bytes(bad))
            struct.pack_into('<I',p,20976,2)
            with self.assertRaises(ValueError):validate_request(bytes(p))
    def test_render_samples_reject_oversized_output(self):
        scope=self.scope();model=Tetrahedron(scope)
        def oversized(name,data):
            p=bytearray(data);struct.pack_into('<II',p,344,129,129)
            return {'mesh_packet':p.hex()}
        model.transport.command=oversized
        with self.assertRaisesRegex(RuntimeError,'sample bounds'):model.render_probe()
    def test_grounded_spawn_cannot_supply_hit_bytes_or_paths(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,7,0,0,17)
        validate_request(bytes(p))
        for offset in (56,344,19856,19952,20976):
            bad=p.copy();bad[offset]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))

    def test_section_upload_rejects_arbitrary_targets_and_section_overflow(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,6,0,0,17)
        p[19952:19956]='D:'.encode('utf-16le')
        validate_request(bytes(p))
        for offset in (88,19808,20980):
            bad=p.copy();bad[offset]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))
        struct.pack_into('<I',p,20976,64)
        with self.assertRaises(ValueError):validate_request(bytes(p))

    def test_wire_rejects_cleanup_targets_and_output_fields(self):
        p=bytearray(SIZE);HEADER.pack_into(p,0,3,2,0,0,17)
        validate_request(bytes(p))
        for offset in (24,40,56,80,84,88,327):
            bad=p.copy();bad[offset]=1
            with self.assertRaises(ValueError):validate_request(bytes(bad))
        with self.assertRaises(ValueError):validate_request(bytes(p[:-1]))

    def scope(self):
        self.calls=[]
        def command(name,data):
            validate_request(data);self.calls.append(HEADER.unpack_from(data)[1])
            return {'mesh_packet':data.hex()}
        session=SimpleNamespace(pid=9,_check=lambda:None,console=SimpleNamespace(),
            _transport=SimpleNamespace(mesh_protocol=3,command=command))
        return SessionScope(session)

    def test_revoked_scope_destroys_once(self):
        scope=self.scope();model=Tetrahedron(scope);model.created=True
        scope.close();scope.close();model.close()
        self.assertEqual(self.calls,[2]);self.assertTrue(model.closed)
        with self.assertRaises(RuntimeError):model.spawn()

    def test_foreign_owner_response_rejected(self):
        scope=self.scope();model=Tetrahedron(scope)
        def foreign(name,data):
            bad=bytearray(data);struct.pack_into('<Q',bad,16,model.owner^1)
            return {'mesh_packet':bad.hex()}
        model.transport.command=foreign
        with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):model._command(3)

    def test_status_accepts_only_bounded_handoff_outputs(self):
        scope=self.scope();model=Tetrahedron(scope)
        def status(name,data):
            result=bytearray(data)
            struct.pack_into('<iiQiiQ',result,88,20,30,400,21,31,500)
            struct.pack_into('<II',result,344,15,2)
            return {'mesh_packet':result.hex()}
        model.transport.command=status
        result=model._command(3)
        self.assertEqual(result['driver']['serial'],30)
        self.assertEqual((result['switch_ms'],result['switch_count']),(15,2))
        for offset in (120,343,352,19952):
            def corrupt(name,data,offset=offset):
                result=bytearray.fromhex(status(name,data)['mesh_packet']);result[offset]=1
                return {'mesh_packet':result.hex()}
            model.transport.command=corrupt
            with self.assertRaisesRegex(RuntimeError,'acknowledgement mismatch'):model._command(3)
