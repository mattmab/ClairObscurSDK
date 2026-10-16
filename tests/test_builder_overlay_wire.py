import struct
import unittest
from expedition33.procedural_mesh import HEADER, SIZE, validate_request


class OverlayWireTests(unittest.TestCase):
    def test_history_delete_accepts_one_identity_and_rejects_extra_payload(self):
        packet=bytearray(SIZE)
        HEADER.pack_into(packet,0,3,63,0,0,7)
        struct.pack_into('<iiQ',packet,88,123,456,0x10000)
        validate_request(bytes(packet))
        packet[104]=1
        with self.assertRaises(ValueError):validate_request(bytes(packet))

    def test_menu_escape_request_has_no_payload(self):
        packet=bytearray(SIZE)
        HEADER.pack_into(packet,0,3,64,0,0,7)
        validate_request(bytes(packet))
        packet[88]=1
        with self.assertRaises(ValueError):validate_request(bytes(packet))

    def test_headless_initialization_accepts_identities(self):
        packet = bytearray(SIZE)
        HEADER.pack_into(packet, 0, 3, 62, 0, 0, 7)
        struct.pack_into('<iiQ', packet, 88, 123, 456, 0x10000)
        validate_request(bytes(packet))
        packet[2136] = 1
        with self.assertRaises(ValueError):
            validate_request(bytes(packet))

    def test_headless_initialization_rejects_output_fields(self):
        packet = bytearray(SIZE)
        HEADER.pack_into(packet, 0, 3, 62, 0, 1, 7)
        with self.assertRaises(ValueError):
            validate_request(bytes(packet))
