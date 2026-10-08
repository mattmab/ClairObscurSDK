"""Incremental port of the original BL4 harness, exposed in the SDK console."""
import json
from pathlib import Path
from expedition33.introspection import Harness
from expedition33.introspection.service import FileService


class Mod:
    def __init__(self):
        self.harness = None
        self._commands = []
        self.service = None

    def enable(self, session):
        self.harness = Harness()
        session.console.expose('introspection', self.harness)
        self._commands.append(session.console.register(
            'e33i.status', lambda _args: self.request({'op': 'status'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.roots', lambda _args: self.request({'op': 'roots'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.request', lambda args: self.request(json.loads(args)), owner=self))
        data = Path(__file__).resolve().parents[2] / 'settings/E33Introspection'
        self.service = FileService(data, self.harness, session.pid)

    def poll(self):
        if self.service is not None:
            self.service.pump()

    def request(self, request):
        return self.harness.request(request)

    def disable(self):
        if self.service is not None:
            self.service.close()
            self.service = None
        for command in self._commands:
            command.remove()
        self._commands.clear()
        if self.harness is not None:
            self.harness.close()
            self.harness = None
