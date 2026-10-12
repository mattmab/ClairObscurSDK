"""Native E33 object browser over the SDK's bounded reflection adapter."""
import copy
import json
from expedition33.paths import sdk_root
from pathlib import Path
import shlex
import time

from expedition33.introspection import Harness
from expedition33.management import Action, Keybind, ModDefinition, ManagementError
from expedition33.management_view import MenuControl, MenuFrame


def summary(value):
    if isinstance(value, dict):
        if '$object' in value:
            return value['$object'].rsplit('.', 1)[-1]
        if '$error' in value:
            return 'Unavailable: ' + value['$error']
        if '$struct' in value:
            return value['$struct']
        if 'items' in value and 'length' in value:
            return f"Array ({value['length']}; observed {len(value['items'])})"
    return json.dumps(value, ensure_ascii=False)[:160]


class Browser:
    """Only JSON observations survive a request; never retain engine pointers."""
    def __init__(self, harness):
        self.harness = harness
        self.request = {'op': 'roots'}
        self.result = {}
        self.path = []
        self.history = []
        self.baseline = None
        self.changed_only = False
        self.generation = 0

    def refresh(self):
        # On failure clear the old display, rather than presenting it as fresh.
        self.result = {}
        self.generation += 1
        try:
            self.result = self.harness.request(copy.deepcopy(self.request))
        except Exception:
            self.path = []
            raise
        try:
            self.node()
        except (KeyError, IndexError, TypeError):
            self.path = []
        return self.result

    def navigate(self, request):
        self.history.append((copy.deepcopy(self.request), list(self.path)))
        self.history = self.history[-64:]
        self.request, self.path = request, []
        self.changed_only = False
        return self.refresh()

    def node(self):
        value = self.result.get('values', self.result.get('objects', self.result))
        if self.request['op'] == 'schema':
            value = {k: v for k, v in self.result.items() if k != 'next_offset'}
        for key in self.path:
            value = value[key]
        return value

    def scope(self):
        return json.dumps([self.request, self.path], sort_keys=True)

    def rows(self):
        value = self.node()
        rows = list(value.items()) if isinstance(value, dict) else list(enumerate(value)) if isinstance(value, list) else [('Value', value)]
        if self.changed_only:
            if self.baseline is None or self.baseline[0] != self.scope():
                return []
            before = self.baseline[1]
            rows = [(k, v) for k, v in rows if k not in before or before[k] != v]
        return rows

    def changed(self, key, value):
        return (self.baseline is not None and self.baseline[0] == self.scope()
                and (key not in self.baseline[1] or self.baseline[1][key] != value))

    def select(self, key):
        value = self.node()
        if not isinstance(value, (dict, list)):
            return
        selected = value[key]
        if isinstance(selected, dict) and '$object' in selected:
            return self.navigate({'op': 'inspect', 'target': selected, 'limit': 64, 'depth': 4})
        self.history.append((copy.deepcopy(self.request), list(self.path)))
        self.history = self.history[-64:]
        self.path.append(key)
        self.changed_only = False
        self.generation += 1

    def back(self):
        if self.history:
            self.request, self.path = self.history.pop()
            self.changed_only = False
            return self.refresh()

    def next_batch(self):
        offset = self.result.get('next_offset')
        if offset is None or self.path:
            raise ValueError('No further reflected batch at this node')
        return self.navigate(dict(self.request, offset=offset))

    def snapshot(self):
        self.refresh()
        self.changed_only = False
        self.baseline = (self.scope(), copy.deepcopy(dict(self.rows())))
        return {'captured_fields': len(self.baseline[1]), 'scope': self.baseline[0]}


class BrowserView:
    PAGE_SIZE = 6

    def __init__(self, registry, browser):
        self.registry, self.browser = registry, browser
        self.closed = False
        self.revision = 0
        self.page = 0
        self.status = ''
        self._generation = -1
        self._controls = {}

    def render(self):
        self.registry._check()
        if self.closed:
            raise ManagementError('Object viewer is closed')
        self.revision += 1
        if self._generation != self.browser.generation:
            self.page = 0
            self._generation = self.browser.generation
        rows = self.browser.rows()
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        self._controls = {}
        controls = []
        for index, (key, value) in enumerate(rows[self.page * 6:(self.page + 1) * 6]):
            self._controls[100 + index] = key
            marker = '* ' if self.browser.changed(key, value) else ''
            controls.append(MenuControl(100 + index, f'{marker}{key}: {summary(value)}'))
        controls.extend((MenuControl(1, 'Back', bool(self.browser.history)),
                         MenuControl(2, 'Refresh'),
                         MenuControl(3, 'Previous page', self.page > 0),
                         MenuControl(4, 'Next page', self.page + 1 < pages),
                         MenuControl(5, 'Next reflected batch', not self.browser.path and self.browser.result.get('next_offset') is not None),
                         MenuControl(6, 'Close')))
        self._enabled = {c.token for c in controls if c.enabled}
        target = self.browser.request.get('target', {}).get('$object', self.browser.request.get('class', 'Live roots'))
        description = target + '\n' + ' / '.join(map(str, self.browser.path))
        node = self.browser.node()
        if not isinstance(node, (list, dict)) or (isinstance(node, dict) and any(k in node for k in ('$error', '$truncated'))):
            description += '\n\n' + json.dumps(node, ensure_ascii=False, indent=2)
        description += '\n\nRead-only observations. Refresh to reread.\nSearch: lov_search Class query\nSnapshot: lov_snapshot\nChanges: lov_changes\nSchema: lov_schema'
        if self.browser.baseline:
            description += '\nBaseline: ' + ('this node' if self.browser.baseline[0] == self.browser.scope() else 'another node')
        return MenuFrame(self.revision, 'E33 Live Object Viewer', description,
                         tuple(controls), self.page, pages, self.status, False)

    def activate(self, revision, token, **_):
        self.registry._check()
        if (self.closed or revision != self.revision or token not in self._enabled
                or self._generation != self.browser.generation):
            raise ManagementError('Stale or unavailable object viewer control')
        self.revision += 1
        try:
            if token in self._controls:
                self.browser.select(self._controls[token])
            elif token == 1:
                self.browser.back()
            elif token == 2:
                self.browser.refresh()
            elif token in (3, 4):
                self.page += -1 if token == 3 else 1
            elif token == 5:
                self.browser.next_batch()
            elif token == 6:
                self.close()
                return MenuFrame(self.revision, 'E33 Live Object Viewer', '', (), 0, 1, '', True)
            self.status = ''
        except Exception as error:
            self.status = str(error)
        return self.render()

    def close(self):
        self.closed = True
        self.revision += 1


class Mod:
    def __init__(self):
        self.session = self.harness = self.browser = self.native = self.shared = None
        self.commands = []

    def management(self):
        return ModDefinition('sdk.live-object-viewer', 'Live Object Viewer', version='0.1.1',
            description='Native live roots, class/object search, properties, schemas and scoped snapshots. Read-only E33 adapter.',
            actions=(Action('open', 'Open Live Object Viewer', lambda _: self.open()),),
            keybinds=(Keybind('toggle', 'Toggle Live Object Viewer', None, lambda _: self.toggle()),))

    def enable(self, session):
        shared = getattr(session._session, '_native_menu_service', None)
        if shared is None or not callable(getattr(shared, 'for_view', None)):
            raise RuntimeError('Live Object Viewer requires SDK Management with shared native views; restart the updated SDK controller')
        self.session = session
        self.shared = shared
        self.harness = Harness(session=session)
        self.browser = Browser(self.harness)
        # A second 12-control tree exceeds the runtime's shared lease pool.
        # SDK Management owns the sole panel; this mod owns only its presenter.
        self.native = shared.for_view(lambda registry: BrowserView(registry, self.browser))
        session.console.expose('lov', self)
        commands = {'lov': lambda _: self.open(), 'lov_open': lambda _: self.open(),
                    'lov_close': lambda _: self.native.close_menu(),
                    'lov_roots': lambda _: self.roots(), 'lov_refresh': lambda _: self.refresh(),
                    'lov_search': self.search, 'lov_schema': self.schema,
                    'lov_snapshot': lambda _: self.snapshot(), 'lov_changes': lambda _: self.changes(),
                    'lov_snapshot_clear': lambda _: self.clear_snapshot(),
                    'lov_dump': lambda _: self.dump(), 'lov_back': lambda _: self.back(),
                    'lov_next': lambda _: self.next_batch()}
        for name, callback in commands.items():
            self.commands.append(session.console.register(name, callback, owner=self))

    def _paint(self, result):
        if self.native.menu is not None and self.native.menu.panel.state == 'open':
            self.shared.refresh()
        return result

    def open(self):
        if self.native.menu is not None and self.native.menu.panel.state == 'open':
            return 'Live Object Viewer is already open'
        if not self.browser.result:
            self.browser.refresh()
        return self.native.open()

    def toggle(self):
        if self.native.menu is not None and self.native.menu.panel.state == 'open':
            return self.native.close_menu()
        return self.open()

    def roots(self):
        return self._paint(self.browser.navigate({'op': 'roots'}))

    def refresh(self):
        try:
            return self.browser.refresh()
        finally:
            self._paint(None)

    def search(self, arguments):
        words = shlex.split(arguments)
        if not words:
            raise ValueError('Use lov_search Class [path text]; e.g. lov_search Actor player')
        return self._paint(self.browser.navigate({'op': 'search', 'class': words[0],
            'query': ' '.join(words[1:]), 'limit': 64, 'scan': 5000}))

    def schema(self, arguments=''):
        cls = arguments.strip() or self.browser.request.get('target', {}).get('class')
        if not cls:
            raise ValueError('Select an object or use lov_schema Class')
        return self._paint(self.browser.navigate({'op': 'schema', 'class': cls, 'limit': 64}))

    def snapshot(self):
        return self._paint(self.browser.snapshot())

    def changes(self):
        if self.browser.baseline is None or self.browser.baseline[0] != self.browser.scope():
            raise ValueError('Capture a snapshot at this exact node first')
        self.browser.refresh()
        self.browser.changed_only = not self.browser.changed_only
        return self._paint({'changed_only': self.browser.changed_only})

    def clear_snapshot(self):
        self.browser.baseline = None
        self.browser.changed_only = False
        return self._paint({'baseline': None})

    def back(self):
        return self._paint(self.browser.back())

    def next_batch(self):
        return self._paint(self.browser.next_batch())

    def dump(self):
        directory = sdk_root() / 'logs' / 'LiveObjectViewer'
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / f'observation-{time.time_ns()}.json'
        destination.write_text(json.dumps({'request': self.browser.request, 'path': self.browser.path,
            'observation': self.browser.result, 'baseline': self.browser.baseline,
            'note': 'Bounded last observation; unsupported/truncated values are explicit.'}, indent=2, ensure_ascii=False), encoding='utf-8')
        return {'saved': str(destination)}

    def poll(self):
        # SDK Management polls the shared panel. Never construct or poll a
        # second panel here, including while another view is active.
        pass

    def disable(self):
        if self.native:
            self.native.close()
            self.native = None
        for command in self.commands:
            command.remove()
        self.commands.clear()
        if self.harness:
            self.harness.close()
        self.harness = self.browser = self.session = self.shared = None
