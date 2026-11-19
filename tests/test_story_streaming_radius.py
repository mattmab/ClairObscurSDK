import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_streaming_radius as wire


class RadiusWireTests(unittest.TestCase):
    def packet(self,radius=8000):return wire.encode(99,(1,2,0x10000),N(index=3,serial=4,address=0x20000),radius)

    def test_exact_instance_request_and_acknowledgement(self):
        packet=self.packet();wire.validate_request(packet)
        self.assertEqual(wire.IDENTITY.unpack_from(packet,24),(1,2,0x10000))
        self.assertEqual(wire.IDENTITY.unpack_from(packet,40),(3,4,0x20000))
        self.assertEqual(struct.unpack_from('<f',packet,56),(8000.,))
        ack=bytearray(packet);struct.pack_into('<I',ack,12,1)
        wire.acknowledge(packet,dict(mesh_packet=ack.hex()))

    def test_bounds_types_reserved_bytes_and_unowned_identities_rejected(self):
        for radius in (True,0,999,50001,float('nan'),float('inf'),'8000'):
            with self.subTest(radius=radius),self.assertRaises(ValueError):self.packet(radius)
        for offset in (60,wire.SIZE-1):
            packet=bytearray(self.packet());packet[offset]=1
            with self.assertRaises(ValueError):wire.validate_request(bytes(packet))
        for offset,fmt,value in ((16,'<Q',0),(28,'<i',0),(32,'<Q',0x10001),(44,'<i',0),(48,'<Q',0)):
            packet=bytearray(self.packet());struct.pack_into(fmt,packet,offset,value)
            with self.assertRaises(ValueError):wire.validate_request(bytes(packet))

    def test_rejection_unknown_or_changed_ack_never_claim_success(self):
        request=self.packet()
        for error,state in ((4310,0),(4311,0),(4310,1),(0,0),(1,0)):
            ack=bytearray(request);struct.pack_into('<II',ack,8,error,state)
            with self.subTest(error=error,state=state),self.assertRaisesRegex(RuntimeError,'not replayed'):
                wire.acknowledge(request,dict(mesh_packet=ack.hex()))
        ack=bytearray(request);struct.pack_into('<I',ack,12,1);struct.pack_into('<f',ack,56,9000)
        with self.assertRaisesRegex(RuntimeError,'changed'):wire.acknowledge(request,dict(mesh_packet=ack.hex()))

