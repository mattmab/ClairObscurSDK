import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from expedition33 import RuntimeQueryError, _button_action_wire as wire
from expedition33.sdk import Session
import test_menu_transport
from test_ownership import Transport


class ButtonActionTransportTests(unittest.TestCase):
    capabilities=('button_action_protocol','button_reference_protocol')+test_menu_transport.MenuTransportTests.capabilities

    def transport(self):
        value=test_menu_transport.MenuTransportTests().transport()
        for name in self.capabilities: setattr(value,name,1)
        value.button_action_session=7
        value._read=lambda: dict(event='session_response',command='button-action',closed=False)
        return value

    def test_capabilities_and_nonce_required_before_send(self):
        sent=wire.request('status',2,3)
        for name in self.capabilities:
            for invalid in (0,True,2):
                value=self.transport(); setattr(value,name,invalid)
                with self.assertRaises(ValueError): value.command('button-action',sent)
                self.assertEqual(value._process.stdin.getvalue(),'')
        for nonce in (0,True,-1,2**64):
            value=self.transport(); value.button_action_session=nonce
            with self.assertRaises(ValueError): value.command('button-action',sent)
            self.assertEqual(value._process.stdin.getvalue(),'')

    def test_payload_and_response_correlation(self):
        sent=wire.request('status',2,3)
        for invalid in (None,bytes(wire.SIZE),sent[:-1],bytearray(sent),sent[:72]+b'\x01'+sent[73:]):
            value=self.transport()
            with self.assertRaises(ValueError): value.command('button-action',invalid)
            self.assertEqual(value._process.stdin.getvalue(),'')
        value=self.transport(); value.command('button-action',sent)
        self.assertEqual(value._process.stdin.getvalue(),'button-action '+sent.hex()+'\n')
        value._read=lambda: dict(event='session_response',command='menu',closed=False)
        with self.assertRaises(RuntimeQueryError): value.command('button-action',sent)
        self.assertTrue(value._closed)

    def fake_backend(self):
        value=Transport()
        for name in self.capabilities: setattr(value,name,1)
        value.button_action_session=7
        return value

    def test_opt_in_selects_v16_and_preserves_v15(self):
        for option,version in [('button_actions',16),('button_references',15)]:
            value=self.fake_backend()
            with patch('expedition33.sdk.SessionTransport',return_value=value) as factory:
                with Session(**{option:True}) as session:
                    self.assertIn(f'research-probe-v{version}',str(factory.call_args.kwargs['_executable']))
                    if version==16: self.assertTrue(session.supports_button_actions)
        with self.assertRaises(ValueError): Session(button_actions=1)

    def test_opt_in_rejects_missing_action_handshake(self):
        for key,invalid in [('button_action_protocol',0),('button_action_protocol',True),
                            ('button_action_session',0),('button_action_session',True)]:
            value=self.fake_backend(); setattr(value,key,invalid)
            with patch('expedition33.sdk.SessionTransport',return_value=value):
                with self.assertRaisesRegex(RuntimeQueryError,'Button action backend'): Session(button_actions=True)
            self.assertTrue(value._closed)

    def test_native_layout(self):
        root=Path(__file__).resolve().parents[1]
        path=root/'build/menu-action-fixture/session_layout_v16.exe'
        if not path.exists(): self.skipTest('Build action fixtures first')
        layout=json.loads(subprocess.check_output([str(path)],text=True))
        self.assertEqual(layout['message'],'E33SDK.Session.v16')
        self.assertTrue(layout['mapping'].startswith('Local\\E33Session16_'))
        self.assertEqual(layout['button_action_size'],wire.SIZE)
        self.assertEqual(layout['button_action_offset'],layout['menu_offset']+layout['menu_size'])
        self.assertEqual(layout['button_action_command'],108)


if __name__=='__main__': unittest.main()
