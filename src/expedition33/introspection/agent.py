"""Port of Mattmab's BL4Introspection agent bridge (MIT, adjacent LICENSE).

Preserves named actions, aliases and bounded diagnostic envelopes. The external
controller owns Python execution; engine operations retain SDK game-thread gates.
No source execution endpoint or request-supplied file path is accepted.
"""
import contextlib
import io
import json
from pathlib import Path
import re
import threading
import time
import traceback

MAX_OUTPUT = 16384
MAX_RESULT = 131072
NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.]{0,95}$')


def plain(value, depth=0):
    if depth > 12:
        raise ValueError('Result exceeds nesting limit')
    if value is None or type(value) in (str, int, float, bool):
        return value
    if type(value) in (list, tuple):
        return [plain(v, depth + 1) for v in value]
    if type(value) is dict and all(type(k) is str for k in value):
        return {k: plain(v, depth + 1) for k, v in value.items()}
    raise TypeError('Actions must return plain JSON values; UObject/native wrappers cannot be retained')


def bounded_json(value):
    value = plain(value)
    if len(json.dumps(value, allow_nan=False).encode()) > MAX_RESULT:
        raise ValueError('Action result exceeds 128 KiB')
    return value


class BoundedText(io.TextIOBase):
    def __init__(self):
        self.parts, self.size, self.truncated = [], 0, False

    def write(self, text):
        text = str(text)
        left = MAX_OUTPUT - self.size
        encoded = text.encode('utf-8', errors='replace')
        if left > 0:
            self.parts.append(encoded[:left].decode('utf-8', errors='ignore'))
        self.size += min(len(encoded), max(0, left))
        self.truncated |= len(encoded) > left
        return len(text)

    def getvalue(self):
        return ''.join(self.parts) + ('\n[output truncated]' if self.truncated else '')


class AgentBridge:
    OPERATIONS = frozenset(('dev_status', 'mod_list', 'mod_enable', 'mod_disable',
                           'mod_reload', 'reload_changed_mod',
                           'action', 'call_debug_action', 'run_test_action', 'logs'))

    def __init__(self, registry, log_path):
        self.registry = registry
        self.log_path = Path(log_path)
        self.actions, self.last = {}, {}
        self.running = False
        self._owner = threading.get_ident()

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Agent operations require the external Python owner thread')

    def register(self, name, callback, *, owner, description='', schema=None, mutates=True):
        self._check()
        if not NAME.fullmatch(name) or not NAME.fullmatch(owner):
            raise ValueError('Invalid action/owner name')
        if name in self.actions or len(self.actions) >= 128:
            raise ValueError('Action already registered or 128 action limit reached')
        if not callable(callback) or type(mutates) is not bool:
            raise TypeError('A callable and boolean mutation policy are required')
        schema = bounded_json(schema if schema is not None else
            {'type': 'object', 'properties': {}, 'additionalProperties': False})
        if type(schema) is not dict or schema.get('type', 'object') != 'object':
            raise ValueError('Action schema must describe an object')
        props = schema.get('properties', {})
        if type(props) is not dict or any(type(v) is not dict for v in props.values()):
            raise ValueError('Invalid action properties')
        if type(schema.get('required', [])) is not list or any(
                type(k) is not str or k not in props for k in schema.get('required', [])):
            raise ValueError('Invalid required action arguments')
        token = object()
        self.actions[name] = dict(callback=callback, owner=owner,
            description=str(description)[:1000], schema=schema, mutates=mutates, token=token)
        return token

    def remove(self, name, token):
        self._check()
        if name in self.actions and self.actions[name]['token'] is token:
            del self.actions[name]

    def close(self):
        self._check()
        self.actions.clear()
        self.last.clear()

    def _args(self, args, schema):
        if type(args) is not dict:
            raise ValueError('args must be an object')
        args = bounded_json(args)
        props = schema.get('properties', {})
        if schema.get('additionalProperties', False) is False and set(args) - set(props):
            raise ValueError('Unknown action arguments')
        if set(schema.get('required', [])) - set(args):
            raise ValueError('Missing required argument')
        types = {'boolean': bool, 'string': str, 'integer': int,
                 'number': (float, int), 'object': dict, 'array': list}
        for key, value in args.items():
            rule = props.get(key, {})
            expected = types.get(rule.get('type'))
            if expected and (not isinstance(value, expected) or isinstance(value, bool)
                    and rule.get('type') in ('integer', 'number')):
                raise ValueError('Wrong argument type: ' + key)
            if 'enum' in rule and value not in rule['enum']:
                raise ValueError('Invalid choice: ' + key)
        return args

    def dispatch(self, request):
        self._check()
        if self.running:
            raise RuntimeError('Development action already running; nested execution rejected')
        self.running = True
        started = time.monotonic()
        out, err = BoundedText(), BoundedText()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                result = bounded_json(self._dispatch(request))
            response = dict(success=True, result=result)
        except BaseException as error:
            try:
                message, trace = str(error)[:2000], traceback.format_exc()[-8000:]
            except BaseException:
                message, trace = '<exception formatting failed>', ''
            response = dict(success=False, error=dict(type=type(error).__name__,
                message=message, traceback=trace))
        finally:
            self.running = False
        response.update(elapsed_ms=round((time.monotonic() - started) * 1000, 2),
                        stdout=out.getvalue(), stderr=err.getvalue())
        response['over_budget'] = response['elapsed_ms'] > 2000
        self.last = plain({k: v for k, v in response.items() if k != 'result'})
        return response

    def _dispatch(self, request):
        op = request['op']
        if op == 'dev_status':
            return dict(transport='local files; no network listener', allow_dev_exec=False,
                raw_exec_supported=False, execution='external Python owner thread',
                adapters={'registry': ['mod_list', 'mod_enable', 'mod_disable',
                                      'mod_reload', 'reload_changed_mod']},
                reload_scope='installed mod.py bytes only; expected_sha256 required; no dependency/core reload',
                unsupported=['staged_archive_install', 'core_reload', 'kart_*'],
                actions=[dict(name=n, **{k: v for k, v in a.items()
                    if k not in ('callback', 'token')}) for n, a in self.actions.items()], last=self.last)
        if op == 'mod_list':
            return [dict(name=v['folder'], enabled=v['enabled'], version=v['version'],
                         cleanup_error=v.get('cleanup_error'), source_sha256=v.get('source_sha256'))
                    for v in self.registry.views()][:128]
        if op in ('mod_enable', 'mod_disable', 'mod_reload', 'reload_changed_mod'):
            if request.get('allow_mutation') is not True:
                raise ValueError('This action requires allow_mutation: true')
            name = request.get('mod')
            if name in ('SDKManagement', 'IntrospectionHarness'):
                raise ValueError('Cannot change the servicing core mod through its own request')
            rows = [v for v in self.registry.views() if v['folder'] == name]
            if len(rows) != 1:
                raise ValueError('Mod must already be loaded')
            if op in ('mod_reload', 'reload_changed_mod'):
                return self.registry.reload(self.registry.select(rows[0]['id']),
                    expected_sha256=request.get('expected_sha256'),
                    changed_only=op == 'reload_changed_mod')
            selection = self.registry.set_enabled(self.registry.select(rows[0]['id']), op == 'mod_enable')
            return {'enabled': self.registry.view(selection)['enabled']}
        if op == 'logs':
            with self.log_path.open('rb') as stream:
                stream.seek(0, 2)
                stream.seek(max(0, stream.tell() - 32768))
                text = stream.read(32768).decode('utf-8', errors='replace')
            query = str(request.get('contains', ''))[:100]
            return {'lines': [line[:2000] for line in text.splitlines() if query in line]
                    [-min(100, max(1, int(request.get('limit', 30)))):]}
        if op in ('action', 'call_debug_action', 'run_test_action'):
            action = self.actions.get(request.get('name'))
            if action is None:
                raise ValueError('Unknown/unloaded action: ' + str(request.get('name')))
            if action['mutates'] and request.get('allow_mutation') is not True:
                raise ValueError('This action requires allow_mutation: true')
            return action['callback'](**self._args(request.get('args', {}), action['schema']))
        raise ValueError('Unsupported development operation')


class ScopedActions:
    """Mod-owned action registrations; old removals cannot revoke replacements."""
    def __init__(self, bridge, scope, owner):
        self._bridge, self._scope, self._owner = bridge, scope, owner
        self._registrations = []

    def register(self, name, callback, *, description='', schema=None, mutates=True):
        self._scope._check()
        if not callable(callback):
            raise TypeError('Action must be callable')
        def guarded(**args):
            self._scope._check()
            return callback(**args)
        token = self._bridge.register(name, guarded, owner=self._owner,
            description=description, schema=schema, mutates=mutates)
        self._registrations.append((name, token))

    def unregister(self, name):
        self._scope._check()
        for entry in tuple(self._registrations):
            if entry[0] == name:
                self._bridge.remove(*entry)
                self._registrations.remove(entry)

    def _close(self):
        for entry in self._registrations:
            self._bridge.remove(*entry)
        self._registrations.clear()
