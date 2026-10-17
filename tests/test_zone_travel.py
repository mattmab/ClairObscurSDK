import sys,struct,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from expedition33 import zone_travel as z
from expedition33.invocation import InvocationError

class ZoneTests(unittest.TestCase):
    def packet(self):
        p=bytearray(z.SIZE);z.HEADER.pack_into(p,0,1,1,0,0)
        for i in range(6):z.IDENTITY.pack_into(p,16+i*16,i,1,0x1000+i*8)
        for at,w,s in ((112,96,'Test'),(208,96,'Level_Test'),(304,128,'Level.SpawnPoint.Test.Entry')):p[at:at+w]=s.encode().ljust(w,b'\0')
        return bytes(p)
    def test_valid_packet(self):z.validate_request(self.packet())
    def test_invalid_inputs(self):
        for at,data in ((0,b'\x02'),(4,b'\x02'),(8,b'\x01'),(16,b'\xff'*4),(112,b';quit'),(207,b'x')):
            p=bytearray(self.packet());p[at:at+len(data)]=data
            with self.assertRaises(ValueError):z.validate_request(bytes(p))
    def test_reply_correlation(self):
        sent=self.packet();p=bytearray(sent);struct.pack_into('<I',p,8,1)
        self.assertEqual(z.decode_reply(sent,{'zone_packet':p.hex()})['outcome'],'dispatch_returned')
        p[112]=ord('X')
        with self.assertRaises(InvocationError) as e:z.decode_reply(sent,{'zone_packet':p.hex()})
        self.assertEqual(e.exception.outcome,'unknown')
    def test_dispatch_outcome(self):
        for outcome,expected in ((0,'not_dispatched'),(2,'unknown')):
            p=bytearray(self.packet());struct.pack_into('<II',p,8,outcome,1810)
            with self.assertRaises(InvocationError) as e:z.decode_reply(self.packet(),{'zone_packet':p.hex()})
            self.assertEqual(e.exception.outcome,expected)
    def test_mapping_rejects_ambiguous_and_missing(self):
        maps=[{'package':p} for p in ('/Game/A/Test','/Game/B/Test','/Game/Okay','/Game/Missing')]
        route={'asset_name':'Okay','level_id':'OK','entrance_tag':'Level.Entry'}
        z.attach_routes(maps,[route,dict(route,asset_name='Test')])
        self.assertEqual([bool(m['normal_route']) for m in maps],[False,False,True,False])
        z.attach_routes(maps,[route,route]);self.assertFalse(maps[2]['normal_route'])

if __name__=='__main__':unittest.main()
