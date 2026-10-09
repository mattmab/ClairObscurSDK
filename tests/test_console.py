import unittest
from expedition33._console import Console


class Transport:
    def __init__(self):
        self.calls = []
        self.fail_names = False
    def command(self, command, payload=None):
        if command == 'console-names' and self.fail_names:
            raise RuntimeError('disconnected')
        self.calls.append((command, payload))
        return {'result': 0, 'console_dropped': 0}


class Session:
    def __init__(self):
        self._transport = Transport()
    def _check(self):
        pass


class ConsoleTests(unittest.TestCase):
    def test_disconnected_cleanup_revokes_callbacks_without_native_sync(self):
        session = Session()
        console = Console(session)
        console.enable()
        owner = object()
        handle = console.register('sdk.cleanup', lambda _: 'alive', owner=owner)
        session._transport._closed = True
        session._transport.fail_names = True
        console.remove_owner(owner)
        handle.remove()
        self.assertEqual(console.dispatcher.command_names, ())
        self.assertTrue(console.dispatcher.execute('sdk.cleanup', native_fallback=False).failed)
        with self.assertRaisesRegex(RuntimeError, 'disconnected'):
            console.register('sdk.new', lambda _: None, owner=owner)
        console._close()

    def test_output_preserves_unicode_and_escapes_untransportable_text(self):
        session = Session()
        console = Console(session)
        console.enable()
        console.write('hello\0\ud800 \U0001f642')
        self.assertEqual(session._transport.calls[-1],
                         ('console-print', 'hello\\0\\ud800 \U0001f642'))
        console.write('\U0001f642' * 4097)
        chunks = [payload for command, payload in session._transport.calls[-2:]]
        self.assertEqual(''.join(chunks), '\U0001f642' * 4097)
        self.assertTrue(all(len(chunk.encode('utf-16le')) <= 65536 for chunk in chunks))
        console._close()

    def test_toggle_key_is_explicit_and_bounded(self):
        session = Session()
        console = Console(session)
        with self.assertRaisesRegex(RuntimeError, 'disabled'):
            console.set_toggle_key('F10')
        console.enable()
        console.set_toggle_key('F10')
        self.assertEqual(session._transport.calls[-1], ('console-key', '121'))
        with self.assertRaises(ValueError):
            console.set_toggle_key('Alt+F4')
        console.set_toggle_key(None)
        self.assertEqual(session._transport.calls[-1], ('console-key', '0'))
        console._close()

    def test_registration_sync_failure_does_not_publish_callback(self):
        session = Session()
        console = Console(session)
        console.enable()
        owner = object()
        handle = console.register('sdk.hello', lambda text: text, owner=owner)
        self.assertEqual(session._transport.calls[-1], ('console-names', 'sdk.hello'))
        session._transport.fail_names = True
        with self.assertRaisesRegex(RuntimeError, 'disconnected'):
            console.register('sdk.other', lambda text: text, owner=owner)
        self.assertEqual(console.dispatcher.command_names, ('sdk.hello',))
        session._transport.fail_names = False
        handle.remove()
        self.assertEqual(session._transport.calls[-1], ('console-names', ''))
        self.assertTrue(console.dispatcher.execute('sdk.hello', native_fallback=False).failed)
        console._close()

    def test_disable_reenable_preserves_namespace_and_resyncs_commands(self):
        session = Session()
        console = Console(session)
        owner = object()
        console.register('sdk.test', lambda _: 42, owner=owner)
        console.expose('my_mod', owner)
        console.enable()
        console.dispatcher.execute('py value = 17')
        console.disable()
        console.enable()
        self.assertEqual(session._transport.calls[-1], ('console-names', 'sdk.test'))
        self.assertEqual(console.dispatcher.execute('py value').output, '17\n')
        self.assertEqual(console.complete('py my'), ('py my_mod',))
        console.remove_owner(owner)
        self.assertEqual(console.dispatcher.command_names, ())
        console._close()
        self.assertFalse(console.dispatcher.namespace)
