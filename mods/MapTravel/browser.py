"""Map browser implementing the installed scrollable Mods workspace contract."""
import re
import logging
from expedition33.management import ManagementError
from expedition33.management_view import MenuControl, MenuFrame
from expedition33.mods_workspace_scroll import ScrollWorkspaceView, EMPTY, CONTROL_COUNT, row_token


def grouped_maps(rows):
    groups = {}
    for row in rows:
        title = re.sub(r' \d+$', '', row['title']).strip()
        groups.setdefault(title.casefold(), dict(title=title, maps=[]))['maps'].append(row)
    return sorted(groups.values(), key=lambda group: group['title'].casefold())


class MapView(ScrollWorkspaceView):
    native_scroll_list = True

    def __init__(self, registry, model):
        super().__init__(registry)
        self.model = model
        self.screen = 'map_list'
        self.group = self.selected = None
        self.groups = grouped_maps(model.maps)
        self.binding_start = 0

    @staticmethod
    def map_token(index):
        return index if index < 48 else 81 + index - 48

    def bindable_tokens(self):
        # Keep a generous window of handlers registered, within the runtime's
        # 64-handler limit. Every row's widget and label stay in place.
        return ({self.map_token(i) for i in range(self.binding_start,
                min(self.total_rows, self.binding_start + 48))}
                | set(range(48, 81)))

    def update_scroll_bindings(self, first_visible):
        end = min(self.total_rows, first_visible + 9)
        if first_visible >= self.binding_start and end <= self.binding_start + 48:
            return False
        self.binding_start = min(max(0, first_visible - 16), max(0, self.total_rows - 48))
        return True

    def reset_scroll(self):
        super().reset_scroll()
        self.binding_start = 0

    def render(self):
        self._check()
        self._invalidate()
        controls = [EMPTY] * CONTROL_COUNT
        self.row_states = []
        def add(index, label, operation, argument=None, enabled=True):
            controls[index] = MenuControl(index, label, enabled)
            self._commands[index] = (operation, argument, enabled)
        groups = self.groups
        if self.group is None:
            rows = [(g['title'] + (f" ({len(g['maps'])})" if len(g['maps']) > 1 else ''), 'group', g)
                    for g in groups if self.query in (g['title'] + ' ' + ' '.join(r['package'] for r in g['maps'])).casefold()]
        else:
            maps = self.group['maps']
            rows = [(r['title'] if sum(other['title'] == r['title'] for other in maps) == 1
                     else r['package'].rsplit('/', 1)[-1], 'destination', r) for r in maps]
        if len(rows) > 72:
            raise ManagementError('Installed map catalog exceeds the 72 native row slots')
        self.total_rows = len(rows)
        self.scroll_start = 0
        for i, (label, operation, argument) in enumerate(rows):
            add(self.map_token(i), label, operation, argument)
        description = f'{len(self.model.maps)} maps in {len(groups)} groups.\n\nSelect a map, then Travel to entrance.'
        if self.selected:
            row = self.selected
            description = row['title'] + '\n\n' + row['package']
            if row.get('normal_route'):
                description += '\n\nTravels directly to the entrance using the normal zone transition.'
            else:
                description += '\n\nNo normal entrance route is available for this map.'
            if row['experimental']:
                description += '\nConcept map: gameplay entrance is unverified.'
            add(60, 'Travel to entrance', 'travel', row['package'], not self.model.busy and bool(row.get('normal_route')))
        elif self.group:
            description = self.group['title'] + '\n\nSelect a variant to inspect its exact map path.'
        add(48, 'All maps', 'back', enabled=self.group is not None or self.selected is not None)
        add(51, 'Close', 'close')
        add(52, 'Search', 'search')
        add(54, 'Clear', 'clear')
        for index, label, delta in ((78, '-', -.1), (79, '+', .1), (80, 'Reset', None)):
            add(index, label, 'text_scale', delta)
        return MenuFrame(self._revision, 'Map Travel', description, tuple(controls), 0, 1,
                         self.model.message, False)

    def activate(self, revision, token, **values):
        self._check()
        if type(revision) is not int or revision != self._revision:
            raise ManagementError('Stale map control')
        command = self._commands.get(token)
        if command is None or not command[2]:
            raise ManagementError('Map control is unavailable')
        operation, argument, _ = command
        if operation == 'text_scale':
            return super().activate(revision, token, **values)
        self._invalidate()
        if operation == 'close':
            self.close()
        elif operation in ('back', 'clear', 'search'):
            if operation == 'search':
                query = values.get('value', '')
                if type(query) is not str or len(query) > 256 or '\0' in query:
                    raise ManagementError('Search must be at most 256 characters')
                self.query = query.casefold()
            elif operation == 'clear':
                self.query = ''
            self.group = self.selected = None
            self.page = 0
            self.reset_scroll()
        elif operation == 'group':
            if len(argument['maps']) == 1:
                self.selected = argument['maps'][0]
            else:
                self.group, self.selected = argument, None
                self.page = 0
                self.reset_scroll()
        elif operation == 'destination':
            self.selected = argument
        elif operation == 'travel':
            logging.getLogger('expedition33.map_travel').info('Travel phase click')
            # Dispose the native widget tree only after its click callback returns.
            self.model.pending_travel = argument
            self.close()
        if self.closed:
            return MenuFrame(self._revision, 'Map Travel', '', (), 0, 1, self.model.message, True)
        return self.render()
