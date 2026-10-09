import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from expedition33.introspection import Harness
from expedition33.introspection.agent import AgentBridge, BoundedText, MAX_OUTPUT
from expedition33.mods import ModLoader, ModError
from test_mods import FakeSession


SOURCE = '''
from expedition33.management import ModDefinition
class Mod:
 def management(self): return ModDefinition('specimen', 'Specimen', version='test')
 def enable(self, session):
  self.scope = session
  session.actions.register('specimen.add', lambda n: n + 1, mutates=False,
      schema={'type':'object', 'properties':{'n':{'type':'integer'}}, 'required':['n']})
 def disable(self): pass
'''


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Specimen').mkdir()
        (self.root / 'Specimen/mod.py').write_text(SOURCE)
        self.session = FakeSession()
        self.loader = ModLoader(self.root, session=self.session)
        self.addCleanup(self.loader.close)
        self.loader.load('Specimen')
        self.loader.enable('Specimen')
        self.bridge = self.loader.actions

    def request(self, **request):
        return self.bridge.dispatch(request)

    def test_original_aliases_schema_copies_and_lifecycle(self):
        for op in ('action', 'call_debug_action', 'run_test_action'):
            result = self.request(op=op, name='specimen.add', args={'n': 4})
            self.assertTrue(result['success'])
            self.assertEqual(result['result'], 5)
        for args in ({}, {'n': True}, {'n': 1, 'other': 1}):
            self.assertFalse(self.request(op='action', name='specimen.add', args=args)['success'])
        view = self.request(op='dev_status')['result']
        view['actions'][0]['schema']['properties'].clear()
        self.assertTrue(self.request(op='action', name='specimen.add', args={'n': 2})['success'])
        self.assertFalse(self.request(op='mod_disable', mod='Specimen')['success'])
        self.assertTrue(self.request(op='mod_disable', mod='Specimen', allow_mutation=True)['success'])
        self.assertFalse(self.bridge.actions)
        self.assertFalse(self.request(op='action', name='specimen.add', args={'n': 2})['success'])
        self.assertTrue(self.request(op='mod_enable', mod='Specimen', allow_mutation=True)['success'])
        self.assertEqual(self.request(op='mod_list')['result'],
        [{'name': 'Specimen', 'enabled': True, 'version': 'test', 'cleanup_error': None}])

    def test_failure_diagnostics_no_retry_mutation_and_reentry(self):
        scope = self.loader._loaded['Specimen'][2]
        calls = []
        def fail():
            calls.append(1)
            print('before error')
            raise SystemExit('contained')
        scope.actions.register('specimen.fail', fail)
        self.assertFalse(self.request(op='action', name='specimen.fail')['success'])
        self.assertFalse(calls)
        result = self.request(op='action', name='specimen.fail', allow_mutation=True)
        self.assertEqual(calls, [1])
        self.assertEqual(result['error']['type'], 'SystemExit')
        self.assertIn('before error', result['stdout'])
        self.assertIn('contained', result['error']['traceback'])
        scope.actions.register('specimen.reenter', lambda: self.request(op='mod_list'), mutates=False)
        result = self.request(op='action', name='specimen.reenter')
        self.assertFalse(result['success'])
        self.assertIn('nested execution', result['error']['message'])
        self.assertTrue(self.request(op='mod_list')['success'])

    def test_unregister_token_does_not_remove_replacement(self):
        scope = self.loader._loaded['Specimen'][2]
        stale = self.bridge.actions['specimen.add']['token']
        scope.actions.unregister('specimen.add')
        scope.actions.register('specimen.add', lambda: 42, mutates=False)
        self.bridge.remove('specimen.add', stale)
        self.assertEqual(self.request(op='action', name='specimen.add')['result'], 42)
        with self.assertRaises(ValueError): scope.actions.register('specimen.add', lambda: None)

    def test_registry_limit_and_schema_copy(self):
        scope = self.loader._loaded['Specimen'][2]
        schema = {'type': 'object', 'properties': {'n': {'type': 'integer'}}}
        scope.actions.register('specimen.copy', lambda **args: args, schema=schema, mutates=False)
        schema['properties'].clear()
        self.assertTrue(self.request(op='action', name='specimen.copy', args={'n': 1})['success'])
        for index in range(126):
            scope.actions.register('specimen.cap' + str(index), lambda: None)
        with self.assertRaisesRegex(ValueError, '128 action limit'):
            scope.actions.register('specimen.overflow', lambda: None)
        self.loader.disable('Specimen')
        self.assertFalse(self.bridge.actions)

    def test_scope_cleanup_even_when_mod_disable_raises(self):
        record = self.loader._loaded['Specimen']
        def fail(): raise SystemExit('cleanup')
        record[1].disable = fail
        with self.assertRaises(ModError): self.loader.disable('Specimen')
        self.assertFalse(self.bridge.actions)
        reply = self.request(op='mod_enable', mod='Specimen', allow_mutation=True)
        self.assertFalse(reply['success'])
        self.assertIn('restart the controller', reply['error']['message'])
        row = self.request(op='mod_list')['result'][0]
        self.assertFalse(row['enabled'])
        self.assertIn('cleanup', row['cleanup_error'])

    def test_output_result_limits_logs_and_foreign_thread(self):
        out = BoundedText()
        out.write('🌍' * MAX_OUTPUT)
        self.assertLessEqual(len(''.join(out.parts).encode()), MAX_OUTPUT)
        self.assertTrue(out.truncated)
        scope = self.loader._loaded['Specimen'][2]
        scope.actions.register('specimen.large', lambda: 'x' * 131073, mutates=False)
        self.assertFalse(self.request(op='action', name='specimen.large')['success'])
        scope.actions.register('specimen.native', lambda: object(), mutates=False)
        self.assertFalse(self.request(op='action', name='specimen.native')['success'])
        self.bridge.log_path = self.root / 'sdk.log'
        self.bridge.log_path.write_text('ignore\nmatch one\nmatch two\n')
        self.assertEqual(self.request(op='logs', contains='match', limit=1)['result']['lines'], ['match two'])
        errors = []
        def foreign():
            try: self.request(op='dev_status')
            except RuntimeError as error: errors.append(str(error))
        thread = threading.Thread(target=foreign); thread.start(); thread.join()
        self.assertIn('owner thread', errors[0])

    def test_harness_routes_agent_without_catalog_scan_and_keeps_original_core(self):
        scope = self.loader._loaded['Specimen'][2]
        fake = SimpleNamespace(actions=scope.actions, supports_reflected_invocation=False)
        harness = Harness(fake)
        self.addCleanup(harness.close)
        with patch('expedition33.introspection._Backend.refresh', side_effect=AssertionError('unneeded scan')):
            result = harness.request({'op': 'action', 'name': 'specimen.add', 'args': {'n': 9}})
        self.assertTrue(result['success'])
        self.assertEqual(result['result'], 10)
        self.assertIn('dev_status', harness.request({'op': 'status'})['operations'])
        self.assertNotIn('mod_reload', harness.SUPPORTED)
        for name in ('IntrospectionHarness', 'SDKManagement'):
            self.assertFalse(self.request(op='mod_disable', mod=name, allow_mutation=True)['success'])


if __name__ == '__main__': unittest.main()
