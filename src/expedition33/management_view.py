"""Registry-backed presentation for native controls; no second mod-state store.

Frames are immutable display snapshots. Every control carries a frame revision;
refresh/navigation revokes old controls before any registry mutation. Native
renderers may reuse their bounded set of widgets across these pages.
"""
from dataclasses import dataclass
import json

from .management import ManagementError, Selection, Report
from .keys import KEY_NAMES


@dataclass(frozen=True)
class MenuEditor:
    kind: str
    value: object = None
    default: object = None
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple = ()


@dataclass(frozen=True)
class MenuControl:
    token: int
    label: str
    enabled: bool = True
    editor: MenuEditor | None = None


@dataclass(frozen=True)
class MenuFrame:
    revision: int
    title: str
    description: str
    controls: tuple[MenuControl, ...]
    page: int
    pages: int
    status: str
    closed: bool


class ManagementView:
    """Owner-thread presenter for list/details/options/actions screens.

    Text/numeric editors submit a typed value through activate(value=...). Key
    capture and sliders belong to the native frontend, not this presenter.
    All settings and actions still use the same Registry as the console menu.
    """
    PAGE_SIZE = 8  # Eight rows plus back/previous/next/close fit the v17 pool.

    def __init__(self, registry):
        self.registry = registry
        self.selection = None
        self.binding_id = None
        self.screen = 'list'
        self.page = 0
        self.query = ''
        self.status = ''
        self.closed = False
        self._revision = 0
        self._commands = {}
        self.report = None
        self.report_detail = None

    def _check(self):
        self.registry._check()
        if self.closed:
            raise ManagementError('Native menu view is closed')

    def _invalidate(self):
        self._revision += 1
        self._commands.clear()

    def close(self):
        self.registry._check()
        self._invalidate()
        self.closed = True
        self.selection = None

    def search(self, query):
        self._check()
        if type(query) is not str or len(query) > 256 or '\0' in query:
            raise ManagementError('Search must be at most256 characters')
        self.query = query.casefold()
        self.selection = None
        self.screen, self.page = 'list', 0
        return self.render()

    def _rows(self):
        if self.screen == 'list':
            views = self.registry.views()
            loaded = {v['folder']: v for v in views}
            rows = []
            # Folder identity stays stable when loading supplies display metadata.
            for folder in sorted(set(loaded) | set(self.registry.installed()),
                                 key=lambda name: (name.casefold(), name)):
                if folder not in loaded:
                    if self.query in folder.casefold():
                        rows.append((f'{folder} [not loaded]', 'load', folder, True, None))
                    continue
                view = loaded[folder]
                if self.query not in ' '.join(str(view[k]) for k in
                        ('id', 'name', 'description', 'author')).casefold():
                    continue
                state = 'enabled' if view['enabled'] else 'disabled'
                rows.append((f"{view['name']} [{state}]", 'select',
                             Selection(view['id'], view['generation']), True, None))
            return 'SDK Mods', 'Select a mod to inspect settings and actions.', rows
        view = self.registry.view(self.selection)  # Reject a reloaded selection.
        if self.screen == 'report' and self.report is not None:
            return self.report.title, self.report_detail or self.report.description, [
                (label, 'report_detail', detail, True, None)
                for label, detail in self.report.entries]
        detail = '\n'.join(filter(None, (view['description'],
            ' '.join(filter(None, (view['author'], view['version']))), view['error'])))
        if self.screen == 'details':
            rows = [('Disable' if view['enabled'] else 'Enable', 'enable',
                     not view['enabled'], not (view['enabled'] and view['protected']), None),
                    ('Settings', 'screen', 'options', bool(view['options']), None),
                    ('Actions', 'screen', 'actions', bool(view['actions']), None),
                    ('Keybinds', 'screen', 'keybinds', bool(view['keybinds']), None),
                    ('Unload', 'unload', None, not view['protected'], None),
                    ('Startup load order', 'screen', 'startup', not view['protected'], None)]
        elif self.screen == 'startup':
            order=self.registry.startup_order()
            position=order.index(view['id'])+1 if view['id'] in order else len(order)+1
            detail=f"Startup position: {position} of {len(order)} optional mods. Changes apply next launch. Disabled mods stay disabled. World Builder must precede Custom Map Loader."
            rows=[('Move earlier','startup','earlier',position>1,None),
                  ('Move later','startup','later',position<len(order),None),
                  ('Load first','startup','first',position>1,None),
                  ('Reset default order','startup','defaults',True,None)]
        elif self.screen == 'keybinds':
            conflicts = self.registry.key_conflicts()
            rows = [(f"{b['title']}: {b['value'] or 'Unbound'}" +
                     (' [conflict]' if b['value'] in conflicts else ''),
                     'pick_key', b['id'], True, None) for b in view['keybinds']]
            detail += '\nSelect a binding to remap. Conflicting enabled bindings do not dispatch.'
            detail += '\nKey delivery requires the experimental v19 controller (--keybinds).'
        elif self.screen == 'key_picker':
            binding = next(b for b in view['keybinds'] if b['id'] == self.binding_id)
            detail += f"\n{binding['title']}: {binding['value'] or 'Unbound'}"
            rows = [('Unbind', 'key', None, True, None),
                    ('Reset to default', 'key_reset', None, True, None)]
            rows += [(key, 'key', key, True, None) for key in KEY_NAMES]
        elif self.screen == 'options':
            rows = []
            for option in view['options']:
                value = json.dumps(option['value'], ensure_ascii=False)
                rows.append((f"{option['title']}: {value}", 'option', option['id'],
                             True, MenuEditor(option['kind'], option['value'],
                                 option['default'], option['minimum'], option['maximum'],
                                 tuple(option['choices']))))
        else:
            rows = [(a['title'], 'action', a['id'], view['enabled'], MenuEditor('json'))
                    for a in view['actions']]
        return f"{view['name']} â€” {self.screen}", detail, rows

    def render(self):
        self._check()
        self._invalidate()
        try:
            title, description, rows = self._rows()
        except ManagementError as error:
            self.status = self.status or str(error)
            self.selection = None
            self.screen, self.page = 'list', 0
            title, description, rows = self._rows()
        pages = max(1, (len(rows) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        controls = []
        def add(label, command, argument, enabled=True, editor=None):
            token = len(controls)
            controls.append(MenuControl(token, label, enabled, editor))
            self._commands[token] = (command, argument, enabled)
        for row in rows[self.page * self.PAGE_SIZE:(self.page + 1) * self.PAGE_SIZE]:
            add(*row)
        add('Back', 'back', None, self.screen != 'list')
        add('Previous', 'page', -1, self.page > 0)
        add('Next', 'page', 1, self.page + 1 < pages)
        add('Close', 'close', None)
        return MenuFrame(self._revision, title, description, tuple(controls),
                         self.page, pages, self.status, False)

    def activate(self, revision, token, *, value=None, reset=False):
        self._check()
        if type(revision) is not int or revision != self._revision or type(token) is not int:
            raise ManagementError('Stale menu control; refresh the menu')
        command = self._commands.get(token)
        if command is None or not command[2]:
            raise ManagementError('Menu control is unavailable')
        operation, argument, _ = command
        self._invalidate()  # Invalidate even if a callback fails or mutates the registry.
        self.status = ''
        try:
            if operation == 'close':
                self.close()
                return MenuFrame(self._revision, 'SDK Mods', '', (), 0, 1, '', True)
            if operation == 'select':
                self.registry.view(argument)
                self.selection, self.screen, self.page = argument, 'details', 0
            elif operation == 'load':
                self.selection = self.registry.load(argument)
                self.screen, self.page = 'details', 0
            elif operation == 'back':
                self.screen = ('actions' if self.screen == 'report' else
                               'keybinds' if self.screen == 'key_picker' else
                               'list' if self.screen == 'details' else 'details')
                self.page = 0
                if self.screen == 'list': self.selection = None
            elif operation == 'page':
                self.page += argument
            elif operation == 'screen':
                self.registry.view(self.selection)
                self.screen, self.page = argument, 0
            elif operation == 'enable':
                self.selection = self.registry.set_enabled(self.selection, argument)
            elif operation == 'startup':
                position=self.registry.move_startup(self.selection,argument)
                self.status=f'Saved startup position {position}; applies next launch.'
            elif operation == 'unload':
                self.registry.unload(self.selection)
                self.selection, self.screen, self.page = None, 'list', 0
            elif operation == 'option':
                result = self.registry.set_option(self.selection, argument, value, reset=reset)
                self.status = 'Saved: ' + repr(result)[:2048]
            elif operation == 'pick_key':
                self.binding_id, self.screen, self.page = argument, 'key_picker', 0
            elif operation in ('key', 'key_reset'):
                self.selection = self.registry.set_keybind(self.selection, self.binding_id,
                    argument, reset=operation == 'key_reset')
                self.screen, self.page = 'keybinds', 0
                self.status = 'Key preference saved'
            elif operation == 'action':
                result = self.registry.invoke(self.selection, argument, value)
                if isinstance(result, Report):
                    self.report, self.report_detail = result, None
                    self.screen, self.page = 'report', 0
                else:
                    self.status = 'Result: ' + repr(result)[:2048]
            elif operation == 'report_detail':
                self.report_detail = argument
        except Exception as error:
            self.status = f'{type(error).__name__}: {str(error)[:2048]}'
        return self.render()

    def callback(self, frame, control, **submission):
        """Capture a frame token, never a mutable row index or a mod method."""
        if control not in frame.controls:
            raise ManagementError('Control does not belong to the supplied frame')
        # Values are validated by Registry at dispatch; copy mutable JSON now.
        submission = json.loads(json.dumps(submission, allow_nan=False))
        def dispatch(_event=None):
            return self.activate(frame.revision, control.token, **submission)
        return dispatch
