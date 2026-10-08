"""Session-owned native console and external persistent Python delivery."""
from ._console_dispatch import CommandDispatcher


class Console:
    def __init__(self, session):
        self._session = session
        self._enabled = False
        self._polling = False
        self.dispatcher = CommandDispatcher(session, self.execute)
        self.dropped_commands = 0

    def enable(self):
        self._session._check()
        if not self._enabled:
            self._session._transport.command('console-attach')
            self._enabled = True

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
                result = self.dispatcher.execute(response['console_text'])
                results.append(result)
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
