import struct,unittest
from types import SimpleNamespace as N
from test_runtime_scene_editor import package
from scene_editor_tests.registry import Registry

class RegistryLookupTests(unittest.TestCase):
    def setup_registry(self,count):
        rows=[f'/Game/Audio/Track{i:06}.Track{i:06}' for i in range(count)]
        r=Registry(N(session=N(_session=N())))
        r.classes=[N(index=i,serial=1,address=100+i) for i in range(5)]
        calls=[]
        def page(op,payload):
            self.assertEqual(op,80);offset=struct.unpack('<I',payload[2][1])[0];calls.append(offset)
            selected=rows[offset:offset+32];raw=bytearray(20984);struct.pack_into('<II',raw,3560,len(rows),len(selected))
            for i,path in enumerate(selected):raw[4000+i*512:4000+i*512+len(path)]=path.encode('ascii')
            return bytes(raw)
        r.command=page
        return r,rows,calls
    def test_single_track_does_not_transfer_the_entire_audio_library(self):
        r,rows,calls=self.setup_registry(38802)
        self.assertEqual(r.asset_index(rows[1234],2),1234)
        self.assertLessEqual(len(calls),13)
        count=len(calls);self.assertEqual(r.asset_index(rows[1234],2),1234);self.assertEqual(len(calls),count)
        other=Registry(r.runtime);other.classes=r.classes;other.command=r.command
        self.assertEqual(other.asset_index(rows[1234],2),1234);self.assertEqual(len(calls),count)
    def test_first_and_last_partial_page(self):
        r,rows,_=self.setup_registry(65)
        self.assertEqual(r.asset_index(rows[0],2),0);self.assertEqual(r.asset_index(rows[-1],2),64)
    def test_absent_and_empty_catalogues_fail_without_dispatching_a_sound(self):
        for count in (0,65):
            r,_,_=self.setup_registry(count)
            with self.assertRaises(ValueError):r.asset_index('/Game/Missing.Missing',2)
if __name__=='__main__':unittest.main()
