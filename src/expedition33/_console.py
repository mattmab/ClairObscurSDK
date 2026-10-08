"""Session-owned native console and external persistent Python delivery."""
from ._console_dispatch import CommandDispatcher
import logging


class Console:
    def __init__(self, session):
        self._session = session
        self._enabled = False
        self._polling = False
        self.dispatcher = CommandDispatcher(session, self.execute, self._sync_commands)
        self.dropped_commands = 0

    def enable(self):
        self._session._check()
        if not self._enabled:
            self._session._transport.command('console-attach')
            self._enabled = True
            self._sync_commands(self.dispatcher.command_names)

    def _sync_commands(self, names):
        if self._enabled:
            self._session._transport.command('console-names', ','.join(names))

    def register(self, name, callback, *, owner):
        """Reserve a console command for a mod; remove its handle on disable."""
        return self.dispatcher.register(name, callback, owner=owner)

    def remove_owner(self, owner):
        self.dispatcher.remove_owner(owner)

    def expose(self, name, value):
        """Expose a loaded mod or other trusted object in this session namespace."""
        self._session._check()
        if not isinstance(name, str) or not name.isidentifier() or name.startswith('_') or name in ('sdk', 'help'):
            raise ValueError('Expected a non-reserved Python identifier')
        if name in self.dispatcher.namespace:
            raise ValueError('Console name is already defined')
        self.dispatcher.namespace[name] = value

    @property
    def history(self):
        self._session._check()
        return tuple(self.dispatcher.history)

    def complete(self, prefix):
        return self.dispatcher.complete(prefix)

    def execute(self, command):
        self._session._check()
        if not self._enabled:
            raise RuntimeError('Enable the console before executing engine commands')
        self._session._transport.command('console-execute', command)

    def write(self, text):
        self._session._check()
        if not self._enabled:
            raise RuntimeError('Console is disabled')
        for offset in range(0, len(text), 4096):
            self._session._transport.command('console-print', text[offset:offset+4096])

    def poll(self):
        self._session._check()
        if not self._enabled:
            return ()
        if self._polling:
            raise RuntimeError('Recursive console polling is not supported')
        self._polling = True
        results = []
        try:
            for _ in range(8):
                response = self._session._transport.command('console-poll')
                self.dropped_commands += response['console_dropped']
                if not response['result']:
                    break
                result = self.dispatcher.execute(response['console_text'], native_fallback=False)
                results.append(result)
                logging.getLogger('expedition33.console').log(
                    logging.ERROR if result.failed else logging.INFO, '%s: %s', result.route, result.output.rstrip())
                self.write(result.output + ('\n[output truncated]\n' if result.truncated else ''))
            return tuple(results)
        finally:
            self._polling = False

    def disable(self):
        self._session._check()
        if self._enabled:
            self._session._transport.command('console-detach')
            self._enabled = False

    def _close(self):
        self.dispatcher.close()
        self._enabled = False
        self._session = None
