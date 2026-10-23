"""The demo envelope cannot introduce arbitrary poses, callbacks, or ABI data."""
import struct
import unittest
from expedition33._runtime_cinematic_wire import SIZE,INPUT_COUNT,validate_request


def request(op):
    packet=bytearray(SIZE);struct.pack_into('<4IQ',packet,0,3,op,0,0,1)
    if op==70:
        for i in range(INPUT_COUNT):struct.pack_into('<iiQ',packet,88+16*i,i,1,0x1000+i*16)
    return packet


class CinematicWireTests(unittest.TestCase):
    def test_only_four_fixed_operations(self):
        for op in (70,71,72,73):validate_request(bytes(request(op)))
        for op in (1,20,62,69,74,0xffffffff):
            with self.assertRaises(ValueError):validate_request(bytes(request(op)))

    def test_no_user_transform_or_callback_payload(self):
        for op in (70,71,72,73):
            for offset in (24,56,80,88+16*INPUT_COUNT,2000,4096,SIZE-1):
                packet=request(op);packet[offset]=1
                with self.assertRaises(ValueError):validate_request(bytes(packet))

    def test_no_null_or_stale_identity_shape(self):
        for index,serial,address in ((-1,1,0x1000),(1,-1,0x1000),(1,1,0)):
            packet=request(70);struct.pack_into('<iiQ',packet,88,index,serial,address)
            with self.assertRaises(ValueError):validate_request(bytes(packet))

    def test_cleanup_and_status_cannot_supply_identities(self):
        for op in (71,72,73):
            packet=request(op);struct.pack_into('<iiQ',packet,88,1,1,0x1000)
            with self.assertRaises(ValueError):validate_request(bytes(packet))


if __name__=='__main__':unittest.main()
