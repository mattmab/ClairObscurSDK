import io,struct,unittest
from types import SimpleNamespace as N
from expedition33._session import SessionTransport
from expedition33.procedural_mesh import validate_request

def packet():
    raw=bytearray(20984);struct.pack_into('<4IQ',raw,0,3,68,0,0,42);return bytes(raw)

class BuilderRetirementWireTests(unittest.TestCase):
    def transport(self,cap):
        t=SessionTransport.__new__(SessionTransport)
        t._check_thread=lambda:None;t._closed=False;t.mesh_protocol=3
        t.builder_world_retirement_protocol=cap
        t._process=N(stdin=io.StringIO())
        t._read=lambda:dict(event='session_response',command='mesh',closed=False)
        return t
    def test_empty_retirement_request_is_bounded(self):
        validate_request(packet())
        raw=bytearray(packet());raw[88]=1
        with self.assertRaises(ValueError):validate_request(bytes(raw))
    def test_missing_or_boolean_capability_never_sends(self):
        for cap in (0,False,True,2):
            t=self.transport(cap)
            with self.assertRaisesRegex(ValueError,'World Builder retirement'):t.command('mesh',packet())
            self.assertEqual(t._process.stdin.getvalue(),'')
    def test_advertised_capability_routes_through_mesh_validation(self):
        t=self.transport(1);t.command('mesh',packet())
        self.assertTrue(t._process.stdin.getvalue().startswith('mesh '))

if __name__=='__main__':unittest.main()
