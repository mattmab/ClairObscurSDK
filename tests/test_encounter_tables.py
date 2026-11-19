import struct,unittest
from types import SimpleNamespace as N
from expedition33 import encounter_tables as t

from encounter_samples import PROFILES

class Tests(unittest.TestCase):
    def make(self,asset='ExampleEnemies'):
        def held(i):return N(object=N(index=i,serial=1001+i,address=0x10000+i*256),_token=i+1)
        row=dict(asset=asset,profile=PROFILES[asset],target=held(1),source=held(2),map_class=held(3),map_add=held(4))
        return t.packet(71,row,held(5),'e33c5701000000020000000300000004',0)
    def test_explicit_rows_and_save_bound_packets(self):
        for asset in PROFILES:self.assertIsNone(t.validate(self.make(asset)))
        for offset in (136,392,488,2024,2040,2048):
            data=bytearray(self.make());data[offset]^=1
            # Identity and token changes remain syntactically valid; native
            # proves those values against held leases and the selected GUID.
            if offset in (136,2048):
                with self.assertRaises(ValueError):t.validate(bytes(data))
    def test_one_additive_row_required_and_no_reserved_mutation(self):
        sent=self.make();reply=bytearray(sent);struct.pack_into('<2I',reply,8,0,1);struct.pack_into('<2I',reply,128,100,101)
        self.assertEqual(t.decode(sent,bytes(reply))['registered_rows'],101)
        struct.pack_into('<I',reply,132,100)
        with self.assertRaises(RuntimeError):t.decode(sent,bytes(reply))
        struct.pack_into('<I',reply,132,101);reply[-1]=1
        with self.assertRaises(RuntimeError):t.decode(sent,bytes(reply))
    def test_cleanup_deferral_is_not_success(self):
        sent=self.make();reply=bytearray(sent);struct.pack_into('<I',reply,8,4242)
        with self.assertRaises(t.wire.OriginalNarrativeError) as result:t.decode(sent,bytes(reply))
        self.assertEqual(result.exception.code,4242)
    def test_different_profiles_and_no_reward_are_supported(self):
        from copy import deepcopy
        other=deepcopy(PROFILES)
        for row in other.values():row['row']='OtherRow';row['required_reward']=''
        self.assertEqual(t.validate_profiles(other),other)
        for invalid in ({},dict(PROFILES,Extra=PROFILES['ExampleEnemies'])):
            with self.assertRaises(ValueError):t.validate_profiles(invalid)
if __name__=='__main__':unittest.main()
