import gc
import unittest
import weakref
from expedition33._console_dispatch import CommandDispatcher


class ConsoleTests(unittest.TestCase):
    def setUp(self):
        self.native = []
        self.dispatcher = CommandDispatcher(object(), self.native.append)
    def tearDown(self):
        self.dispatcher.close()
    def test_python_state_expression_and_import_persist(self):
        d = self.dispatcher
        self.assertFalse(d.execute('py import math; x=9').failed)
        self.assertEqual(d.execute('py math.sqrt(x)').output, '3.0\n')
        self.assertEqual(d.execute('py print("Hello World")').output, 'Hello World\n')
        self.assertIn('state persists', d.execute('py help()').output)
    def test_errors_do_not_destroy_session(self):
        for code, name in [('py x=', 'SyntaxError'), ('py 1/0', 'ZeroDivisionError'), ('py raise SystemExit(7)', 'SystemExit')]:
            result = self.dispatcher.execute(code)
            self.assertTrue(result.failed)
            self.assertIn(name, result.output)
        self.assertEqual(self.dispatcher.execute('py 6*7').output, '42\n')
    def test_native_preserved_and_custom_removed(self):
        owner = object()
        handle = self.dispatcher.register('example.ping', lambda text: text.upper(), owner=owner)
        self.assertEqual(self.dispatcher.execute('example.ping hello').output, "'HELLO'\n")
        self.dispatcher.execute('stat fps')
        self.assertEqual(self.native, ['stat fps'])
        self.dispatcher.remove_owner(owner)
        handle.remove()
        self.assertEqual(self.dispatcher.execute('example.ping hello').route, 'native')
    def test_output_history_bounded_and_close_releases_mod(self):
        class Mod:
            def command(self, text): pass
        mod = Mod()
        reference = weakref.ref(mod)
        self.dispatcher.register('mod.test', mod.command, owner=mod)
        self.dispatcher.namespace['my_mod'] = mod
        del mod
        result = self.dispatcher.execute('py print("x" * 100000)')
        self.assertTrue(result.truncated)
        self.assertEqual(len(result.output), 32768)
        for _ in range(110): self.dispatcher.execute('py 1')
        self.assertEqual(len(self.dispatcher.history), 100)
        self.dispatcher.close()
        gc.collect()
        self.assertIsNone(reference())
    def test_registration_recursion_and_completions(self):
        self.dispatcher.execute('py value=1')
        self.assertEqual(self.dispatcher.complete('py val'), ('py value',))
        self.dispatcher.register('nested', lambda _: self.dispatcher.execute('py 1'), owner=self)
        self.assertIn('Recursive', self.dispatcher.execute('nested').output)
        with self.assertRaises(ValueError): self.dispatcher.register('py', print, owner=self)


if __name__ == '__main__': unittest.main()
