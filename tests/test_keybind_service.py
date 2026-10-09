from types import SimpleNamespace
import unittest
from expedition33 import RuntimeQueryError, _key_wire as wire
from expedition33._session import BUTTON_CAPABILITIES
from expedition33.keybind_service import KeybindService
import test_management_keys as key_fixture


class Transport:
    def __init__(self):
        for name in BUTTON_CAPABILITIES + ('multi_button_protocol', 'trace_protocol', 'keybind_protocol'):
            setattr(self, name, 1)
        self.button_action_session = 123
        self.multi_button_capacity = self.trace_capacity = 16
        self.keybind_capacity = 64
        self.events = []
        self.dropped = 0
        self.sent = []
        self.fail = False

    def command(self, command, sent):
        assert command == 'keys'
        operation = wire.validate_request(sent)
        self.sent.append(sent)
        if self.fail:
            return {'key_packet': 'malformed'}
        reply = bytearray(sent)
        if operation == 1:
            self.events = []
        else:
            wire.HEADER.pack_into(reply, 0, 1, 2, 123, wire.HEADER.unpack_from(sent)[3],
                                  len(self.events), self.dropped, 0, 0)
            for i, event in enumerate(self.events):
                wire.BINDING.pack_into(reply, 40 + i * 8, *event)
            self.events, self.dropped = [], 0
        return {'key_packet': reply.hex()}


class KeyServiceTests(unittest.TestCase):
    def setUp(self):
        key_fixture.ManagementKeysTests.setUp(self)
        self.loader.enable('Specimen')
        self.transport = Transport()
        self.session = SimpleNamespace(_closed=False, _transport=self.transport, _check=lambda: None)
        self.service = KeybindService(self.session, self.registry)
        self.service.poll()
        self.instance = self.loader._loaded['Specimen'][1]

    def tearDown(self):
        self.session._closed = True
        self.service.close()
        key_fixture.ManagementKeysTests.tearDown(self)

    def test_remap_clears_queued_old_map_before_delivery(self):
        self.transport.events = [(1, 117)]
        self.registry.set_keybind(self.registry.select('specimen'), 'read-key', 'F7')
        self.assertEqual(self.service.poll(), 0)
        self.assertEqual(self.instance.calls, 0)
        self.transport.events = [(1, 118)]
        self.assertEqual(self.service.poll(), 1)
        self.assertEqual(self.instance.calls, 1)

    def test_disabled_mod_replaces_map_with_empty(self):
        self.transport.events = [(1, 117)]
        self.loader.disable('Specimen')
        self.assertEqual(self.service.poll(), 0)
        self.assertEqual(self.service._routes, ())
        self.assertEqual(self.instance.calls, 0)

    def test_entire_batch_validated_before_callback(self):
        self.transport.events = [(1, 117), (2, 117)]
        with self.assertRaises(RuntimeQueryError): self.service.poll()
        self.assertEqual(self.instance.calls, 0)
        self.assertEqual(self.service.poll(), 0)

    def test_overflow_discards_batch_without_callbacks(self):
        self.transport.events = [(1, 117)]
        self.transport.dropped = 3
        self.assertEqual(self.service.poll(), 0)
        self.assertEqual(self.service.dropped, 4)
        self.assertEqual(self.instance.calls, 0)

    def test_lifecycle_change_inside_callback_revokes_rest_of_batch(self):
        from dataclasses import replace
        entry = self.registry._entries['specimen']
        calls = []
        def disable(_):
            calls.append(1)
            self.loader.disable('Specimen')
        entry.definition = replace(entry.definition, keybinds=(replace(entry.definition.keybinds[0], callback=disable),))
        self.transport.events = [(1, 117), (1, 117)]
        self.assertEqual(self.service.poll(), 1)
        self.assertEqual(calls, [1])

    def test_single_owner_and_generation_continuity_on_reuse(self):
        with self.assertRaises(ValueError): KeybindService(self.session, self.registry)
        old = self.service._generation
        self.service.close()
        new = KeybindService(self.session, self.registry)
        new.poll()
        self.assertGreater(new._generation, old + 1)
        new.close()

    def test_unknown_outcome_does_not_retry_or_close_borrowed_session(self):
        self.transport.fail = True
        with self.assertRaises(ValueError): self.service.poll()
        count = len(self.transport.sent)
        self.assertEqual(self.service.poll(), 0)
        with self.assertRaisesRegex(RuntimeQueryError, 'owning session'): self.service.close()
        self.assertEqual(len(self.transport.sent), count)
        self.assertFalse(self.session._closed)
        with self.assertRaises(ValueError): KeybindService(self.session, self.registry)


if __name__ == '__main__': unittest.main()

