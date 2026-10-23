"""Incremental port of the original BL4 harness, exposed in the SDK console."""
import json
from expedition33.paths import sdk_root
from pathlib import Path
from expedition33.introspection import Harness
from expedition33.introspection.service import FileService
from expedition33.management import ModDefinition, Action


class Mod:
    def __init__(self):
        self.harness = None
        self._commands = []
        self.service = None
        self._world_retiring=False;self._retirement_result=None
        self._retirement_leases=[];self._retirement_closed=False
        self._retirement_release_started=set()

    def management(self):
        return ModDefinition('sdk.introspection', 'Introspection Harness',
            description='Original Explorer core with verified Expedition 33 adapters; parity is incomplete.',
            version='e33-port-1.3-stage1', actions=(
                Action('status', 'Port status', lambda _: self.request({'op': 'status'})),
                Action('roots', 'Live roots', lambda _: self.request({'op': 'roots'})),
                Action('request', 'Explorer JSON request', self.request)))

    def enable(self, session):
        self._world_retiring=False;self._retirement_result=None
        self._retirement_leases=[];self._retirement_closed=False
        self._retirement_release_started=set()
        self.harness = Harness(session=session)
        session.console.expose('introspection', self.harness)
        self._commands.append(session.console.register(
            'e33i.status', lambda _args: self.request({'op': 'status'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.roots', lambda _args: self.request({'op': 'roots'}), owner=self))
        self._commands.append(session.console.register(
            'e33i.request', lambda args: self.request(json.loads(args)), owner=self))
        data = sdk_root() / 'settings/E33Introspection'
        self.service = FileService(data, self.harness, session.pid)

    def poll(self):
        if self._world_retiring:return
        if self.harness is not None:
            self.harness.poll()
        if self.service is not None:
            self.service.pump()

    def request(self, request):
        if self._world_retiring:raise RuntimeError('Introspection world is retiring')
        return self.harness.request(request)

    def revoke_world(self,context):
        self._world_retiring=True
        if self.service is not None:self.service.revoke()
        if self.harness is not None:self.harness.revoke()

    def begin_world_retirement(self,context):
        if self._retirement_result is not None:return self._retirement_result
        self._world_retiring=True
        if self.harness is not None:
            # Explorer.close sweeps owners out of its table before releasing.
            # Keep exact leases independently until their native ACK is known.
            owners=[pair[1] for pair in self.harness._explorer._owners.values()]
            pending=self.harness._backend.pending_owner
            if pending is not None:owners.append(pending)
            for owner in owners:
                for lease in owner._leases:
                    if not any(lease is old for old in self._retirement_leases):
                        self._retirement_leases.append(lease)
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if self._retirement_result in ('ack','unknown'):return self._retirement_result
        if ((self.service is not None and self.service._busy)
                or (self.harness is not None and self.harness._running)):
            self._retirement_result='pending';return 'pending'
        try:
            closed_now=False
            if not self._retirement_closed:
                if self.service is not None:
                    self.service.close();self.service=None
                while self._commands:
                    self._commands[0].remove();self._commands.pop(0)
                if self.harness is not None:self.harness.close()
                self._retirement_closed=True
                closed_now=True
            pending=False
            for lease in self._retirement_leases:
                state=lease._state
                if state=='released':continue
                if closed_now and state=='pending_release':
                    pending=True;continue
                if state not in ('active','pending_release') or (state=='active' and id(lease) in self._retirement_release_started):
                    self._retirement_result='unknown';return 'unknown'
                self._retirement_release_started.add(id(lease))
                if not lease.release():
                    if lease._state!='pending_release':
                        self._retirement_result='unknown';return 'unknown'
                    pending=True
            if pending:self._retirement_result='pending'
            else:
                self._retirement_result='ack';self.harness=None
            return self._retirement_result
        except BaseException:
            # Preserve exact owners/journal. No failed or ambiguous close replay.
            self._retirement_result='unknown'
            return 'unknown'

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
