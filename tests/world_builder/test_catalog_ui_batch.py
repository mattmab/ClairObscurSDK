from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tests'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from dataclasses import replace
from expedition33 import _ui_batch as wire
import test_text_transport

class UIBatchTests(unittest.TestCase):
    def test_layout_class_input_echo_is_validated_without_accepting_ownership(self):
        from test_invocation import InvocationTests
        specimen = InvocationTests(); specimen.setUp()
        cls = specimen.catalog.by_index[2]
        row = specimen.field('Class', 'ClassProperty', 0, 8, meta_class_index=2,
            meta_class_serial=cls.serial, meta_class_name=cls.name, meta_class_address=hex(cls.address))
        obj = specimen.catalog.by_index[3]
        plan = specimen.plan([row], {'Class': obj}, 8)
        plan = replace(plan, function=replace(plan.function, name='SetStyle'))
        session = SimpleNamespace(_abort_ownership=Mock(),
            _transport=SimpleNamespace(ui_batch_protocol=1, layout_batch_protocol=1))
        planner = SimpleNamespace(_catalog=specimen.catalog)
        call = SimpleNamespace(_plan=plan, _check=lambda: (planner, session))
        reply = SimpleNamespace(outcome='dispatch_returned', error=0, data=bytes(8),
                                objects=((0, obj.index, obj.serial, obj.address),))
        with patch('expedition33._ui_batch.execute', return_value=[{'retained_packet': 'unused'}]), \
             patch('expedition33._retained_wire.decode_reply', return_value=(reply, ())):
            wire.invoke_setters(SimpleNamespace(_session=session), [call])
            session._abort_ownership.assert_not_called()
            reply.objects = ((0, obj.index, obj.serial + 1, obj.address),)
            with self.assertRaises(Exception):
                wire.invoke_setters(SimpleNamespace(_session=session), [call])
            session._abort_ownership.assert_called_once()

    def test_layout_requires_explicit_capability(self):
        for protocol in (0, True, 4, '1'):
            session = SimpleNamespace(_transport=SimpleNamespace(ui_batch_protocol=1, layout_batch_protocol=protocol))
            self.assertFalse(wire.layout_available(session))
        session._transport.layout_batch_protocol = 1
        self.assertTrue(wire.layout_available(session))
        self.assertFalse(wire.extended_layout_available(session))
        session._transport.layout_batch_protocol = 2
        self.assertTrue(wire.layout_available(session))
        self.assertTrue(wire.extended_layout_available(session))
        session._transport.layout_batch_protocol = 3
        self.assertTrue(wire.layout_available(session))
        self.assertTrue(wire.extended_layout_available(session))
        session._transport.ui_batch_protocol = 0
        self.assertFalse(wire.layout_available(session))

    def test_sparse_roundtrip_including_zero_gaps_and_edges(self):
        for data in (b'', bytes(100), b'x', b'\0'*3+b'abc'+bytes(18)+b'z', bytes(range(256))*20):
            self.assertEqual(wire.unpack_sparse(wire.pack_sparse(data), len(data)), data)

    def test_sparse_rejects_overlap_overflow_and_truncation(self):
        for malformed in (b'1', struct.pack('<2I', 1, 0), struct.pack('<2I', 10, 2)+b'ab',
                          struct.pack('<2I', 0, 3)+b'ab', struct.pack('<2I', 0, 2)+b'ab'+struct.pack('<2I', 1, 1)+b'c'):
            with self.assertRaises(ValueError): wire.unpack_sparse(malformed, 10)

    def requests(self):
        return [('multi-button', bytes(2648)), ('text-invoke', bytes(91800))]

    def test_reply_requires_all_ordered_operations_and_exact_bounds(self):
        request = wire.encode(self.requests())
        wire.validate_request(request)
        reply = bytearray(request); struct.pack_into('<I', reply, 12, 2)
        self.assertEqual(wire.decode(self.requests(), reply.hex()),
            [{'multi_button_packet': bytes(2648).hex()}, {'text_packet': bytes(91800).hex()}])
        for offset, value in ((4, 1), (8, len(reply)+1), (12, 1), (16, 1203), (20, 104)):
            bad = bytearray(reply); struct.pack_into('<I', bad, offset, value)
            with self.assertRaises(ValueError): wire.decode(self.requests(), bad.hex())

    def test_unknown_reply_aborts_once_without_retry(self):
        session = SimpleNamespace(_check=Mock(), _abort_ownership=Mock(),
            _transport=SimpleNamespace(command=Mock(return_value={'ui_batch_packet': '00'})))
        with self.assertRaises(ValueError): wire.execute(session, self.requests())
        session._abort_ownership.assert_called_once_with()
        self.assertEqual(session._transport.command.call_count, 1)

    def test_local_oversize_never_dispatches(self):
        session = SimpleNamespace(_check=Mock(), _abort_ownership=Mock(), _transport=Mock())
        with self.assertRaises(ValueError): wire.execute(session, [('text-invoke', b'x'*91800)])
        session._transport.command.assert_not_called()
        session._abort_ownership.assert_not_called()

    def test_transport_capability_and_request_gate(self):
        t = test_text_transport.TextTransportTests().transport()
        payload = wire.encode(self.requests())
        with self.assertRaises(ValueError): t.command('ui-batch', payload)
        self.assertEqual(t._process.stdin.getvalue(), '')
        t.ui_batch_protocol = 1
        t._read = lambda: dict(event='session_response', command='ui-batch', closed=False)
        t.command('ui-batch', payload)
        self.assertEqual(t._process.stdin.getvalue(), 'ui-batch '+payload.hex()+'\n')

if __name__ == '__main__': unittest.main()
