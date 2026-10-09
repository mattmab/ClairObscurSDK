import unittest
import struct
from types import SimpleNamespace
from expedition33 import _trace_wire as wire


class TraceWireTests(unittest.TestCase):
    def test_start_schema_filter_and_assigned_registration(self):
        identity = SimpleNamespace(pid=99, index=2, serial=0, address=0x20000)
        exemplar = SimpleNamespace(pid=99, index=1, serial=0, address=0x10000)
        plan = SimpleNamespace(function=identity, parameters=(), parameter_size=0,
            allocation_extent=0, return_offset=65535, function_flags=0x400, entry_rva=0x1234)
        request = wire.encode_request('start', 7, plan=plan, exemplar=exemplar, target=exemplar)
        header = wire.HEADER.unpack_from(request)
        self.assertEqual(header, (1, 1, 7, 0, 10000, 100, 1, 0, 1, 0, 0x10000))
        reply = bytearray(request)
        struct.pack_into('<Q', reply, 16, 45)
        wire.OUTPUT.pack_into(reply, wire.OUTPUT_AT, 0, 1, 0, 0, 0, 0, 0)
        self.assertEqual(wire.decode_reply(request, reply.hex(), expected_pid=99).registration, 45)
        struct.pack_into('<Q', reply, 16, 0)
        with self.assertRaises(ValueError):
            wire.decode_reply(request, reply.hex(), expected_pid=99)
        exemplar.pid = 98
        with self.assertRaises(ValueError):
            wire.encode_request('start', 7, plan=plan, exemplar=exemplar)

    def response(self):
        request = wire.encode_request('drain', 7, 9)
        reply = bytearray(request)
        wire.OUTPUT.pack_into(reply, wire.OUTPUT_AT, 0, 1, 0, 1, 3, 1, 2)
        wire.EVENT.pack_into(reply, wire.EVENTS_AT, 3, 100, 8, 99, 12, 0, 1)
        reply[wire.EVENTS_AT + wire.EVENT.size] = 42
        return request, reply

    def test_abi_and_owned_event_with_overflow_gap(self):
        self.assertEqual((wire.HEADER.size, wire.OUTPUT.size, wire.EVENT.size), (56, 32, 36))
        request, reply = self.response()
        decoded = wire.decode_reply(request, reply.hex(), expected_pid=99)
        self.assertEqual((decoded.registration, decoded.observed, decoded.dropped, decoded.rejected), (9, 3, 1, 2))
        self.assertEqual(decoded.events[0].data, b'*')
        reply[wire.EVENTS_AT + wire.EVENT.size] = 0
        self.assertEqual(decoded.events[0].data, b'*')

    def test_reject_corruption_and_cross_registration(self):
        for offset in (8, 16, 40, wire.SCHEMA_AT, wire.EVENTS_AT + 36 + 1, wire.SIZE - 1):
            request, reply = self.response()
            reply[offset] ^= 1
            with self.assertRaises(ValueError):
                wire.decode_reply(request, reply.hex(), expected_pid=99)
        request, reply = self.response()
        with self.assertRaises(ValueError):
            wire.decode_reply(request, reply.hex(), expected_pid=98)
        wire.EVENT.pack_into(reply, wire.EVENTS_AT, 4, 100, 8, 99, 12, 0, 1)
        with self.assertRaises(ValueError):
            wire.decode_reply(request, reply.hex(), expected_pid=99)

    def test_control_request_validation(self):
        for op in ('stop', 'drain', 'status', 'forget'):
            request = wire.encode_request(op, 7, 9)
            self.assertEqual(len(request), wire.SIZE)
            self.assertFalse(any(request[wire.SCHEMA_AT:]))
            with self.assertRaises(ValueError):
                wire.encode_request(op, 7)
        for owner in (0, -1, 2**64, True):
            with self.assertRaises(ValueError):
                wire.encode_request('status', owner, 9)
