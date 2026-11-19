import struct,unittest
from types import SimpleNamespace
from expedition33 import _story_action_wire as wire

def held(index):return SimpleNamespace(object=SimpleNamespace(index=index,serial=4,address=0x10000+index*8),_token=index+1)
def packet(mode=0,after=0):return wire.encode(99,held(1),held(2),(held(3),held(4)),'e33c5701'+'12345678'*3,mode=mode,after=after)

class StoryActionTests(unittest.TestCase):
    def test_owner_registers_with_real_scope_before_any_native_dispatch(self):
        from expedition33._scope import SessionScope
        from expedition33.story_actions import ActionCompletions
        session=SimpleNamespace(_check=lambda:None,_transport=SimpleNamespace(story_action_completion_protocol=1),console=SimpleNamespace(dispatcher=SimpleNamespace(namespace={})))
        parent=SessionScope(session)
        owner=ActionCompletions(parent)
        self.assertIs(owner._scope,parent)
        self.assertIn(owner,parent._native_owners)
        self.assertIn(owner,parent._close_first)
        self.assertTrue(owner.close())
    def test_transport_routes_only_advertised_protocol(self):
        from test_menu_transport import MenuTransportTests
        for capability in (0,True,2,1):
            t=MenuTransportTests().transport();t.mesh_protocol=3;t.story_action_completion_protocol=capability
            t._read=lambda:dict(event='session_response',command='mesh',closed=False)
            if type(capability) is int and capability==1:
                t.command('mesh',packet());self.assertEqual(t._process.stdin.getvalue(),'mesh '+packet().hex()+'\n')
            else:
                with self.assertRaises(ValueError):t.command('mesh',packet())
                self.assertEqual(t._process.stdin.getvalue(),'')
    def test_correlated_ordered_receipts(self):
        p=packet(1,after=7);r=bytearray(p);struct.pack_into('<I',r,12,2);struct.pack_into('<I',r,296,1)
        struct.pack_into('<QIIiiQ',r,304,8,1,0,200,3,0x30000)
        self.assertEqual(wire.decode(p,bytes(r)),(dict(sequence=8,source=1,world=(200,3,0x30000)),))
        struct.pack_into('<Q',r,304,7)
        with self.assertRaises(RuntimeError):wire.decode(p,bytes(r))
    def test_cannot_change_save_or_source(self):
        p=packet();r=bytearray(p);struct.pack_into('<I',r,12,1)
        self.assertEqual(wire.decode(p,bytes(r)),())
        r[76]^=1
        with self.assertRaises(RuntimeError):wire.decode(p,bytes(r))
    def test_rejects_unused_sources_and_receipt_payload_in_request(self):
        for at in (144,296,304,20983):
            p=bytearray(packet());p[at]=1
            with self.assertRaises(ValueError):wire.validate(bytes(p))

if __name__=='__main__':unittest.main()
