import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_speaker_wire as wire

class StorySpeakerWireTests(unittest.TestCase):
    def packet(self,name='Faceless Boy'):
        objects=[N(index=i,serial=1001+i,address=0x10000+i*16) for i in range(4)]
        return wire.encode(123,456,*objects,name)
    def test_name_is_copied_as_utf16_and_all_identities_and_owner_are_bound(self):
        p=self.packet('Speaker \U0001f339');wire.validate(p)
        count=struct.unpack_from('<I',p,96)[0]
        self.assertEqual(p[100:100+count*2].decode('utf-16-le'),'Speaker \U0001f339\0')
        for at in (0,4,8,12,16,24,36,100+count*2):
            changed=bytearray(p);struct.pack_into('<I',changed,at,0 if at in (16,24,36) else 1)
            with self.assertRaises(ValueError):wire.validate(bytes(changed))
    def test_invalid_names_are_rejected_and_surrogate_pairs_fit(self):
        for name in ('',' ', 'a'*161,'bad\0name','\ud800'):
            with self.assertRaises(ValueError):self.packet(name)
        wire.validate(self.packet('\U0001f339'*160))
