import struct
import unittest
from expedition33 import _key_wire as wire


class KeyWireTests(unittest.TestCase):
    def test_native_packet_layout_and_replace_ack(self):
        sent = wire.request('replace', 123, 7, ((1, 117), (2, 65)))
        self.assertEqual(len(sent), 552)
        self.assertEqual(struct.unpack_from('<IIQQIIII', sent), (1, 1, 123, 7, 2, 0, 0, 0))
        self.assertEqual(sent[40:56], struct.pack('<IIII', 1, 117, 2, 65))
        self.assertEqual(wire.decode(sent, sent.hex()), (0, 0, ()))

    def test_invalid_requests_rejected_before_transport(self):
        for bindings in (((1, 117), (2, 117)), ((1, 117), (1, 118)),
                         ((0, 117),), ((1, 192),), ((True, 117),), tuple((i+1, 65) for i in range(65))):
            with self.assertRaises(ValueError): wire.request('replace', 123, 1, bindings)
        with self.assertRaises(ValueError): wire.request('drain', 123, 1, ((1, 117),))
        for session, generation in ((0, 1), (123, 0), (True, 1), (123, 2**64)):
            with self.assertRaises(ValueError): wire.request('drain', session, generation)
        dirty = bytearray(wire.request('drain', 123, 1)); dirty[-1] = 1
        with self.assertRaises(ValueError): wire.validate_request(bytes(dirty))

    def test_drain_repeated_presses_and_overflow_accounting(self):
        sent = wire.request('drain', 123, 1)
        reply = bytearray(sent)
        struct.pack_into('<II', reply, 24, 2, 5)
        struct.pack_into('<IIII', reply, 40, 1, 117, 1, 117)
        self.assertEqual(wire.decode(sent, reply.hex()), (0, 5, ((1, 117), (1, 117))))
        reply[-1] = 1
        with self.assertRaises(ValueError): wire.decode(sent, reply.hex())

    def test_changed_identity_and_fabricated_error_data_rejected(self):
        sent = wire.request('replace', 123, 1, ((1, 117),))
        for offset in (0, 4, 8, 16, 28, 36, 40):
            reply = bytearray(sent); reply[offset] ^= 1
            with self.assertRaises(ValueError): wire.decode(sent, reply.hex())
        reply = bytearray(sent); struct.pack_into('<I', reply, 32, 3)
        self.assertEqual(wire.decode(sent, reply.hex()), (3, 0, ()))
        reply[40] = 2
        with self.assertRaises(ValueError): wire.decode(sent, reply.hex())


if __name__ == '__main__': unittest.main()
