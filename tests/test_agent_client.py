import contextlib
import io
import json
from pathlib import Path
import runpy
import unittest
from unittest.mock import Mock, patch


class AgentClientTests(unittest.TestCase):
    def setUp(self):
        self.main = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/e33_agent.py'))['main']

    def call(self, argv, result=None, error=None):
        sender = Mock(return_value=result or {'ok': True, 'result': {'success': True}}, side_effect=error)
        output = io.StringIO()
        with patch.dict(self.main.__globals__, send=sender), contextlib.redirect_stdout(output):
            code = self.main(argv)
        return code, json.loads(output.getvalue()), sender

    def test_request_shapes_and_explicit_mutation_flag(self):
        examples = [(['status'], {'op': 'dev_status'}), (['mods'], {'op': 'mod_list'}),
            (['action', 'sample.add', '--args', '{"n":3}'], {'op': 'action', 'name': 'sample.add', 'args': {'n':3}}),
            (['enable', 'Sample'], {'op': 'mod_enable', 'mod': 'Sample'}),
            (['disable', 'Sample'], {'op': 'mod_disable', 'mod': 'Sample'}),
            (['logs', '--contains', 'match', '--limit', '2'], {'op': 'logs', 'contains': 'match', 'limit':2})]
        for argv, expected in examples:
            code, _, sender = self.call(['--allow-mutation', '--timeout', '27', '--data', 'custom'] + argv)
            self.assertEqual(code, 0)
            sender.assert_called_once_with(dict(expected, allow_mutation=True), Path('custom'), 27.)
        _, _, sender = self.call(['action', 'read'])
        self.assertIs(sender.call_args.args[0]['allow_mutation'], False)

    def test_outer_and_inner_failures_produce_nonzero_exit(self):
        for result in ({'ok': False, 'error': 'protocol'}, {'ok': True, 'result': {'success': False}},
                       {'ok': True, 'result': {}}):
            code, body, sender = self.call(['mods'], result=result)
            self.assertEqual(code, 1)
            self.assertEqual(body, result)
            self.assertEqual(sender.call_count, 1)

    def test_local_validation_and_unknown_outcome_do_not_retry(self):
        for text in ('{', '[]', 'null'):
            code, _, sender = self.call(['action', 'test', '--args', text])
            self.assertEqual(code, 1)
            sender.assert_not_called()
        code, result, sender = self.call(['--allow-mutation', 'enable', 'Sample'],
                                       error=TimeoutError('Outcome unknown'))
        self.assertEqual(code, 1)
        self.assertIn('unknown', result['error'])
        self.assertEqual(sender.call_count, 1)


if __name__ == '__main__': unittest.main()
