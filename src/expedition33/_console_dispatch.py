"""Persistent external-Python dispatcher. Native console transport is separate.

Trusted local code only. Execute on the Python session owner thread, never the
GameThread. Python execution can block this controller; it is not sandboxed.
"""
import ast
from collections import deque
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass
import io
import pydoc
import re
import threading
import traceback
import weakref


@dataclass(frozen=True)
class CommandResult:
    route: str
    output: str
    failed: bool
    truncated: bool


class BoundedOutput(io.TextIOBase):
    def __init__(self, limit=32768):
        self.limit = limit
        self.parts = []
        self.length = 0
        self.truncated = False

    def write(self, value):
        if not isinstance(value, str):
            raise TypeError('Console output must be text')
        remaining = self.limit - self.length
        piece = value[:remaining]
        if piece:
            self.parts.append(piece)
            self.length += len(piece)
        self.truncated |= len(value) > remaining
        return len(value)

    def flush(self):
        pass

    def text(self):
        return ''.join(self.parts)


class Registration:
    def __init__(self, dispatcher, token):
        self._dispatcher = weakref.ref(dispatcher)
        self._token = token

    def remove(self):
        dispatcher = self._dispatcher()
        if dispatcher is not None:
            dispatcher._remove(self._token)

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.remove()


class CommandDispatcher:
    def __init__(self, sdk, native_execute, commands_changed=None):
        self._owner = threading.get_ident()
        self._closed = False
        self._executing = False
        self._native_execute = native_execute
        self._commands_changed = commands_changed
        self._commands = {}
        self._next_token = 1
        self.history = deque(maxlen=100)
        self.namespace = {'__name__': '__sdk_console__', 'sdk': sdk, 'help': self._help}

    def _check(self):
        if threading.get_ident() != self._owner:
            raise RuntimeError('Console commands require the Python session owner thread')
        if self._closed:
            raise RuntimeError('Console dispatcher is closed')

    @staticmethod
    def _help(value=None):
        if value is None:
            print('Use py <Python code>; state persists for this session. sdk exposes the session API. '
                  'Native commands run without py. help(object) prints help without opening a pager.')
        else:
            print(pydoc.render_doc(value, renderer=pydoc.plaintext))

    def register(self, name, callback, *, owner):
        self._check()
        if (not isinstance(name, str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]{0,63}', name)
            or name.lower() == 'py' or not callable(callback) or owner is None):
            raise ValueError('A command name, callable and lifecycle owner are required')
        key = name.lower()
        if key in self._commands:
            raise ValueError(f'Command {name!r} is already registered')
        if len(self._commands) >= 256:
            raise RuntimeError('Console registration limit reached')
        token = self._next_token
        self._next_token += 1
        self._replace_commands({**self._commands, key: (token, owner, callback)})
        return Registration(self, token)

    def _replace_commands(self, updated):
        if self._commands_changed is not None:
            self._commands_changed(tuple(updated))
        self._commands = updated

    @property
    def command_names(self):
        self._check()
        return tuple(self._commands)

    def _remove(self, token):
        if self._closed:
            return
        self._check()
        self._replace_commands({name: value for name, value in self._commands.items() if value[0] != token})

    def remove_owner(self, owner):
        self._check()
        self._replace_commands({name: value for name, value in self._commands.items() if value[1] is not owner})

    def complete(self, prefix):
        self._check()
        # Never evaluate expressions/properties just to offer completions.
        if prefix.startswith('py '):
            word = prefix[3:]
            return tuple('py '+key for key in sorted(self.namespace) if key.startswith(word) and not key.startswith('__'))[:50]
        return tuple(name for name in sorted(['py', *self._commands]) if name.startswith(prefix.lower()))[:50]

    def execute(self, line, *, native_fallback=True):
        self._check()
        if self._executing:
            raise RuntimeError('Recursive console dispatch is not supported')
        if not isinstance(line, str) or not line.strip() or len(line) > 4096 or '\0' in line:
            raise ValueError('Command must contain 1–4096 characters and no NUL')
        self._executing = True
        self.history.append(line)
        parts = line.strip().split(None, 1)
        command, remainder = parts[0], parts[1] if len(parts) > 1 else ''
        route = 'python' if command.lower() == 'py' else ('custom' if command.lower() in self._commands else 'native')
        output = BoundedOutput()
        failed = False
        try:
            with redirect_stdout(output), redirect_stderr(output):
                try:
                    if route == 'python':
                        tree = ast.parse(remainder, filename='<game console>', mode='exec')
                        expression = tree.body.pop() if tree.body and isinstance(tree.body[-1], ast.Expr) else None
                        exec(compile(tree, '<game console>', 'exec'), self.namespace)
                        if expression is not None:
                            value = eval(compile(ast.Expression(expression.value), '<game console>', 'eval'), self.namespace)
                            if value is not None:
                                print(repr(value))
                    elif route == 'custom':
                        value = self._commands[command.lower()][2](remainder)
                        if value is not None:
                            print(repr(value))
                    else:
                        if not native_fallback:
                            raise RuntimeError('SDK console command registration is no longer active')
                        value = self._native_execute(line)
                        if value is not None:
                            print(value)
                except BaseException as error:
                    failed = True
                    try:
                        traceback.print_exception(error)
                    except BaseException:
                        output.write('<exception formatting failed>\n')
        finally:
            self._executing = False
        return CommandResult(route, output.text(), failed, output.truncated)

    def close(self):
        if self._closed:
            return
        self._check()
        self._closed = True
        self._commands.clear()
        self.namespace.clear()
        self.history.clear()
        self._native_execute = None
        self._commands_changed = None
