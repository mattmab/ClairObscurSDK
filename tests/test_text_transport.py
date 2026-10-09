import io
import json
from pathlib import Path
import subprocess
import threading
from types import SimpleNamespace
import unittest

from expedition33 import RuntimeQueryError
from expedition33._session import SessionTransport
from expedition33._text_wire import SIZE


class TextTransportTests(unittest.TestCase):
    capabilities = ('text_value_protocol', 'pod_value_protocol', 'object_assignment_protocol',
                    'stable_identity_protocol', 'retained_protocol', 'lease_protocol', 'reflected_protocol')

    def transport(self):
        transport = SessionTransport.__new__(SessionTransport)
        transport._owner = threading.get_ident()
        transport._closed = False
        transport._process = SimpleNamespace(stdin=io.StringIO())
        for name in self.capabilities:
            setattr(transport, name, 1)
        transport._read = lambda: dict(event='session_response', command='text-invoke', closed=False)
        transport._abort = lambda: setattr(transport, '_closed', True)
        return transport

    def test_complete_handshake_required_before_any_send(self):
        packet = (3).to_bytes(4, 'little') + bytes(SIZE-4)
        for missing in self.capabilities:
            transport = self.transport()
            setattr(transport, missing, 0)
            with self.assertRaisesRegex(ValueError, 'owned text'):
                transport.command('text-invoke', packet)
            self.assertEqual(transport._process.stdin.getvalue(), '')
            self.assertFalse(transport._closed)

    def test_exact_version_extent_and_bytes_required(self):
        for payload in (None, bytes(SIZE), bytes(SIZE-1), bytes(SIZE+1), bytearray(SIZE),
                        (2).to_bytes(4, 'little') + bytes(SIZE-4)):
            transport = self.transport()
            with self.assertRaisesRegex(ValueError, 'payload'):
                transport.command('text-invoke', payload)
            self.assertEqual(transport._process.stdin.getvalue(), '')

    def test_full_packet_sent_and_mismatched_ack_aborts(self):
        packet = (3).to_bytes(4, 'little') + bytes(SIZE-4)
        transport = self.transport()
        transport.command('text-invoke', packet)
        self.assertEqual(transport._process.stdin.getvalue(), 'text-invoke ' + packet.hex() + '\n')
        transport._read = lambda: dict(event='session_response', command='retained-invoke', closed=False)
        with self.assertRaises(RuntimeQueryError):
            transport.command('text-invoke', packet)
        self.assertTrue(transport._closed)

    def test_compiled_session_layouts_preserve_existing_fields_and_isolate_v12(self):
        root = Path(__file__).resolve().parents[1] / 'build/text-compatibility'
        executables = [root / f'session_layout_v{version}.exe' for version in (11,12)]
        if not all(path.is_file() for path in executables):
            self.skipTest('Run scripts/verify-text-compatibility.cmd to build native fixtures')
        old, new = [json.loads(subprocess.check_output([str(path)], text=True)) for path in executables]
        self.assertEqual(old['message'], 'E33SDK.Session.v11')
        self.assertEqual(new['message'], 'E33SDK.Session.v12')
        self.assertNotEqual(old['mapping'], new['mapping'])
        self.assertTrue(new['mapping'].startswith('Local\\E33Session12_'))
        for field in ('retained_offset', 'assignment_offset'):
            self.assertEqual(old[field], new[field])
        self.assertEqual(new['text_offset'], old['legacy_payload_end'])
        self.assertLessEqual(new['text_offset'], old['size'])
        alignment = new['alignment']
        expected_size = (new['text_offset'] + SIZE + alignment-1) // alignment * alignment
        self.assertEqual(new['size'], expected_size)
        self.assertEqual(new['text_size'], SIZE)
        self.assertEqual(new['text_action'], 106)
