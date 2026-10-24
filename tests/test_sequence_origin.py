import math
import unittest
import struct
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _sequence_origin as origin
from expedition33 import _sequence_owner as owner


class SequenceOriginTests(unittest.TestCase):
    def test_translation_roundtrip(self):
        data = origin.encode((120, -20, 402000))
        origin.validate_request(data)
        self.assertEqual(len(data), 32)

    def test_rejects_non_translation_or_nonfinite(self):
        for value in (None, (1, 2), (True, 0, 0), (math.nan, 0, 0),
                      (math.inf, 0, 0), (10_000_001, 0, 0), (10**1000, 0, 0), '123'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                origin.encode(value)

    def test_canonical_packet(self):
        valid = origin.encode((0, 0, 0))
        for data in (valid[:-1], valid+b'\0', bytes(32), bytearray(valid)):
            with self.subTest(data=data), self.assertRaises(ValueError):
                origin.validate_request(data)

    def test_owner_packet_accepts_only_origin_payload(self):
        packet = (owner.HEADER.pack(1, 6, 42, 0, 0, 0) +
                  origin.encode((1, 2, 3)) + bytes(owner.SIZE-64))
        owner.validate_request(packet)
        with self.assertRaises(ValueError):
            owner.validate_request(packet[:-1]+b'\1')

    def test_missing_capability_rejects_before_transport(self):
        class Transport:
            def command(self, *args):
                raise AssertionError('No command may be sent')
        class Session:
            _transport = Transport()
        class Scope:
            _session = Session()
        native = owner.NativeSequenceOwner(Scope())
        native.state = 'armed'
        with self.assertRaisesRegex(RuntimeError, 'capability'):
            native.configure_origin((0, 0, 0))
        self.assertEqual(native.state, 'armed')

    def native_owner(self):
        session=N(_transport=N(sequence_origin_protocol=1,command=Mock()),
                  _check=lambda:None,_abort_ownership=Mock())
        native=owner.NativeSequenceOwner(N(_session=session));native.state='armed'
        return native,session

    def test_origin_ack_requires_armed_state(self):
        for state in (0,1,2,3):
            native,session=self.native_owner()
            session._transport.command.side_effect=lambda name,data: {'sequence_owner_packet':
                (data[:24]+struct.pack('<II',0,state)+data[32:]).hex()}
            if state==1:
                self.assertTrue(native.configure_origin((1,2,3)))
                self.assertEqual(native.state,'armed');session._abort_ownership.assert_not_called()
            else:
                with self.assertRaises(ValueError):native.configure_origin((1,2,3))
                self.assertEqual(native.state,'unknown');session._abort_ownership.assert_called_once()
            session._transport.command.assert_called_once()

    def test_known_rejection_remains_closeable(self):
        native,session=self.native_owner()
        def command(name,data):
            op=owner.HEADER.unpack_from(data)[1]
            return {'sequence_owner_packet':(data[:24]+struct.pack('<II',1591,1)+data[32:]).hex()
                    if op==6 else data.hex()}
        session._transport.command.side_effect=command
        with self.assertRaisesRegex(RuntimeError,'close required'):native.configure_origin((1,2,3))
        self.assertEqual(native.state,'cleanup_pending');self.assertEqual(native.origin_error,1591)
        session._abort_ownership.assert_not_called()
        self.assertTrue(native.close());self.assertEqual(native.state,'closed')

    def test_unknown_lost_and_malformed_reply_abort_once(self):
        for fault in ('unknown','lost','tail'):
            native,session=self.native_owner()
            def command(name,data):
                if fault=='lost':raise OSError('Reply lost')
                if fault=='tail':return {'sequence_owner_packet':(data[:24]+struct.pack('<II',0,1)+data[32:-1]+b'\1').hex()}
                return {'sequence_owner_packet':(data[:24]+struct.pack('<II',1593,2)+data[32:]).hex()}
            session._transport.command.side_effect=command
            with self.assertRaises((RuntimeError,ValueError,OSError)):native.configure_origin((1,2,3))
            self.assertEqual(native.state,'unknown');session._abort_ownership.assert_called_once()
            session._transport.command.assert_called_once()
