"""BL4 Mods Menu workflow adapted to E33's owned registry and native widgets.

The World Builder supplies the visual vocabulary: opaque navy background,
compact teal buttons, scaled game text and a separate inspector workspace.
No BL4 engine hooks or input ownership are reused.
"""
from dataclasses import replace
import json

from .management import ManagementError, Selection
from .management_view import ManagementView, MenuControl
from .management_native import NativeManagementMenu, display_detail, display_line
from .widgets import OwnedMenuPanel


THEMES = {
    'World Builder': ((.012, .018, .028), (.025, .045, .065), (.07, .14, .18)),
    'KAIROS Cyan': ((.03, .045, .055), (.065, .105, .125), (.02, .40, .48)),
    'Crimson': ((.045, .025, .03), (.13, .065, .075), (.48, .095, .15)),
    'Vault Gold': ((.04, .035, .022), (.12, .10, .065), (.43, .30, .06)),
    'Neutral Dark': ((.03, .032, .036), (.085, .09, .10), (.25, .29, .34)),
}


class ModsWorkspaceView(ManagementView):
    FILTERS = ('All', 'Enabled', 'Disabled', 'Options', 'Keybinds', 'Reloadable', 'Core', 'Not loaded')

    def __init__(self, registry):
        super().__init__(registry)
        self.filter_mode = 'All'
        self.editing = None
        self.bulk_plan = ()
        self.bulk_results = ()

    def _export(self, name, data):
        settings = self.registry._settings
        if settings is None:
            raise ManagementError('No settings directory is configured')
        path = settings.path.parent / 'ModsMenu' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    def _rows(self):
        if self.screen == 'all_keys':
            conflicts = self.registry.key_conflicts()
            rows = []
            for view in self.registry.views():
                for binding in view['keybinds']:
                    label = f"{view['name']} / {binding['title']}: {binding['value'] or 'Unbound'}"
                    if self.query and self.query not in label.casefold():
                        continue
                    if binding['value'] in conflicts:
                        label += ' [conflict]'
                    rows.append((label, 'global_key', (Selection(view['id'], view['generation']), binding['id']), True, None))
            return 'All keybinds', 'Select a binding to remap, unbind or restore its default.\n\nConflicting enabled bindings do not dispatch.', rows
        if self.screen == 'bulk':
            return 'Bulk mod actions', 'Applies to the currently loaded, unprotected mods. Each result is reported; failed operations are not retried.', [
                ('Enable all', 'bulk_confirm', True, True, None),
                ('Disable all', 'bulk_confirm', False, True, None),
                ('Reload enabled mods', 'bulk_confirm', 'reload', True, None),
                ('Unbind all user-mod keys', 'bulk_confirm', 'unbind', True, None),
                ('Restore all user-mod key defaults', 'bulk_confirm', 'reset_keys', True, None)]
        if self.screen == 'bulk_confirm':
            names = [view['name'] for view in self.bulk_plan]
            verb = ('enable' if self.bulk_enabled else 'disable') if type(self.bulk_enabled) is bool else self.bulk_enabled
            return 'Confirm bulk action', '\n'.join(names) or 'No mods need changing.', [
                (f'Confirm {verb} {len(names)} mods', 'bulk_apply', None, bool(names), None)]
        if self.screen == 'bulk_results':
            return 'Bulk results', 'Results saved in settings/ModsMenu/last_bulk_operation.json.', [
                (result, 'bulk_result', result, True, None) for result in self.bulk_results]
        title, detail, rows = super()._rows()
        if self.screen == 'list':
            views = {v['id']: v for v in self.registry.views()}
            def matches(row):
                if self.filter_mode == 'All':
                    return True
                if row[1] == 'load':
                    return self.filter_mode == 'Not loaded'
                if self.filter_mode == 'Not loaded':
                    return False
                view = views[row[2].mod_id]
                return {'Enabled': view['enabled'], 'Disabled': not view['enabled'],
                        'Options': bool(view['options']), 'Keybinds': bool(view['keybinds']),
                        'Reloadable': not view['protected'], 'Core': view['protected']}[self.filter_mode]
            rows = [row for row in rows if matches(row)]
            title = "Matt's E33 Mods Menu"
            detail = (f'INSTALLED MODS\n{len(rows)} matching mods • {self.filter_mode}\n\n'
                      'Select a mod to configure settings, actions and keybinds.\n\n'
                      'Type in the search field, then click Search. Search matches '
                      'name, author, description and module.\n\n'
                      'No matching mods.' if not rows else
                      f'INSTALLED MODS\n{len(rows)} matching mods • {self.filter_mode}\n\n'
                      'Select a mod to configure settings, actions and keybinds.\n\n'
                      'Type in the search field, then click Search.')
            rows += [('All keybinds', 'workspace', 'all_keys', True, None),
                     ('Bulk actions', 'workspace', 'bulk', True, None)]
            if 'sdk.management' in views:
                rows.append(('Menu appearance', 'appearance', None, True, None))
        elif self.screen == 'details':
            view = self.registry.view(self.selection)
            rows.insert(1, ('Reload', 'reload_current', None, not view['protected'], None))
            rows.append(('Export diagnostics', 'diagnostics', None, True, None))
            detail = (f"{view['name']}\n{'ENABLED' if view['enabled'] else 'DISABLED'}\n"
                      f"Author: {view['author'] or 'Unknown'}\nVersion: {view['version'] or '—'}\n"
                      f"Module: {view['folder']}\n\n{detail}\n\n"
                      f"{len(view['options'])} settings • {len(view['keybinds'])} keybinds\n\n"
                      + '\n'.join(f"{o['title']}: {o['value']}" for o in view['options'][:3]))
        if self.editing:
            selection, option = self.editing
            self.registry.view(selection)
            detail = (f"EDIT {option['title']}\nType: {option['kind']}\n"
                      f"Default: {option['default']}\n"
                      + (f"Range: {option['minimum']} to {option['maximum']}\n"
                         if option['minimum'] is not None or option['maximum'] is not None else '')
                      + '\nEdit the value below, then Apply. Reset restores the default. '
                      'Cancel leaves the saved value unchanged.')
            if option['choices']:
                detail += '\n\nChoices: ' + ', '.join(json.dumps(v) for v in option['choices'])
        elif self.screen == 'actions':
            detail += '\n\nOptional action argument: enter JSON below before selecting an action. Leave blank for no argument.'
        return title, detail, rows

    def render(self):
        if self.editing:
            try:
                self.registry.view(self.editing[0])
            except ManagementError:
                self.editing = None
        frame = super().render()
        # Keep navigation and toolbar geometry stable on short/empty pages.
        rows, navigation = frame.controls[:-4], frame.controls[-4:]
        controls = list(rows)
        controls.extend(MenuControl(-1, '', False) for _ in range(8 - len(rows)))
        controls.extend(navigation)
        toolbar = (('Apply', 'apply'), ('Reset', 'reset'), ('Cancel', 'cancel'), ('Refresh', 'refresh')) if self.editing else (
            ('Search', 'search'), (f'Filter: {self.filter_mode}', 'filter'),
            ('Clear', 'clear'), ('Refresh', 'refresh'))
        for token, (label, operation) in enumerate(toolbar, 100):
            self._commands[token] = (operation, None, True)
            controls.append(MenuControl(token, label))
        return replace(frame, controls=tuple(controls))

    def activate(self, revision, token, *, value=None, reset=False):
        self._check()
        if revision != self._revision or type(revision) is not int or type(token) is not int:
            raise ManagementError('Stale menu control; refresh the menu')
        command = self._commands.get(token)
        if command is None or not command[2]:
            raise ManagementError('Menu control is unavailable')
        operation, argument, _ = command
        if operation == 'option' and value is None and not reset:
            option = next(o for o in self.registry.view(self.selection)['options'] if o['id'] == argument)
            self.editing = (self.selection, option)
            self.status = ''
            return self.render()
        if operation == 'back' and self.screen in ('all_keys', 'bulk', 'bulk_confirm', 'bulk_results'):
            self.screen, self.page, self.selection = 'list', 0, None
            return self.render()
        if operation not in ('search', 'filter', 'clear', 'refresh', 'apply', 'reset', 'cancel', 'reload_current',
                             'workspace', 'appearance', 'global_key', 'bulk_confirm', 'bulk_apply', 'bulk_result', 'diagnostics'):
            self.editing = None
            return super().activate(revision, token, value=value, reset=reset)
        self._invalidate()
        self.status = ''
        try:
            if operation == 'search':
                if self.screen == 'all_keys':
                    if type(value) is not str or len(value) > 256 or '\0' in value:
                        raise ManagementError('Search must be at most 256 characters')
                    self.query, self.page = value.casefold(), 0
                    return self.render()
                return self.search(value or '')
            if operation == 'filter':
                self.filter_mode = self.FILTERS[(self.FILTERS.index(self.filter_mode) + 1) % len(self.FILTERS)]
                self.selection, self.screen, self.page = None, 'list', 0
            elif operation == 'clear':
                self.filter_mode = 'All'
                return self.search('')
            elif operation == 'cancel':
                self.editing = None
            elif operation == 'workspace':
                self.screen, self.page = argument, 0
            elif operation == 'appearance':
                self.selection = self.registry.select('sdk.management')
                self.screen, self.page = 'options', 0
            elif operation == 'global_key':
                self.selection, self.binding_id = argument
                self.registry.view(self.selection)
                self.screen, self.page = 'key_picker', 0
            elif operation == 'bulk_confirm':
                self.bulk_enabled = argument
                self.bulk_plan = tuple(v for v in self.registry.views() if not v['protected'] and (
                    (v['desired_enabled'] if v.get('disable_pending') else v['enabled']) != argument if type(argument) is bool else
                    v['enabled'] if argument == 'reload' else bool(v['keybinds'])))
                self.screen, self.page = 'bulk_confirm', 0
            elif operation == 'bulk_apply':
                results = []
                for view in self.bulk_plan:
                    try:
                        selection = Selection(view['id'], view['generation'])
                        current = self.registry.view(selection)
                        if current['protected']:
                            raise ManagementError('Protected mod')
                        if type(self.bulk_enabled) is bool:
                            selection=self.registry.set_enabled(selection, self.bulk_enabled)
                            if self.registry.view(selection).get('disable_pending'):
                                results.append(view['name'] + ': disabling');continue
                        elif self.bulk_enabled == 'reload':
                            self.registry.reload_current(selection)
                        else:
                            for binding in view['keybinds']:
                                selection = self.registry.set_keybind(selection, binding['id'], None,
                                    reset=self.bulk_enabled == 'reset_keys')
                        results.append(view['name'] + ': done')
                    except Exception as error:
                        results.append(view['name'] + ': ' + str(error))
                self.status = '\n'.join(results)
                self.bulk_results, self.bulk_plan = tuple(results), ()
                self.screen, self.page = 'bulk_results', 0
                self._export('last_bulk_operation.json', results)
            elif operation == 'bulk_result':
                self.status = argument
            elif operation == 'diagnostics':
                self.status = 'Saved: ' + str(self._export('selected_mod_diagnostics.json', self.registry.view(self.selection)))
            elif operation in ('apply', 'reset'):
                if self.editing is None:
                    raise ManagementError('Select a setting first')
                selection, option = self.editing
                parsed = option['default'] if operation == 'reset' else self.parse_value(option['kind'], value)
                result = self.registry.set_option(selection, option['id'], parsed, reset=operation == 'reset')
                self.status = 'Saved: ' + repr(result)[:2048]
                self.editing = None
            elif operation == 'reload_current':
                folder = self.registry.view(self.selection)['folder']
                self.registry.reload_current(self.selection)
                current = next(v for v in self.registry.views() if v['folder'] == folder)
                self.selection = self.registry.select(current['id'])
                self.status = 'Reloaded ' + current['name']
        except Exception as error:
            self.status = f'{type(error).__name__}: {str(error)[:2048]}'
        return self.render()

    @staticmethod
    def parse_value(kind, text):
        if kind == 'text':
            return text
        if not isinstance(text, str):
            raise ManagementError('Enter a value first')
        # JSON keeps bool/int/float/choice types exact; Registry enforces bounds.
        return json.loads(text, parse_constant=lambda value: (_ for _ in ()).throw(
            ValueError('Non-finite values are not supported')))


class ModsWorkspacePanel(OwnedMenuPanel):
    EXTRA_NAMES = ('EditableText', 'GetText',
                   'SetRenderScale', 'SetRenderTransformPivot')

    def __init__(self, session, **options):
        super().__init__(session, controls=16, **options)
        self.field_value = None
        self.scaled_labels = []
        self.surfaces = []
        self.appearance = None

    def label(self, x, y, width, height, scale=.62):
        label = self._label(x, y, width / scale, height / scale)
        self._call(label, 'Widget', 'SetRenderTransformPivot', Pivot={'X': 0., 'Y': 0.})
        self._call(label, 'Widget', 'SetRenderScale', Scale={'X': scale, 'Y': scale})
        self.scaled_labels.append((label, scale))
        return label

    def _build_contents(self):
        background = self._spawn('Border')
        self.background = background
        slot = self._place(background, 0, 0, 0, 0)
        self._call(slot, 'CanvasPanelSlot', 'SetAnchors',
                   InAnchors={'Minimum': {'X': 0., 'Y': 0.}, 'Maximum': {'X': 1., 'Y': 1.}})
        self._call(background, 'Border', 'SetBrushColor',
                   InBrushColor={'R': .012, 'G': .018, 'B': .028, 'A': .98})
        for x, width in ((24, 1050), (1100, 790)):
            border = self._spawn('Border')
            self.surfaces.append(border)
            self._place(border, x, 120, width, 800)
            self._call(border, 'Border', 'SetBrushColor',
                       InBrushColor={'R': .025, 'G': .045, 'B': .065, 'A': 1.})
        self.title = self.label(24, 24, 1800, 64, .9)
        self.detail = self.label(1124, 145, 740, 570)
        layouts = [(44, 145 + i * 91, 1010, 76) for i in range(8)]
        layouts += [(24 + i * 472, 970, 452, 62) for i in range(4)]
        layouts += [(1124 + (i % 2) * 374, 795 + (i // 2) * 58, 356, 48) for i in range(4)]
        for index, (x, y, width, height) in enumerate(layouts):
            button = self._spawn('Button')
            self._place(button, x, y, width, height)
            self._call(button, 'Button', 'SetBackgroundColor',
                       InBackgroundColor={'R': .07, 'G': .14, 'B': .18, 'A': 1.})
            self.buttons.append(button)
            self.labels.append(self.label(x + 14, y + 10, width - 28, height - 16))
            self._visible[index] = self._enabled[index] = True
        field_backdrop = self._spawn('Border')
        self._place(field_backdrop, 1124, 725, 730, 54)
        self._call(field_backdrop, 'Border', 'SetBrushColor',
                   InBrushColor={'R': .008, 'G': .012, 'B': .02, 'A': 1.})
        self._call(field_backdrop, 'Widget', 'SetVisibility', InVisibility=self.invisible)
        self.field = self._spawn('EditableText')
        self._place(self.field, 1136, 733, 706, 42)

    def paint_appearance(self, theme, text_scale):
        if self.appearance == (theme, text_scale):
            return
        background, surface, accent = THEMES.get(theme, THEMES['World Builder'])
        def color(rgb):
            return dict(zip(('R', 'G', 'B', 'A'), (*rgb, 1.)))
        self._render_call(self.background, 'Border', 'SetBrushColor', InBrushColor=color(background))
        for widget in self.surfaces:
            self._render_call(widget, 'Border', 'SetBrushColor', InBrushColor=color(surface))
        for widget in self.buttons:
            self._render_call(widget, 'Button', 'SetBackgroundColor', InBackgroundColor=color(accent))
        for widget, scale in self.scaled_labels:
            self._render_call(widget, 'Widget', 'SetRenderScale', Scale={'X': scale * text_scale, 'Y': scale * text_scale})
        self.appearance = (theme, text_scale)

    def set_field(self, value):
        if self.field_value != value:
            # Native UI batches accept TextBlock.SetText, not the distinct
            # EditableText function. Use the ordinary validated dispatcher.
            queue, self._paint_queue = self._paint_queue, None
            try:
                self._render_call(self.field, 'EditableText', 'SetText', InText=value)
            finally:
                self._paint_queue = queue
            self.field_value = value

    def read_field(self):
        with self._planner.prepare(self.field, self._function('EditableText', 'GetText')).invoke() as result:
            return str(result.return_value)


class ModsWorkspaceMenu(NativeManagementMenu):
    supports_typed_editors = True
    def __init__(self, session, registry, **options):
        options.setdefault('view_factory', ModsWorkspaceView)
        super().__init__(session, registry, panel_factory=ModsWorkspacePanel, **options)
        self._field_context = None

    def _open(self):
        if not getattr(self,'_reuse_prepared_frame',False):self._field_context = None
        return super()._open()

    def _paint_frame(self):
        frame = self.frame
        try:
            owner = self.view.registry.select('sdk.management')
            theme = self.view.registry.option(owner, 'theme')
            text_scale = self.view.registry.option(owner, 'text_scale')
        except ManagementError:
            theme, text_scale = 'World Builder', 1.
        self.panel.paint_appearance(theme, text_scale)
        self.panel.set_text(self.panel.title,
            f'{display_line(frame.title, 80)}   •   {frame.page + 1} / {frame.pages}')
        detail = '\n\n'.join(filter(None, (self.error, frame.status, frame.description)))
        self.panel.set_text(self.panel.detail, display_detail(detail, width=52, height=19))
        for index in range(self.panel.count):
            control = frame.controls[index] if index < len(frame.controls) else None
            self.panel.set_text(self.panel.labels[index], display_line(control.label, 64 if index < 8 else 24) if control else '')
            self.panel.set_enabled(index, bool(control and control.enabled))
            self.panel.set_visible(index, bool(control and control.label))
        self._paint_field()

    def _paint_field(self):
        editing = getattr(self.view, 'editing', None)
        action_input = isinstance(self.view, ModsWorkspaceView) and self.view.screen == 'actions'
        context = ('edit', editing[0], editing[1]['id']) if editing else (
            ('action', self.view.selection) if action_input else ('search', getattr(self.view, 'query', '')))
        if context != self._field_context:
            value = (editing[1]['value'] if editing[1]['kind'] == 'text' else
                     json.dumps(editing[1]['value'], ensure_ascii=False)) if editing else ('' if action_input else getattr(self.view, 'query', ''))
            # Force writes on context changes even if the previous cached default
            # equals this value: native typing can have changed the actual field.
            self.panel.field_value = None
            self.panel.set_field(value)
            self._field_context = context

    def _bind(self):
        if not isinstance(self.view, ModsWorkspaceView):
            return super()._bind()
        frame = self.frame
        retaining=getattr(self,'_retain_scroll_callbacks',False)
        if retaining and getattr(self,'_bound_frame',None) is not frame:
            raise ManagementError('Cannot retain callbacks across a changed frame')
        if not retaining:self._binding_tokens={}
        bindings = [];binding_tokens=[]
        bindable = self.view.bindable_tokens() if callable(getattr(self.view, 'bindable_tokens', None)) else None
        for index, control in enumerate(frame.controls):
            if not control.enabled:
                continue
            if bindable is not None and control.token not in bindable:
                continue
            if retaining and control.token in self._binding_tokens:continue
            def click(_event, control=control, frame=frame):
                if self._presentation_suspended:
                    return
                if not self._accept_input or self.frame is not frame:
                    raise ManagementError('Native menu input is revoked or stale')
                operation = self.view._commands[control.token][0]
                submission = {'value': self.panel.read_field()} if operation in ('search', 'apply') else {}
                if operation == 'action':
                    text = self.panel.read_field().strip()
                    try:
                        submission = {'value': ModsWorkspaceView.parse_value('json', text)} if text else {}
                    except ValueError as error:
                        self.error = 'Invalid action JSON: ' + str(error)
                        self._paint()
                        return
                if operation == 'clear':
                    self._field_context = None
                self.submit(frame.revision, control.token, **submission)
            bindings.append((self.panel.buttons[index], click));binding_tokens.append(control.token)
        for start in range(0,len(bindings),48):
            controls=self.panel.menu.bind_controls(bindings[start:start+48])
            self.actions.extend(controls)
            self._binding_tokens.update(zip(binding_tokens[start:start+48],controls))
        self._bound_frame=frame
        self._accept_input = True
