"""Independent Statistics candidate using only public Expedition 33 SDK APIs.

Entry observations are callback notifications, not proof of a completed hit.
No third-party native implementation or DLL is used.
"""
from collections import deque
from dataclasses import asdict
import json
import logging
from logging.handlers import RotatingFileHandler
from expedition33.paths import sdk_root
from pathlib import Path
import time

from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33.management import ModDefinition, Action, Report
from datetime import datetime

COUNTERS = ('TotalReceivedDamagesByCharacters', 'TotalReceivedDamagesByEnemies',
            'HighestReceivedDamagesByEnemies', 'DodgeCount', 'ParryCount')


class Mod:
    def __init__(self):
        self.trace = None
        self.session = None
        self.sink = None
        self.events = deque(maxlen=1000)
        self.count = 0
        self.incomplete = False
        self.error = None
        self.last_status = {}

    def management(self):
        return ModDefinition('sdk.statistics', 'Statistics',
            description='Candidate damage notifications and five native summary counters. Full DLL parity is not yet verified.',
            actions=(Action('records', 'View Statistics records', lambda _: self.records()),
                     Action('status', 'Statistics status', lambda _: self.status()),
                     Action('summary', 'Read native battle summary', lambda _: self.summary())))

    def records(self):
        """Saved observations only; browsing never dereferences past UObject identities."""
        folder = sdk_root() / 'logs'
        entries = []
        archive = folder / 'statistics-battle-records.json'
        if archive.exists() and archive.stat().st_size <= 1_000_000:
            for battle in json.loads(archive.read_text(encoding='utf-8'))[-50:]:
                v = battle['counters']
                detail = (f"{battle['title']}\n\n"
                    f"Damage dealt: {v['TotalReceivedDamagesByEnemies']:,.2f}\n"
                    f"Damage received: {v['TotalReceivedDamagesByCharacters']:,.2f}\n"
                    f"Highest damage: {v['HighestReceivedDamagesByEnemies']:,.2f}\n"
                    f"Dodges: {v['DodgeCount']}   Parries: {v['ParryCount']}\n\n"
                    f"{battle['note']}")
                entries.append((battle['title'], detail))
        recent = deque(maxlen=950)
        # Rotation is bounded; skip malformed/torn lines instead of losing the view.
        for suffix in ('.3', '.2', '.1', ''):
            path = folder / ('statistics.jsonl' + suffix)
            if not path.exists() or path.stat().st_size > 5_000_000:
                continue
            with path.open(encoding='utf-8') as stream:
                for line in stream:
                    if len(line) > 65536:
                        continue
                    try:
                        row = json.loads(line)
                        if row.get('kind') == 'damage':
                            recent.append(row)
                    except (ValueError, TypeError):
                        continue
        for row in reversed(recent):
            try:
                e = row['value']; a = e['arguments']; damage = a['ReceivedDamages']
                stamp = datetime.fromtimestamp(row['delivery_time']).strftime('%b %d  %H:%M:%S')
                def identity(value):
                    return f"Object {value['index']} / serial {value['serial']}" if value else 'None'
                entries.append((f"{stamp}  |  {damage:,.2f} damage", (
                    f"Damage notification #{e['sequence']}\n\n"
                    f"Damage: {damage:,.2f}\n"
                    f"Source: {identity(a['SourceCharacter'])}\n"
                    f"Target: {identity(a['TargetCharacter'])}\n\n"
                    f"Session: {e['session']}\n"
                    "Historical identity only. Zero damage does not establish a dodge or shield.\n"
                    "Capture may begin mid-battle.")))
            except (KeyError, TypeError, ValueError, OverflowError):
                continue
        return Report('Statistics — Records',
            'Saved battle summaries and recent damage notifications.\n\n'
            'Select a record to inspect it. Newest damage records appear first.\n\n'
            'Damage is the engine callback value, not necessarily health lost. '
            'Skill breakdowns and defense success rates are not yet supported.'
            if entries else 'No recorded damage yet. Enable Statistics before combat.', tuple(entries))

    def record(self, kind, value):
        if self.sink is not None:
            payload = json.dumps({'kind': kind, 'delivery_time': time.time(), 'value': value}, allow_nan=False)
            self.sink.emit(logging.LogRecord('Statistics', logging.INFO, '', 0, payload, (), None))

    def enable(self, session):
        self.session = session
        folder = sdk_root() / 'logs'
        folder.mkdir(exist_ok=True)
        self.sink = RotatingFileHandler(folder / 'statistics.jsonl', maxBytes=4_000_000, backupCount=3, encoding='utf-8')
        catalog = capture()
        owner = catalog.find_class('BP_BattleSummaryStatsManager_C')
        functions = [o for o in catalog.objects if o.outer_index == owner.index and o.name == 'OnCharacterReceivedDamages']
        exemplars = [o for o in catalog.select('BP_BattleSummaryStatsManager_C') if not o.object_flags & 0x10]
        if len(functions) != 1 or not exemplars:
            raise RuntimeError('Verified Statistics callback or live exemplar unavailable')
        self.trace = session.trace(functions[0], exemplars[0], duration_ms=300000, limit=1000)
        session.console.expose('statistics_mod', self)
        session.console.register('stats.status', lambda _: self.status(), owner=self)
        session.console.register('stats.summary', lambda _: self.summary(), owner=self)
        self.next_poll = self.next_renew = 0
        self.record('enabled', {'function': catalog.path_name(functions[0]), 'phase': self.trace.plan.phase})

    def poll(self):
        if self.trace is None or self.error:
            return
        now = time.monotonic()
        if now < self.next_poll:
            return
        self.next_poll = now + .1
        try:
            for _ in range(8):
                events = self.trace.read()
                for event in events:
                    row = dict(sequence=event.sequence, session=event.session, pid=event.pid,
                        monotonic_ms=event.monotonic_ms, thread=event.thread, phase=event.phase,
                        receiver={'index':event.index,'serial':event.serial},
                        arguments={name: asdict(value) if hasattr(value, '__dataclass_fields__') else value
                                   for name,value in event.arguments.items()})
                    self.events.append(row)
                    self.count += 1
                    self.record('damage', row)
                if len(events) < 8:
                    break
            if now >= self.next_renew:
                status = self.trace.status()
                self.last_status = dict(observed=status.observed, dropped=status.dropped,
                    rejected=status.rejected, cleanup=status.cleanup, state=self.trace.state)
                self.incomplete |= bool(status.dropped or status.rejected)
                if self.trace.state != 'active':
                    self.incomplete = True
                    self.error = 'Trace stopped; re-enable Statistics after travel to acquire a fresh function'
                else:
                    self.trace.renew(duration_ms=300000, limit=1000)
                self.next_renew = now + 10
                self.record('status', self.status())
        except Exception as error:
            self.incomplete = True
            self.error = str(error)
            self.record('error', self.error)
            # Stop on uncertainty; scope cleanup remains the final backstop.
            self.trace.close()
            self.trace = None

    def status(self):
        return dict(captured=self.count, retained=len(self.events), incomplete=self.incomplete,
                    error=self.error, native=self.last_status, parity='unverified')

    def summary(self):
        catalog = capture()
        rows = []
        for manager in catalog.select('BP_BattleSummaryStatsManager_C'):
            if manager.object_flags & 0x10:
                continue
            values = read_values(catalog, manager)
            counters = {name:value for (_,name),value in values.values.items() if name in COUNTERS}
            rows.append(dict(path=catalog.path_name(manager), index=manager.index, serial=manager.serial,
                counters=counters, missing=[name for name in COUNTERS if name not in counters]))
        self.record('summary', rows)
        return rows

    def disable(self):
        try:
            if self.trace is not None:
                self.trace.close()
                self.trace = None
            self.record('disabled', self.status())
        finally:
            if self.sink is not None:
                self.sink.close()
                self.sink = None
            self.session = None
