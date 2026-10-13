"""Native E33 object browser over the SDK's bounded reflection adapter."""
import copy
import json
from expedition33.paths import sdk_root
from pathlib import Path
import shlex
import time
import re

from expedition33.introspection import Harness
from expedition33.management import Action, Keybind, ModDefinition, ManagementError
from expedition33.management_view import MenuControl, MenuFrame
from expedition33.menu import MenuError

def friendly(name):
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', str(name)).replace('_', ' ')

PRESETS = (('World actors', 'Actor'), ('Characters', 'Character'),
           ('Movement components', 'MovementComponent'), ('Actor components', 'ActorComponent'),
           ('Widgets', 'UserWidget'), ('Inventory objects', 'Object', 'Inventory'),
           ('Loaded classes', 'Class'), ('Game systems', 'Object', 'Manager'))


def summary(value):
    if isinstance(value, list):
        return f'{len(value)} items' + (': ' + summary(value[0]) if len(value) == 1 else '')
    if isinstance(value, dict):
        if '$object' in value:
            return value['$object'].rsplit('.', 1)[-1]
        if '$error' in value:
            return 'Unavailable: ' + value['$error']
        if '$removed' in value:
            return 'REMOVED (previously ' + summary(value['$removed']) + ')'
        if '$struct' in value:
            return value['$struct']
        if 'items' in value and 'length' in value:
            return f"Array ({value['length']}; observed {len(value['items'])})"
        return f'{len(value)} fields'
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
        self.mode = 'simple'
        self.filter = ''
        self.bookmarks = []
        self.observed_at = None
        self.live = False
        self.interval = 1.0
        self.next_refresh = 0.0
        self.monitor_error = ''
        self.draft = None

    def refresh(self):
        # On failure clear the old display, rather than presenting it as fresh.
        self.result = {}
        self.observed_at = None
        self.generation += 1
        try:
            request=copy.deepcopy(self.request)
            if self.live and len(self.path)==1: request['members']=[self.path[0]]
            self.result = self.harness.request(request)
            self.observed_at = time.monotonic()
        except Exception:
            self.path = []
            raise
        try:
            self.node()
        except (KeyError, IndexError, TypeError):
            self.path = []
            if self.live:
                self.live = False
                raise ValueError('Monitored property disappeared; monitoring stopped')
        return self.result

    def navigate(self, request):
        self.live = False
        self.draft = None
        self.history.append((copy.deepcopy(self.request), list(self.path)))
        self.history = self.history[-64:]
        self.request, self.path = request, []
        self.changed_only = False
        self.filter = ''
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
            present = dict(list(value.items()) if isinstance(value, dict) else list(enumerate(value)) if isinstance(value, list) else [('Value', value)])
            rows += [(k, {'$removed': before[k]}) for k in before if k not in present]
        if self.mode == 'simple':
            rows = [(k, v) for k, v in rows if k not in ('$address', '$index', '$serial')]
        if self.filter:
            query = self.filter.casefold()
            by_value = query.startswith('value:')
            if by_value: query = query[6:]
            rows = [(k, v) for k, v in rows if query in (json.dumps(v, ensure_ascii=False).casefold() if by_value else str(k).casefold())]
        return rows

    def set_filter(self, query):
        if len(query) > 256: raise ValueError('Filter is limited to 256 characters')
        self.filter = query
        self.generation += 1

    def bookmark(self):
        value = (copy.deepcopy(self.request), list(self.path))
        if value not in self.bookmarks:
            if len(self.bookmarks) >= 32: raise ValueError('32 session bookmark limit')
            self.bookmarks.append(value)

    def open_bookmark(self, index):
        request, path = copy.deepcopy(self.bookmarks[index])
        self.navigate(request)
        self.path = path
        try: self.node()
        except (KeyError, IndexError, TypeError):
            self.path = []
            raise ValueError('Bookmarked field no longer exists; returned to object')

    def toggle_live(self):
        if not self.live and (self.request.get('op') != 'inspect' or len(self.path)!=1 or type(self.node()) not in (bool,int,float,str,type(None))):
            raise ValueError('Select a direct scalar property before enabling focused live monitoring')
        self.live = not self.live
        self.next_refresh = time.monotonic() + self.interval
        self.monitor_error = ''

    def poll(self, visible):
        if not visible:
            self.live = False
        if not self.live or time.monotonic() < self.next_refresh: return False
        started = time.monotonic()
        try:
            self.refresh()
            node = self.node()
            if isinstance(node, dict) and '$error' in node:
                raise ValueError(node['$error'])
        except Exception as error:
            self.live = False
            self.monitor_error = str(error)
        self.next_refresh = time.monotonic() + max(self.interval, 4 * (time.monotonic()-started))
        return True

    def stage_edit(self, value):
        if self.request.get('op') != 'inspect' or len(self.path) != 1:
            raise ValueError('Select a direct object property first; nested writes are unsupported')
        target = self.request['target']
        if not target.get('$identity'):
            raise ValueError('Editing requires identity-aware SDK support; restart with the updated SDK')
        member = self.path[0]
        self.refresh()
        if self.path != [member]: raise ValueError('Selected property disappeared')
        before = copy.deepcopy(self.node())
        if type(before) in (bool,int,float):
            if type(before) is bool and type(value) is not bool:
                raise ValueError('Boolean properties require true or false')
            if type(before) in (int,float) and type(value) not in (int,float):
                raise ValueError('Numeric properties require a number')
            if type(before) is int and type(value) is not int:
                raise ValueError('Integer properties require an integer')
            import math
            if type(value) is float and not math.isfinite(value):
                raise ValueError('Numeric properties require a finite number')
        else:
            if value is not None and not (isinstance(value,dict) and '$object' in value and '$identity' in value):
                raise ValueError('Expected null or an identity-bearing object reference')
            if before is not None and not (isinstance(before,dict) and '$object' in before):
                raise ValueError('This property has no supported editor')
        self.live = False
        self.draft = dict(target=copy.deepcopy(target), member=member,
                          before=before, value=copy.deepcopy(value), deadline=time.monotonic()+30)
        return {'staged':member, 'before':before, 'after':value, 'expires_seconds':30}

    def apply_edit(self):
        draft=self.draft
        self.draft=None # Consume before dispatch; never retry an uncertain write.
        if draft is None or time.monotonic()>draft['deadline']: raise ValueError('Edit expired or absent; stage again')
        observed=self.harness.request({'op':'inspect','target':draft['target'],'members':[draft['member']],'limit':1,'depth':2})
        if observed.get('values',{}).get(draft['member'],{'missing':True}) != draft['before']:
            raise ValueError('Property changed since staging; edit rejected')
        result=self.harness.request({'op':'set','target':draft['target'],'member':draft['member'],
                                     'value':draft['value'],'expected':draft['before'],'allow_mutation':True})
        self.refresh()
        return result

    def changed(self, key, value):
        return (self.baseline is not None and self.baseline[0] == self.scope()
                and (key not in self.baseline[1] or self.baseline[1][key] != value))

    def select(self, key):
        self.live=False
        self.draft=None
        value = self.node()
        if not isinstance(value, (dict, list)):
            return
        selected = value[key]
        if isinstance(selected, dict) and '$removed' in selected:
            raise ValueError('Removed field is a snapshot observation, not a live reference')
        if (isinstance(selected, dict) and '$object' in selected
                and not (self.request['op'] == 'inspect' and not self.path)):
            return self.navigate({'op': 'inspect', 'target': selected, 'limit': 64, 'depth': 4})
        self.history.append((copy.deepcopy(self.request), list(self.path)))
        self.history = self.history[-64:]
        self.path.append(key)
        self.changed_only = False
        self.generation += 1

    def back(self):
        self.live=False
        self.draft=None
        if self.history:
            self.request, self.path = self.history.pop()
            self.changed_only = False
            return self.refresh()

    def follow_reference(self):
        value = self.node()
        if not isinstance(value, dict) or '$object' not in value:
            raise ValueError('Select an object-reference property first')
        return self.navigate({'op': 'inspect', 'target': value, 'limit': 64, 'depth': 4})

    def next_batch(self):
        offset = self.result.get('next_offset')
        if offset is None or self.path:
            raise ValueError('No further reflected batch at this node')
        return self.navigate(dict(self.request, offset=offset))

    def snapshot(self):
        self.refresh()
        self.changed_only = False
        value = self.node()
        rows = value.items() if isinstance(value, dict) else enumerate(value) if isinstance(value, list) else [('Value', value)]
        self.baseline = (self.scope(), copy.deepcopy(dict(rows)))
        return {'captured_fields': len(self.baseline[1]), 'scope': self.baseline[0]}


class BrowserView:
    PAGE_SIZE = 8

    def __init__(self, registry, browser):
        self.registry, self.browser = registry, browser
        self.closed = False
        self.revision = 0
        self.page = 0
        self.status = ''
        self._generation = -1
        self._controls = {}
        self.screen = 'browse'

    def tool(self, action):
        b = self.browser
        if action == 'roots': b.navigate({'op': 'roots'})
        elif action == 'refresh': b.refresh()
        elif action == 'mode': b.mode = 'advanced' if b.mode == 'simple' else 'simple'; b.generation += 1
        elif action == 'snapshot': b.snapshot()
        elif action == 'changes':
            if b.baseline is None or b.baseline[0] != b.scope(): raise ValueError('Capture a snapshot at this node first')
            b.refresh(); b.changed_only = not b.changed_only
        elif action == 'bookmark': b.bookmark()
        elif action == 'clearfilter': b.set_filter('')
        elif action == 'schema':
            cls = b.request.get('target', {}).get('class')
            if not cls: raise ValueError('Select a live object first')
            b.navigate({'op': 'schema', 'class': cls, 'limit': 64})
        elif action == 'nextbatch': b.next_batch()
        elif action == 'live': b.toggle_live()
        elif action == 'apply': b.apply_edit()
        elif action == 'cancel': b.draft=None
        elif action == 'editnull': b.stage_edit(None)
        elif action == 'togglebool':
            if type(b.node()) is not bool: raise ValueError('Select a boolean property first')
            b.stage_edit(not b.node())
        elif action in ('increment','decrement'):
            if type(b.node()) not in (int,float): raise ValueError('Select a numeric property first')
            b.stage_edit(b.node() + (1 if action=='increment' else -1))
        elif action == 'follow': b.follow_reference()
        self.screen = 'browse'; self.page = 0

    def render(self):
        self.registry._check()
        if self.closed:
            raise ManagementError('Object viewer is closed')
        self.revision += 1
        if self._generation != self.browser.generation:
            if self.screen == 'browse':
                self.page = 0
            self._generation = self.browser.generation
        if self.screen == 'tools':
            rows = [('live','Live monitoring: '+('ON' if self.browser.live else 'OFF')),
                    ('snapshot','Capture snapshot'), ('changes','Compare with snapshot'),
                    ('editnull','Stage null object-reference edit'), ('apply','APPLY staged edit'), ('cancel','Cancel staged edit'),
                    ('roots','Player / world roots'), ('refresh','Refresh this observation'),
                    ('mode','Mode: '+self.browser.mode), ('schema','Properties and function signatures'),
                    ('bookmark','Bookmark this node'), ('clearfilter','Clear field filter'),
                    ('nextbatch','Next reflected batch'), ('presets','Search loaded objects'),
                    ('bookmarks','Open bookmark'), ('follow','Follow selected object reference'),
                    ('togglebool','Stage boolean toggle'), ('increment','Stage numeric +1'),
                    ('decrement','Stage numeric -1')]
        elif self.screen == 'presets': rows = list(enumerate(PRESETS))
        elif self.screen == 'bookmarks': rows = list(enumerate(self.browser.bookmarks))
        else: rows = self.browser.rows()
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._pages = pages
        self.page = min(self.page, pages - 1)
        self._controls = {}
        controls = []
        for index, (key, value) in enumerate(rows[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]):
            self._controls[100 + index] = key
            marker = '* ' if self.browser.changed(key, value) else ''
            if self.screen == 'tools': label = value
            elif self.screen == 'presets': label = value[0]
            elif self.screen == 'bookmarks': label = value[0].get('target', {}).get('$object', value[0].get('class', value[0]['op'])) + ' / ' + '/'.join(map(str,value[1]))
            else:
                label = friendly(key) if self.browser.mode == 'simple' else str(key)
                if isinstance(value, dict) and '$object' in value: label = summary(value)
                else: label += ': ' + summary(value)
            controls.append(MenuControl(100 + index, marker + label))
        controls.extend((MenuControl(1, 'Back', self.screen != 'browse' or bool(self.browser.history)),
                         MenuControl(2, 'Inspect tools' if self.screen == 'browse' else 'Return to object'),
                         MenuControl(3, 'Previous page', self.page > 0),
                         MenuControl(4, 'Next page' if self.page + 1 < pages else 'First page', pages > 1),
                         MenuControl(6, 'Close')))
        # Eight rows + five navigation buttons would exceed the shared panel.
        # On multi-page screens Previous/Next is a single page-cycle control.
        controls = [c for c in controls if c.token != 3]
        self._enabled = {c.token for c in controls if c.enabled}
        target = self.browser.request.get('target', {}).get('$object', self.browser.request.get('class', 'Live roots'))
        description = target + '\n' + ' / '.join(map(str, self.browser.path))
        node = self.browser.node()
        if not isinstance(node, (list, dict)) or (isinstance(node, dict) and any(k in node for k in ('$error', '$truncated'))):
            description += '\n\n' + json.dumps(node, ensure_ascii=False, indent=2)
        age = '?' if self.browser.observed_at is None else str(int(time.monotonic()-self.browser.observed_at))+'s'
        description += f'\n\n{self.browser.mode.title()} mode | age when drawn {age}\n{len(rows)} rows in this batch. Filter: {self.browser.filter or "none"}'
        description += '\nLive: '+('ON' if self.browser.live else 'OFF')
        if self.browser.monitor_error: description += '\nMonitoring stopped: '+self.browser.monitor_error
        if self.browser.draft:
            description += '\nPENDING WRITE: '+self.browser.draft['member']+'\n'+summary(self.browser.draft['before'])+' → '+summary(self.browser.draft['value'])
        description += '\nInspect tools: roots, search groups, schema, snapshots and bookmarks.\nField filter: lov_filter text\nObject search: lov_search Class text\nManual refresh; collections may be truncated.'
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
                key = self._controls[token]
                if self.screen == 'tools':
                    if key in ('presets','bookmarks'): self.screen=key; self.page=0
                    else: self.tool(key)
                elif self.screen == 'presets':
                    preset=PRESETS[key]
                    self.browser.navigate({'op':'search','class':preset[1],'query':preset[2] if len(preset)>2 else '', 'limit':64,'scan':5000})
                    self.screen='browse'
                elif self.screen == 'bookmarks': self.browser.open_bookmark(key); self.screen='browse'
                else: self.browser.select(key)
            elif token == 1:
                if self.screen != 'browse': self.screen='browse'; self.page=0
                else: self.browser.back()
            elif token == 2:
                self.screen = 'tools' if self.screen == 'browse' else 'browse'
                self.page=0
            elif token in (3, 4):
                self.page = (self.page + 1) % max(1, self._pages)
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
        self.browser.live = False
        self.browser.draft = None
        self.closed = True
        self.revision += 1


class Mod:
    def __init__(self):
        self.session = self.harness = self.browser = self.native = self.shared = None
        self.commands = []

    def management(self):
        return ModDefinition('sdk.live-object-viewer', 'Live Object Viewer', version='0.2.0',
            description='Native live roots, property monitoring, guarded edits, schemas and scoped snapshots.',
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
                    'lov_filter': self.filter, 'lov_mode': self.mode,
                    'lov_live': lambda _: self._paint(self.browser.toggle_live()),
                    'lov_edit': lambda args: self._paint(self.browser.stage_edit(json.loads(args))),
                    'lov_apply': lambda _: self._paint(self.browser.apply_edit()),
                    'lov_cancel': lambda _: setattr(self.browser,'draft',None),
                    'lov_bookmark': lambda _: self._paint(self.browser.bookmark()),
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
        if not self.browser.result or self.browser.request['op'] == 'roots':
            self.browser.refresh()
        try:
            return self.native.open()
        except MenuError as error:
            if error.outcome == 'returned' and error.native_error == 902:
                # This acknowledged preparation rejection has not attached the
                # panel or changed focus. Release its owner so it cannot poison
                # later opens after the player exits the conflicting game UI.
                self.native.close_menu()
                raise ManagementError('Close the game\'s party/inventory screen, then open the viewer again; its current focus cannot be restored safely.') from error
            raise

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

    def filter(self, arguments):
        return self._paint(self.browser.set_filter(arguments.strip()))

    def mode(self, arguments):
        mode=arguments.strip().lower()
        if mode not in ('simple','advanced'): raise ValueError('Use lov_mode simple|advanced')
        self.browser.mode=mode
        self.browser.generation+=1
        return self._paint({'mode':mode})

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
        if self.browser:
            visible=self.native.menu is not None and self.native.menu.panel.state == 'open'
            if self.browser.poll(visible): self._paint(None)

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
