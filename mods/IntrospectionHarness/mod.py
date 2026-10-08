"""Incremental port of the original BL4 harness, exposed in the SDK console."""
import json
from expedition33.introspection import Harness


class Mod:
    def __init__(self):
        self.harness = None
        self._commands = []

    def enable(self, session):
        self.harness = Harness()
        session.console.expose('introspection', self.harness)
        self._commands.append(session.console.register(
            'e33i.status', lambda _args: self.request({'op': 'status'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.roots', lambda _args: self.request({'op': 'roots'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.request', lambda args: self.request(json.loads(args)), owner=self))

    def request(self, request):
        return self.harness.request(request)

    def disable(self):
        for command in self._commands:
            command.remove()
        self._commands.clear()
        if self.harness is not None:
            self.harness.close()
            self.harness = None
