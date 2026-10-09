"""Wire checks and optional cross-language packet validation; no game attach."""
from dataclasses import replace
from pathlib import Path
import struct
import subprocess
import tempfile
import threading
from types import SimpleNamespace
from io import StringIO
import unittest

from expedition33 import _invocation_wire as wire
from expedition33.invocation import PARM, RETURN, UnsupportedInvocation
import test_invocation
from expedition33._session import SessionTransport


class WireTests(unittest.TestCase):
    def setUp(self):
        self.planner = test_invocation.InvocationTests()
        self.planner.setUp()

    def plan(self):
        p = self.planner
        return p.plan([p.field('Input', 'IntProperty', 0, 4),
                       p.field('Result', 'BoolProperty', 4, 1, PARM | RETURN,
                               bool_encoding='0xff010001')], {'Input': 42}, 5, 4, 16)

    def test_roundtrip_correlates_schema_and_outcomes(self):
        request = wire.encode_plan(self.plan())
        self.assertEqual(len(request), 24648)
        reply = bytearray(request)
        struct.pack_into('<II', reply, 32, 1, 0)
        reply[wire.DATA_AT + 4] = 1
        result = wire.decode_reply(request, reply.hex())
        self.assertEqual((result.outcome, result.data), ('dispatch_returned', struct.pack('<iB', 42, 1)))
        reply[wire.FIELDS_AT + 28] ^= 1
        with self.assertRaises(ValueError): wire.decode_reply(request, reply.hex())
        for outcome, error, expected in ((0, 209, 'not_dispatched'), (2, 223, 'unknown')):
            reply = bytearray(request)
            struct.pack_into('<II', reply, 32, outcome, error)
            result = wire.decode_reply(request, reply.hex())
            self.assertEqual((result.outcome, result.data, result.objects), (expected, b'', ()))
        for outcome, error in ((0, 0), (1, 209), (3, 0)):
            struct.pack_into('<II', reply, 32, outcome, error)
            with self.assertRaises(ValueError): wire.decode_reply(request, reply.hex())

    def test_object_results_are_observations_and_never_raw_data(self):
        p = self.planner
        cls = p.catalog.by_index[2]
        plan = p.plan([p.field('ReturnValue', 'ObjectProperty', 0, 8, PARM | RETURN,
                             property_class_index=2, property_class_serial=cls.serial,
                             property_class_name=cls.name, property_class_address=hex(cls.address))], {}, 8, 0)
        request = wire.encode_plan(plan)
        reply = bytearray(request)
        struct.pack_into('<III', reply, 28, 1, 1, 0)
        wire.OBJECT.pack_into(reply, wire.OBJECTS_AT, 0, p.target.index, p.target.serial, p.target.address)
        result = wire.decode_reply(request, reply.hex())
        self.assertEqual(result.objects, ((0, p.target.index, p.target.serial, p.target.address),))
        reply[wire.DATA_AT] = 1
        with self.assertRaises(ValueError): wire.decode_reply(request, reply.hex())
        reply[wire.DATA_AT] = 0
        struct.pack_into('<I', reply, wire.OBJECTS_AT, 1)
        with self.assertRaises(ValueError): wire.decode_reply(request, reply.hex())

    def test_bounds_and_encoding(self):
        plan = self.plan()
        with self.assertRaises(UnsupportedInvocation): wire.encode_plan(replace(plan, parameter_size=4097))
        for name in ('', 'a' * 96, 'a\0b', '\u00e9'):
            with self.assertRaises(UnsupportedInvocation):
                wire.encode_plan(replace(plan, parameters=(replace(plan.parameters[0], name=name),)))
        request = wire.encode_plan(plan)
        for reply in ('', 'z' * (wire.SIZE * 2), ' ' * (wire.SIZE * 2)):
            with self.assertRaises(ValueError): wire.decode_reply(request, reply)

    def test_native_validator_agrees_with_python_layout(self):
        executable = Path(__file__).resolve().parents[1] / 'build/invocation-fixture/invocation_fixture.exe'
        if not executable.exists(): self.skipTest('Run scripts/test-invocation-packet.cmd for native fixture')
        request = bytearray(wire.encode_plan(self.plan()))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'packet.bin'
            path.write_bytes(request)
            checked = subprocess.run([str(executable), str(path)], capture_output=True, text=True)
            self.assertEqual((checked.returncode, checked.stdout.strip()), (0, '0'))
            request[wire.DATA_AT + 4] = 1  # Nonzero return storage must be rejected before dispatch.
            path.write_bytes(request)
            checked = subprocess.run([str(executable), str(path)], capture_output=True, text=True)
            self.assertEqual((checked.returncode, checked.stdout.strip()), (1, '306'))

    def test_transport_capability_and_payload_gate_before_writing(self):
        transport = object.__new__(SessionTransport)
        transport._owner = threading.get_ident()
        transport._closed = False
        stream = StringIO()
        transport._process = SimpleNamespace(stdin=stream)
        request = wire.encode_plan(self.plan())
        with self.assertRaises(ValueError): transport.command('reflected-invoke', request)
        self.assertEqual(stream.getvalue(), '')
        transport.reflected_protocol = 1
        for payload in (None, 'text', bytes(1)):
            with self.assertRaises(ValueError): transport.command('reflected-invoke', payload)
        self.assertEqual(stream.getvalue(), '')
        transport._read = lambda: {'event': 'session_response', 'command': 'reflected-invoke', 'closed': False}
        transport.command('reflected-invoke', request)
        self.assertEqual(stream.getvalue(), 'reflected-invoke ' + request.hex() + '\n')


if __name__ == '__main__':
    unittest.main()
