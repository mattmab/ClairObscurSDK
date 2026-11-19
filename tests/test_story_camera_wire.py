import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_camera_wire as wire


class StoryCameraWireTests(unittest.TestCase):
    def packet(self):
        actors=[N(index=i,serial=i+20,address=0x10000+i*0x1000) for i in range(6)]
        return wire.encode(1,2,3,4,*actors)

    def test_packet_matches_native_fixed_layout(self):
        p=self.packet();self.assertEqual(len(p),20984)
        self.assertEqual(struct.unpack_from('<4I4Q',p),(3,234,0,0,1,2,3,4))
        self.assertEqual(wire.IDENTITY.unpack_from(p,48+5*16),(5,25,0x15000))
        self.assertFalse(any(p[144:]));wire.validate(p)

    def test_missing_ownership_and_invalid_context_are_rejected(self):
        for at in (16,24,32,40):
            p=bytearray(self.packet());struct.pack_into('<Q',p,at,0)
            with self.assertRaises(ValueError):wire.validate(bytes(p))
        for at in range(48,144,16):
            p=bytearray(self.packet());struct.pack_into('<i',p,at+4,0)
            with self.assertRaises(ValueError):wire.validate(bytes(p))

    def test_reserved_bytes_and_reply_state_cannot_be_submitted(self):
        for at in (8,12,144,20983):
            p=bytearray(self.packet());p[at]=1
            with self.assertRaises(ValueError):wire.validate(bytes(p))
        with self.assertRaises(ValueError):wire.validate(bytearray(self.packet()))

    def test_framing_requires_both_original_transform_functions(self):
        actors=[N(index=i,serial=i+20,address=0x10000+i*0x1000) for i in range(8)]
        p=wire.encode(1,2,3,4,*actors[:6],pose_functions=actors[6:])
        self.assertEqual(wire.IDENTITY.unpack_from(p,144),(6,26,0x16000))
        self.assertEqual(wire.IDENTITY.unpack_from(p,160),(7,27,0x17000))
        self.assertFalse(any(p[176:]));wire.validate(p)
        broken=bytearray(p);broken[160:176]=bytes(16)
        with self.assertRaises(ValueError):wire.validate(bytes(broken))

    def test_camera_restoration_requires_both_original_view_functions(self):
        actors=[N(index=i,serial=i+20,address=0x10000+i*0x1000) for i in range(8)]
        p=wire.encode(1,2,3,4,*actors[:6],view_functions=actors[6:])
        self.assertEqual(wire.IDENTITY.unpack_from(p,176),(6,26,0x16000))
        self.assertEqual(wire.IDENTITY.unpack_from(p,192),(7,27,0x17000))
        self.assertFalse(any(p[208:]));wire.validate(p)
        broken=bytearray(p);broken[192:208]=bytes(16)
        with self.assertRaises(ValueError):wire.validate(bytes(broken))

    def test_retirement_keeps_owner_identities_and_requires_valid_mode(self):
        p=self.packet();retired=wire.retire(p,999)
        self.assertEqual(struct.unpack_from('<Q',retired,16)[0],999)
        self.assertEqual(retired[24:208],p[24:208])
        self.assertEqual(struct.unpack_from('<II',retired,208),(1,0))
        for at in (208,212,216):
            bad=bytearray(retired);bad[at]=2
            with self.assertRaises(ValueError):wire.validate(bytes(bad))
        with self.assertRaises(ValueError):wire.retire(p,0)
