import json
from pathlib import Path
import subprocess
import unittest
from expedition33 import RuntimeQueryError, _menu_wire as wire
import test_text_transport


class MenuTransportTests(unittest.TestCase):
    capabilities = ('menu_protocol', 'enum_value_protocol') + test_text_transport.TextTransportTests.capabilities

    def transport(self):
        transport = test_text_transport.TextTransportTests().transport()
        for name in self.capabilities: setattr(transport, name, 1)
        transport._read = lambda: dict(event='session_response', command='menu', closed=False)
        return transport

    def test_capability_gate(self):
        for name in self.capabilities:
            transport = self.transport()
            setattr(transport, name, 0)
            with self.assertRaises(ValueError): transport.command('menu', wire.request('status', 1))
            self.assertEqual(transport._process.stdin.getvalue(), '')

    def test_send_and_ack_mismatch(self):
        transport = self.transport()
        packet = wire.request('status', 1)
        transport.command('menu', packet)
        self.assertEqual(transport._process.stdin.getvalue(), 'menu ' + packet.hex() + '\n')
        transport._read = lambda: dict(event='session_response', command='ping', closed=False)
        with self.assertRaises(RuntimeQueryError): transport.command('menu', packet)
        self.assertTrue(transport._closed)

    def test_invalid_payload_before_send(self):
        for payload in (None, bytes(wire.SIZE), bytes(wire.SIZE-1), bytearray(wire.SIZE)):
            transport = self.transport()
            with self.assertRaises(ValueError): transport.command('menu', payload)
            self.assertEqual(transport._process.stdin.getvalue(), '')

    def test_compiled_layout(self):
        root = Path(__file__).resolve().parents[1] / 'build/menu-lifetime-fixture'
        paths = [root / f'session_layout_v{version}.exe' for version in (13, 14)]
        if not all(path.exists() for path in paths): self.skipTest('Build menu native fixtures first')
        old, new = [json.loads(subprocess.check_output([str(path)], text=True)) for path in paths]
        self.assertEqual((old['message'], new['message']), ('E33SDK.Session.v13', 'E33SDK.Session.v14'))
        self.assertTrue(new['mapping'].startswith('Local\\E33Session14_'))
        self.assertNotEqual(old['mapping'], new['mapping'])
        for name in ('retained_offset', 'assignment_offset', 'text_offset', 'text_size'):
            self.assertEqual(old[name], new[name])
        self.assertEqual(new['menu_offset'], old['text_offset'] + old['text_size'])
        self.assertEqual(new['menu_size'], wire.SIZE)
        self.assertEqual(new['menu_plans_offset'], wire.PLANS_AT)
        self.assertEqual(new['menu_action'], 107)
