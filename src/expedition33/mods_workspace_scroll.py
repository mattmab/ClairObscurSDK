"""Scrollable BL4-style workspace using E33-owned UMG controls.

Eight recycled native rows cover a seven-row viewport plus an overscan row.
The ScrollBox owns wheel/drag/clipping; registry generations own every action.
"""
import math
import time
import textwrap
from dataclasses import replace
from .management import ManagementError, Selection
from .management_view import MenuControl, MenuFrame
from .management_native import NativeManagementMenu, display_detail, display_line
from .mods_workspace import ModsWorkspaceView, ModsWorkspacePanel, ModsWorkspaceMenu, THEMES
from .widgets import OwnedMenuPanel

EMPTY = MenuControl(-1, '', False)
ROW_HEIGHT = 84
CONTROL_COUNT = 105
TEXT_MIN, TEXT_MAX, TEXT_DEFAULT = .75, 2.75, 1.35

def bounded_detail(text, **bounds):
    width, height = bounds.get('width', 42), bounds.get('height', 18)
    lines = [line for paragraph in text.splitlines() if paragraph.strip()
             for line in textwrap.wrap(paragraph, width=width)]
    if len(lines) > height:
        lines = lines[:height]
        lines[-1] = lines[-1][:max(1, width-1)].rstrip() + '…'
    return '\n'.join(lines)

def row_token(row):
    return row*6 if row<8 else 81+(row-8)*6

def row_height(screen):
    return 64 if screen in ('list','options') else ROW_HEIGHT


def expand_controls(controls):
    result = [EMPTY] * CONTROL_COUNT
    if len(controls) < 16:
        rows, navigation = controls[:-4], controls[-4:]
        controls = tuple(rows) + (EMPTY,) * (8-len(rows)) + tuple(navigation) + (EMPTY,) * 4
    for i, control in enumerate(controls[:8]): result[i * 6] = control
    result[48:52] = controls[8:12]
    result[52:56] = controls[12:16]
    return tuple(result)


class ScrollWorkspaceView(ModsWorkspaceView):
    def __init__(self, registry):
        super().__init__(registry)
        self.scroll_start = 0
        self.scroll_reset = 0
        self.total_rows = 0
        self.key_filter = 'All'
        self.key_mod = None
        self.conflict_key = None
        self.selected_mod = None
        self.row_states = []
        self.return_to_keys = False
        self.capture_target = None
        self.key_scroll_start = 0
        self.key_total = 0
        self.binding_start = 0

    @property
    def native_scroll_list(self):
        return self.screen == 'list' and self.total_rows <= 36

    @staticmethod
    def mod_token(index):
        cell = index * 2
        return cell if cell < 48 else 81 + cell - 48

    def bindable_tokens(self):
        if not self.native_scroll_list:
            return set(range(CONTROL_COUNT))
        return ({self.mod_token(i) + cell
                 for i in range(self.binding_start, min(self.total_rows, self.binding_start + 24))
                 for cell in (0, 1)} | set(range(48, 81)))

    def update_scroll_bindings(self, first_visible):
        end = min(self.total_rows, first_visible + 12)
        if first_visible >= self.binding_start and end <= self.binding_start + 24:
            return False
        self.binding_start = min(max(0, first_visible - 6), max(0, self.total_rows - 24))
        return True

    def chrome(self,frame):
        controls=list(frame.controls)
        for index,label,op,arg,enabled in ((76,'Mods','tab','list',self.screen!='list'),
                (77,'Keybinds','tab','all_keys',self.screen!='all_keys'),
                (78,'−','text_scale',-.1,True),(79,'+','text_scale',.1,True),
                (80,'Reset','text_scale',None,True)):
            controls[index]=MenuControl(index,label,enabled)
            self._commands[index]=(op,arg,enabled)
        if sum(c.enabled for c in controls if c.label and c.token in self.bindable_tokens())>64:
            raise ManagementError('Menu exceeds native active-control capacity')
        return self.capture_frame(replace(frame,controls=tuple(controls)))

    def capture_frame(self,frame):
        if self.capture_target is None:return frame
        selection,binding_id=self.capture_target
        try:
            mod=self.registry.view(selection)
            binding=next(b for b in mod['keybinds'] if b['id']==binding_id)
        except (ManagementError,StopIteration):
            self.capture_target=None
            self.status='Rebind cancelled: the mod or binding changed.'
            return self.render()
        controls=[replace(c,enabled=False) for c in frame.controls]
        for index,label,op in ((51,'Close','close'),(55,'Cancel capture','cancel_capture')):
            controls[index]=MenuControl(index,label)
            self._commands[index]=(op,None,True)
        for token,(op,arg,_enabled) in tuple(self._commands.items()):
            if token not in (51,55):self._commands[token]=(op,arg,False)
        prompt=f"Press a key for {mod['name']} / {binding['title']}  |  Escape unbinds  |  Cancel keeps {binding['value'] or 'Unbound'}"
        return replace(frame,status=prompt,controls=tuple(controls))

    def reset_scroll(self):
        self.scroll_start = 0
        self.key_scroll_start = 0
        self.scroll_reset += 1
        self.binding_start = 0

    def _mods(self):
        # Reuse the existing installed/search/filter policy, excluding utility rows.
        return [r for r in super()._rows()[2] if r[1] in ('select', 'load')]

    def _bindings(self):
        conflicts = self.registry.key_conflicts()
        result = []
        for mod in self.registry.views():
            for binding in mod['keybinds']:
                key = binding['value']
                conflict = bool(mod['enabled'] and key in conflicts)
                if self.key_mod and mod['id'] != self.key_mod: continue
                if self.conflict_key and (key != self.conflict_key or not conflict): continue
                if self.key_filter == 'Bound' and key is None: continue
                if self.key_filter == 'Unbound' and key is not None: continue
                if self.key_filter == 'Conflicts' and not conflict: continue
                if self.query not in f"{mod['name']} {binding['title']} {key or 'Unbound'}".casefold(): continue
                result.append((mod, binding, conflict))
        return sorted(result, key=lambda row: (row[0]['name'].casefold(), row[1]['title'].casefold()))

    def render(self):
        if self.screen in ('options','keybinds'):
            self._check();self._invalidate()
            title,description,rows=self._rows()
            self.total_rows=len(rows);self.row_states=[]
            visible=10 if self.screen=='options' else 7
            self.scroll_start=min(self.scroll_start,max(0,len(rows)-visible))
            controls=[EMPTY]*CONTROL_COUNT
            def add(index,label,op,arg=None,enabled=True,editor=None):
                controls[index]=MenuControl(index,label,enabled,editor)
                self._commands[index]=(op,arg,enabled)
            for i,(label,op,arg,enabled,editor) in enumerate(rows[self.scroll_start:self.scroll_start+(12 if self.screen=='options' else 8)]):
                index=row_token(i)
                add(index,label,op,arg,enabled,editor)
                if self.screen=='options':
                    option=next(o for o in self.registry.view(self.selection)['options'] if o['id']==arg)
                    if option['kind']=='bool':add(index+1,'ON' if option['value'] else 'OFF','quick_option',arg)
                    elif option['choices']:add(index+1,'Next','quick_option',arg)
                    else:add(index+1,'Edit','option',arg)
                    add(index+2,'Reset','reset_option',arg)
            add(48,'Back','back');add(51,'Close','close')
            if self.screen=='options':
                mod=self.registry.view(self.selection)
                add(56,'Mod keybinds','mod_keys',self.selection.mod_id)
                if not self.editing:
                    description=f"{mod['name']}\n{'ENABLED' if mod['enabled'] else 'DISABLED'}\n\nAuthor: {mod['author'] or 'Unknown'}\nVersion: {mod['version'] or 'Unknown'}\nModule: {mod['folder']}\n\n{len(mod['options'])} options\n{len(mod['keybinds'])} keybinds\n\n{mod['description']}"
                self.key_total=len(mod['keybinds'])
                self.key_scroll_start=min(self.key_scroll_start,max(0,self.key_total-10))
                for i,binding in enumerate(mod['keybinds'][self.key_scroll_start:self.key_scroll_start+12]):
                    add(64+i,f"{binding['title']}: {binding['value'] or 'Unbound'}",'global_key',(self.selection,binding['id']),not mod['protected'])
                add(60,'Enable' if not mod['enabled'] else 'Disable','inline_toggle',self.selection,not mod['protected'])
                add(61,'Reload','reload_current',enabled=not mod['protected'])
            if self.editing:
                for i,(label,op) in enumerate((('Apply','apply'),('Reset','reset'),('Cancel','cancel'),('Refresh','refresh')),52):add(i,label,op)
            else:add(55,'Refresh','refresh')
            return self.chrome(MenuFrame(self._revision,title,description,tuple(controls),0,1,self.status,False))
        if self.screen not in ('list', 'all_keys'):
            frame = super().render()
            self.total_rows = len([c for c in frame.controls[:8] if c.label])
            self.row_states = []
            return self.chrome(replace(frame, controls=expand_controls(frame.controls)))
        self._check()
        self._invalidate()
        controls = [EMPTY] * CONTROL_COUNT
        self.row_states = []
        def add(index, label, operation, argument=None, enabled=True):
            self._commands[index] = (operation, argument, enabled)
            controls[index] = MenuControl(index, label, enabled)
        views = self.registry.views()
        conflicts = self.registry.key_conflicts()
        enabled = sum(v['enabled'] for v in views)
        summary = f"{len(self.registry.installed())} installed   |   {enabled} enabled   |   {len(views)-enabled} disabled   |   {len(conflicts)} conflicting keys"
        add(51, 'Close', 'close')
        add(52, 'Search', 'search')
        add(54, 'Clear', 'clear')
        add(55, 'Refresh', 'refresh')
        add(57, 'Bulk actions', 'workspace', 'bulk')
        add(59, f'Conflicts ({len(conflicts)})', 'conflicts')
        if self.screen == 'list':
            rows = self._mods()
            title = "Matt's E33 Mods Menu"
            add(53, 'Filter: ' + self.filter_mode, 'filter')
            add(56, 'Keybind manager', 'workspace', 'all_keys')
            add(58, 'Appearance', 'appearance')
            loaded = {v['id']: v for v in views}
            if self.selected_mod not in loaded:
                self.selected_mod = next((r[2].mod_id for r in rows if r[1] == 'select'), None)
            selected = loaded.get(self.selected_mod)
            description = summary + '\n\nSelect a mod to inspect it. Use its switch to enable or disable it.'
            if selected:
                self.selection = self.registry.select(selected['id'])
                description = (f"{selected['name']}\n{selected['version'] or 'No version'}  |  {selected['author'] or 'Unknown author'}\n"
                    f"{'CORE / PROTECTED' if selected['protected'] else 'ENABLED' if selected['enabled'] else 'DISABLED'}\n\n"
                    f"{selected['description']}\n\nModule: {selected['folder']}\n"
                    f"{len(selected['options'])} settings  |  {len(selected['keybinds'])} bindings\n{selected['error'] or ''}")
                description=f"{selected['name']}\n{'ENABLED' if selected['enabled'] else 'DISABLED'}\n\n{selected['description'][:260]}"
                add(60, f"Configure ({len(selected['options'])} options, {len(selected['keybinds'])} keybinds)", 'screen', 'options', bool(selected['options'] or selected['keybinds']))
                add(61, 'Enable', 'inline_toggle', self.selection,not selected['enabled'] and not selected['protected'])
                add(62, 'Disable', 'inline_toggle', self.selection,selected['enabled'] and not selected['protected'])
                add(63, 'Reload', 'reload_current', enabled=not selected['protected'])
                add(56, 'Details / actions', 'inspect_details', self.selection)
            if not rows: description = summary + '\n\nNo matching mods.'
        else:
            rows = self._bindings()
            title = 'KEYBIND MANAGER'
            add(48, 'Back to mods', 'back')
            add(53, 'Keys: ' + self.key_filter, 'key_filter')
            add(56, 'Mod: ' + next((v['name'] for v in views if v['id']==self.key_mod), 'All'), 'key_mod')
            add(58, 'All bindings', 'all_bindings')
            description = summary + '\n\n' + (f'CONFLICT: {self.conflict_key}\n' if self.conflict_key else '')
            description += 'Click a conflicting key to see its owners. Rebind, unbind, reset or disable an owner to resolve it.'
        self.summary = summary
        self.total_rows = len(rows)
        self.scroll_start = min(self.scroll_start, max(0, len(rows)-(10 if self.screen=='list' else 7)))
        if self.native_scroll_list:
            self.scroll_start = 0
        visible_rows = rows if self.native_scroll_list else rows[self.scroll_start:self.scroll_start+(12 if self.screen=='list' else 8)]
        for local, row in enumerate(visible_rows):
            index = self.mod_token(local) if self.native_scroll_list else row_token(local)
            if self.screen == 'list':
                label, operation, argument, allowed, _ = row
                if operation == 'load':
                    add(index, label, 'load', argument)
                    add(index+1, 'Load', 'load', argument)
                    self.row_states.append((False, False, False))
                else:
                    mod = loaded[argument.mod_id]
                    collision = any(mod['enabled'] and b['value'] in conflicts for b in mod['keybinds'])
                    add(index, f"{'! ' if collision else ''}{mod['name']}   {mod['version']}", 'inspect', argument)
                    add(index+1, 'ON' if mod['enabled'] else 'OFF', 'inline_toggle', argument, not mod['protected'])
                    self.row_states.append((mod['id']==self.selected_mod, mod['enabled'], collision))
            else:
                mod, binding, collision = row
                selection = Selection(mod['id'], mod['generation'])
                target = (selection, binding['id'])
                add(index, mod['name'] + ' / ' + binding['title'], 'open_key_mod', selection)
                add(index+1, ('! ' if collision else '') + (binding['value'] or 'Unbound'), 'shared_key', binding['value'], collision)
                add(index+2, 'Rebind', 'global_key', target, not mod['protected'])
                add(index+3, 'Unbind', 'unbind_key', target, not mod['protected'])
                add(index+4, 'Core' if mod['protected'] else 'Disable mod', 'inline_toggle', selection, mod['enabled'] and not mod['protected'])
                add(index+5, 'Reset', 'reset_key', target, not mod['protected'])
                self.row_states.append((False, mod['enabled'], collision))
        return self.chrome(MenuFrame(self._revision, title, description, tuple(controls), 0, 1, self.status, False))

    def activate(self, revision, token, **values):
        self._check()
        if revision != self._revision or type(revision) is not int or type(token) is not int:
            raise ManagementError('Stale menu control; refresh the menu')
        command = self._commands.get(token)
        if not command or not command[2]: raise ManagementError('Menu control is unavailable')
        operation, argument, _ = command
        if operation=='tab':
            self.editing=None;self.capture_target=None;self.status=''
            self.screen=argument;self.reset_scroll()
            if argument=='all_keys':self.key_mod=None;self.key_filter='All';self.query='';self.conflict_key=None
            return self.render()
        if operation=='text_scale':
            owner=self.registry.select('sdk.management')
            current=self.registry.option(owner,'text_scale')
            value=TEXT_DEFAULT if argument is None else max(TEXT_MIN,min(TEXT_MAX,round(current+argument,2)))
            self.registry.set_option(owner,'text_scale',value)
            return self.render()
        if operation in ('quick_option','reset_option'):
            try:
                option=next(o for o in self.registry.view(self.selection)['options'] if o['id']==argument)
                value=not option['value'] if option['kind']=='bool' else option['choices'][(option['choices'].index(option['value'])+1)%len(option['choices'])] if option['choices'] else option['default']
                result=self.registry.set_option(self.selection,argument,value,reset=operation=='reset_option')
                self.editing=None;self.status='Saved: '+repr(result)
            except Exception as error:self.status=f'{type(error).__name__}: {error}'
            return self.render()
        if operation in ('global_key','pick_key'):
            target=argument if operation=='global_key' else (self.selection,argument)
            if self.registry.view(target[0])['protected']:raise ManagementError('Protected core mod')
            self.capture_target=target
            self.status=''
            return self.render()
        if operation=='cancel_capture':
            self.capture_target=None
            self.status='Rebind cancelled; binding unchanged.'
            return self.render()
        custom = ('inspect', 'inline_toggle', 'key_filter', 'key_mod', 'conflicts', 'all_bindings',
                  'shared_key', 'mod_keys', 'open_key_mod', 'inspect_details', 'unbind_key', 'reset_key')
        if operation not in custom:
            old_screen = self.screen
            if operation == 'global_key': self.return_to_keys = True
            if operation in ('search','clear','filter','workspace','back','appearance','global_key','load'):
                self.reset_scroll()
            if operation == 'clear':
                self.key_filter, self.key_mod, self.conflict_key = 'All', None, None
            if operation == 'search' and self.screen == 'all_keys': self.conflict_key = None
            frame = super().activate(revision, token, **values)
            if old_screen == 'key_picker' and self.return_to_keys and operation in ('key','key_reset','back'):
                self.return_to_keys = False
                self.screen, self.page = 'all_keys', 0
                self.reset_scroll()
                return self.render()
            if old_screen != self.screen: self.reset_scroll()
            return frame
        self._invalidate()
        self.status = ''
        try:
            if operation == 'inspect':
                self.registry.view(argument)
                self.selected_mod, self.selection = argument.mod_id, argument
            elif operation == 'inline_toggle':
                mod = self.registry.view(argument)
                if mod['protected']: raise ManagementError('Protected core mod')
                self.registry.set_enabled(argument, not mod['enabled'])
                if self.selection==argument:self.selection=self.registry.select(argument.mod_id)
                self.status = ('Disabled ' if mod['enabled'] else 'Enabled ') + mod['name']
            elif operation in ('unbind_key','reset_key'):
                selection, binding = argument
                if self.registry.view(selection)['protected']: raise ManagementError('Protected core mod')
                self.registry.set_keybind(selection, binding, None, reset=operation=='reset_key')
                self.status = 'Binding updated'
            elif operation == 'inspect_details': self.selection, self.screen, self.page = argument, 'details', 0
            elif operation == 'open_key_mod':
                self.registry.view(argument)
                self.selected_mod, self.selection, self.screen = argument.mod_id, argument, 'list'
                self.query, self.filter_mode = '', 'All'
                self.reset_scroll()
            else:
                self.reset_scroll()
                self.screen, self.page = 'all_keys', 0
                if operation == 'key_filter':
                    modes = ('All','Bound','Unbound','Conflicts')
                    self.key_filter = modes[(modes.index(self.key_filter)+1)%len(modes)]
                    self.conflict_key = None
                elif operation == 'key_mod':
                    mods = [None] + [v['id'] for v in self.registry.views() if v['keybinds']]
                    self.key_mod = mods[(mods.index(self.key_mod)+1)%len(mods)] if self.key_mod in mods else None
                    self.conflict_key = None
                elif operation == 'mod_keys':
                    self.key_mod, self.key_filter, self.query, self.conflict_key = argument, 'All', '', None
                elif operation == 'shared_key':
                    self.key_mod, self.key_filter, self.query, self.conflict_key = None, 'Conflicts', '', argument
                else:
                    self.key_mod, self.query, self.conflict_key = None, '', None
                    self.key_filter = 'Conflicts' if operation == 'conflicts' else 'All'
        except Exception as error: self.status = f'{type(error).__name__}: {error}'
        return self.render()


class ScrollWorkspacePanel(ModsWorkspacePanel):
    BATCH_CONSTRUCTION = True
    EXTRA_NAMES = ModsWorkspacePanel.EXTRA_NAMES + ('ScrollBox','SizeBox','PanelWidget','ContentWidget',
        'AddChild','SetContent','SetHeightOverride','SetWidthOverride','GetScrollOffset','SetScrollOffset',
        'SetAlwaysShowScrollbar','SetWheelScrollMultiplier','Slider','GetValue','SetValue','SetStepSize')

    def __init__(self, session, **options):
        OwnedMenuPanel.__init__(self, session, controls=64, **options)
        # These are retained widgets, not simultaneous native bindings. Each
        # view binds <=64 enabled buttons; inactive pools remain unbound.
        self.count=CONTROL_COUNT
        self.field_value = None
        self.scaled_labels, self.surfaces = [], []
        self.appearance = None
        self.row_slots, self.button_slots, self.label_slots = [], [], []
        self.layout_mode = None
        self.scroll_marker = None
        self.surface_slots, self.switches, self.switch_slots = [], [], []
        self.key_slots=[]
        self.slider_scale=None
        self.text_bounds={}

    def label(self,x,y,width,height,scale=.62):
        label=super().label(x,y,width,height,scale)
        self.text_bounds[label.index]=(self.last_slot,width,height)
        return label

    def direct(self, obj, owner, name, **args):
        queue, self._paint_queue = self._paint_queue, None
        try: return self._render_call(obj, owner, name, **args)
        finally: self._paint_queue = queue

    def _button(self, x, y, width, height):
        button = self._spawn('Button')
        self.button_slots.append(self._place(button,x,y,width,height))
        self.buttons.append(button)
        self.labels.append(self.label(x+12,y+10,width-24,height-12,.53))
        # _place is intercepted only while creating labels to capture their slots.
        self.label_slots.append(self.last_slot)
        index=len(self.buttons)-1
        self._visible[index]=self._enabled[index]=True

    def _place(self,*args,**kw):
        self.last_slot=super()._place(*args,**kw)
        return self.last_slot

    def _build_contents(self):
        self.background=self._spawn('Border')
        slot=self._place(self.background,0,0,0,0)
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':0.,'Y':0.},'Maximum':{'X':1.,'Y':1.}})
        for x,w in ((32,596),(650,1238),(1340,548)):
            border=self._spawn('Border');self.surfaces.append(border);self.surface_slots.append(self._place(border,x,218,w,650))
        self.title=self.label(32,13,380,42,.58)
        self.title_slot=self.last_slot
        self.subtitle=self.label(34,55,380,30,.30)
        self.scale_label=self.label(1346,24,150,30,.34)
        self.panel_titles=[];self.panel_title_slots=[]
        for x,w in ((32,596),(650,1238),(1340,548)):
            self.panel_titles.append(self.label(x+20,196,w-40,40,.34));self.panel_title_slots.append(self.last_slot)
        self.summary=self.label(32,1040,1856,30,.30)
        self.readiness_label=self.label(674,978,980,28,.30)
        self.readiness_track=self._spawn('Border');self._place(self.readiness_track,674,1014,980,10)
        self.readiness_fill=self._spawn('Border');self.readiness_slot=self._place(self.readiness_fill,674,1014,0,10)
        self._call(self.readiness_track,'Border','SetBrushColor',InBrushColor={'R':.04,'G':.06,'B':.09,'A':1.})
        self._call(self.readiness_fill,'Border','SetBrushColor',InBrushColor={'R':.18,'G':.75,'B':.55,'A':1.})
        for widget in (self.readiness_label,self.readiness_track,self.readiness_fill):
            self._call(widget,'Widget','SetVisibility',InVisibility=self.invisible)
        self.detail=self.label(674,248,1180,300,.48)
        self.detail_slot=self.last_slot
        self.preview=self.label(674,600,1180,280,.44)
        self.preview_slot=self.last_slot
        self.key_preview=self.label(1278,610,580,280,.44)
        self.key_preview_slot=self.last_slot
        self.metadata=[];self.metadata_labels=[]
        for i in range(4):
            x=674+i*300
            border=self._spawn('Border');self._place(border,x,402,288,68)
            self._call(border,'Border','SetBrushColor',InBrushColor={'R':.07,'G':.091,'B':.105,'A':1.})
            self.metadata.append(border)
            self.metadata_labels.append(self.label(x+12,409,264,54,.34))
        self.scroll=self._spawn('ScrollBox')
        self.scroll_slot=self._place(self.scroll,32,230,1060,588)
        self.root_canvas=self.canvas
        self.content_size=self._spawn('SizeBox')
        self._construction_call(self.scroll,self._function('PanelWidget','AddChild'),Content=self.content_size)
        self.content_canvas=self._spawn('CanvasPanel')
        self._construction_call(self.content_size,self._function('ContentWidget','SetContent'),Content=self.content_canvas)
        self.canvas=self.content_canvas
        for row in range(8):
            row_canvas=self._spawn('CanvasPanel')
            self.row_slots.append(self._place(row_canvas,0,row*ROW_HEIGHT,1840,ROW_HEIGHT))
            self.canvas=row_canvas
            for cell in range(6):self._button(cell*150,0,140,72)
            knob=self._spawn('Border');self.switches.append(knob)
            self.switch_slots.append(self._place(knob,976,25,22,24))
            self._call(knob,'Border','SetBrushColor',InBrushColor={'R':.9,'G':.94,'B':.95,'A':1.})
            self._call(knob,'Widget','SetVisibility',InVisibility=self.invisible)
            self.canvas=self.content_canvas
        self.canvas=self.root_canvas
        for index in range(48,64):self._button(32+(index%4)*460,900+(index//4-12)*70,440,54)
        # Independent keybind ScrollBox owns its own wheel input and offset.
        self.key_scroll=self._spawn('ScrollBox')
        self.key_scroll_slot=self._place(self.key_scroll,1362,246,504,672)
        self.key_size=self._spawn('SizeBox')
        self._construction_call(self.key_scroll,self._function('PanelWidget','AddChild'),Content=self.key_size)
        self.key_canvas=self._spawn('CanvasPanel')
        self._construction_call(self.key_size,self._function('ContentWidget','SetContent'),Content=self.key_canvas)
        self.canvas=self.key_canvas
        for i in range(12):
            self._button(0,i*64,494,58)
            self.key_slots.append((self.button_slots[-1],self.label_slots[-1]))
        self.canvas=self.root_canvas
        for i in range(5):self._button(438+i*140,25,126,46)
        # More mod/option rows fit the BL4 64-pixel cadence. Global bindings
        # retain their eight wider action rows and leave this pool unbound.
        self.canvas=self.content_canvas
        for row in range(8,12):
            row_canvas=self._spawn('CanvasPanel')
            self.row_slots.append(self._place(row_canvas,0,row*64,1840,64))
            self.canvas=row_canvas
            for cell in range(6):self._button(cell*150,0,140,58)
            knob=self._spawn('Border');self.switches.append(knob)
            self.switch_slots.append(self._place(knob,490,20,18,20))
            self._call(knob,'Border','SetBrushColor',InBrushColor={'R':.9,'G':.94,'B':.95,'A':1.})
            self._call(knob,'Widget','SetVisibility',InVisibility=self.invisible)
            self.canvas=self.content_canvas
        self.canvas=self.root_canvas
        self.slider=self._spawn('Slider');self._place(self.slider,1346,58,502,22)
        field_bg=self._spawn('Border');self._place(field_bg,32,116,660,48)
        self._call(field_bg,'Border','SetBrushColor',InBrushColor={'R':.008,'G':.012,'B':.02,'A':1.})
        self._call(field_bg,'Widget','SetVisibility',InVisibility=self.invisible)
        self.field=self._spawn('EditableText');self._place(self.field,44,122,636,38)
        # ScrollBox/SizeBox setters are outside the native paint-batch whitelist.
        self._flush_layout()
        self._call(self.slider,'Slider','SetValue',InValue=(TEXT_DEFAULT-TEXT_MIN)/(TEXT_MAX-TEXT_MIN))
        self._call(self.slider,'Slider','SetStepSize',InValue=.01)
        self._call(self.key_scroll,'ScrollBox','SetAlwaysShowScrollbar',NewAlwaysShowScrollbar=True)
        self._call(self.key_size,'SizeBox','SetWidthOverride',InWidthOverride=494.)
        self._call(self.key_size,'SizeBox','SetHeightOverride',InHeightOverride=672.)
        self._call(self.scroll,'ScrollBox','SetAlwaysShowScrollbar',NewAlwaysShowScrollbar=True)
        self._call(self.scroll,'ScrollBox','SetWheelScrollMultiplier',NewWheelScrollMultiplier=1.)
        self._call(self.content_size,'SizeBox','SetWidthOverride',InWidthOverride=1840.)
        self._call(self.content_size,'SizeBox','SetHeightOverride',InHeightOverride=672.)

    def position(self,slot,x,y,w,h):
        for label,base in self.scaled_labels:
            bounds=self.text_bounds.get(label.index)
            if bounds is not None and bounds[0] is slot:
                self.text_bounds[label.index]=(slot,w*base,h*base)
                break
        self._render_call(slot,'CanvasPanelSlot','SetPosition',InPosition={'X':float(x),'Y':float(y)})
        self._render_call(slot,'CanvasPanelSlot','SetSize',InSize={'X':float(w),'Y':float(h)})

    def layout(self, view):
        mode='maps' if getattr(view,'native_scroll_list',False) and view.screen != 'list' else 'keys' if view.screen=='all_keys' else 'mods' if view.screen=='list' else 'options' if view.screen=='options' else 'editor'
        fixed_mods = mode == 'mods' and view.native_scroll_list
        layout_key = (mode, fixed_mods)
        if self.layout_mode != layout_key:
            columns=((32,438),(492,826),(1340,548)) if mode=='options' else ((32,596),(650,1238),(1340,548))
            if mode=='keys':columns=((32,1856),(650,1238),(1340,548))
            for i,(x,w) in enumerate(columns):
                self.position(self.surface_slots[i],x,182,w,760)
                self.position(self.panel_title_slots[i],x+20,196,(w-40)/.34,40/.34)
                show=(i<3 if mode=='options' else i==0 if mode=='keys' else i<2)
                self.direct(self.surfaces[i],'Widget','SetVisibility',InVisibility=self.invisible if show else self.collapsed)
                self.direct(self.panel_titles[i],'Widget','SetVisibility',InVisibility=self.invisible if show else self.collapsed)
            x,width,height=(514,782,672) if mode=='options' else (54,1812,588) if mode=='keys' else (52,556,672)
            self.position(self.scroll_slot,x,250,width,height)
            self.direct(self.content_size,'SizeBox','SetWidthOverride',InWidthOverride=float(width-10))
            self.direct(self.key_scroll,'Widget','SetVisibility',InVisibility=self.visible if mode=='options' else self.collapsed)
            widths=(600,210,170,170,230,160) if mode=='keys' else (456,90,1,1,1,1) if mode=='mods' else (570,100,100,1,1,1) if mode=='options' else (546,1,1,1,1,1)
            for row in range(12):
                x=0
                for cell,w in enumerate(widths):
                    i=row_token(row)+cell;h=58 if mode in ('mods','options') else 72
                    self.position(self.button_slots[i],x,2,max(1,w-8),h)
                    self.position(self.label_slots[i],x+10,12,max(1,w-26)/.53,(h-12)/.53)
                    if mode=='maps':
                        self.position(self.button_slots[i],0,cell*ROW_HEIGHT+2,538,72)
                        self.position(self.label_slots[i],10,cell*ROW_HEIGHT+12,520/.53,60/.53)
                    if mode=='mods' and cell==1:self.position(self.button_slots[i],x,16,w-8,32)
                    if fixed_mods:
                        cx, cw = (0, 456) if cell % 2 == 0 else (456, 90)
                        cy = (cell // 2) * 64
                        self.position(self.button_slots[i],cx,cy+2,cw-8,58)
                        self.position(self.label_slots[i],cx+10,cy+12,(cw-26)/.53,46/.53)
                    x+=w
            globals={48:(32,970,190,48),49:(238,970,140,48),50:(394,970,140,48),51:(1708,972,176,52),
                52:(704,116,112,48),53:(828,116,190,48),54:(1030,116,142,48),55:(1200,116,190,48),
                56:(32,890,190,46),57:(746,25,188,46),58:(948,25,160,46),59:(1122,25,180,46),
                60:(1148,484,650,48),61:(674,484,138,48),62:(824,484,138,48),63:(974,484,138,48),
                76:(438,25,126,46),77:(578,25,154,46),78:(1488,27,38,28),79:(1532,27,38,28),80:(1580,27,82,28)}
            if mode=='options':globals.update({60:(54,822,178,46),61:(244,822,178,46),56:(54,880,368,46)})
            if mode=='mods':globals[56]=(674,548,300,42)
            for i,(x,y,w,h) in globals.items():
                self.position(self.button_slots[i],x,y,w,h)
                self.position(self.label_slots[i],x+10,y+7,(w-20)/.53,(h-8)/.53)
            dx,dy,dw,dh=(54,248,394,540) if mode=='options' else (674,250,1180,142) if mode=='mods' else (674,250,1180,600)
            self.position(self.detail_slot,dx,dy,dw/.48,dh/.48)
            self.position(self.preview_slot,674,610,580/.44,280/.44)
            self.direct(self.detail,'Widget','SetVisibility',InVisibility=self.collapsed if mode=='keys' else self.invisible)
            self.direct(self.preview,'Widget','SetVisibility',InVisibility=self.invisible if mode=='mods' else self.collapsed)
            self.direct(self.key_preview,'Widget','SetVisibility',InVisibility=self.invisible if mode=='mods' else self.collapsed)
            for widget in (*self.metadata,*self.metadata_labels):self.direct(widget,'Widget','SetVisibility',InVisibility=self.invisible if mode=='mods' else self.collapsed)
            self.layout_mode=layout_key
        total=getattr(view,'total_rows',8);rh=row_height(view.screen)
        self.direct(self.content_size,'SizeBox','SetHeightOverride',InHeightOverride=float(max(588 if mode=='keys' else 672,total*rh)))
        self.direct(self.key_size,'SizeBox','SetHeightOverride',InHeightOverride=float(max(672,view.key_total*64)))
        marker=(view.screen,view.scroll_reset,getattr(view,'page',0))
        if marker!=self.scroll_marker:
            self.direct(self.scroll,'ScrollBox','SetScrollOffset',NewScrollOffset=float(view.scroll_start*rh))
            self.direct(self.key_scroll,'ScrollBox','SetScrollOffset',NewScrollOffset=float(view.key_scroll_start*64))
            self.scroll_marker=marker
        start=view.scroll_start if view.screen in ('list','all_keys','options','keybinds') else 0
        for i,slot in enumerate(self.row_slots):
            self.position(slot,0,i*6*rh if mode=='maps' else i*3*rh if fixed_mods else (start+i)*rh,1840,6*rh if mode=='maps' else 3*rh if fixed_mods else rh)
        for i,(button,label) in enumerate(self.key_slots):
            y=(view.key_scroll_start+i)*64
            self.position(button,0,y,494,58);self.position(label,10,y+10,474/.53,48/.53)
        for i,knob in enumerate(self.switches):
            states=getattr(view,'row_states',[]);token=row_token(i)
            show=mode=='mods' and not fixed_mods and i<len(states) and view._commands.get(token+1,('',))[0]=='inline_toggle'
            self._render_call(knob,'Widget','SetVisibility',InVisibility=self.invisible if show else self.collapsed)
            if show:self.position(self.switch_slots[i],514 if states[i][1] else 460,22,18,20)
        self.direct(self.slider,'Widget','SetIsEnabled',bInIsEnabled=view.capture_target is None)

    def key_scroll_offset(self):
        with self._planner.prepare(self.key_scroll,self._function('ScrollBox','GetScrollOffset')).invoke() as result:
            return float(result.return_value)

    def slider_value(self):
        with self._planner.prepare(self.slider,self._function('Slider','GetValue')).invoke() as result:
            return float(result.return_value)

    def restore_child_focus(self):
        # Sliders and scrollbars are Slate input owners, not registered buttons.
        # Return only our own child's focus to the menu anchor before native
        # teardown; never steal focus from an unrelated game widget.
        if self.state!='open' or self.uncertain:return
        for child in (self.slider,self.scroll,self.key_scroll,self.field):
            with self._planner.prepare(child,self._function('Widget','HasKeyboardFocus')).invoke() as result:
                focused=bool(result.return_value)
            if focused:
                self.direct(self.buttons[0],'Widget','SetUserFocus',PlayerController=self.player)
                return

    def paint_appearance(self,theme,text_scale):
        super().paint_appearance(theme,text_scale/TEXT_DEFAULT)
        if self.slider_scale!=text_scale:
            self.direct(self.slider,'Slider','SetValue',InValue=(text_scale-TEXT_MIN)/(TEXT_MAX-TEXT_MIN))
            self.slider_scale=text_scale
        # The game's common text style is 36px, whereas BL4's design uses
        # 48px as its base. Compensate once and keep the measured slot inside
        # its actual layout bounds, including when the user moves the slider.
        for label,base in self.scaled_labels:
            slot,width,height=self.text_bounds[label.index]
            scale=min(base*(48/36)*text_scale, max(.25,height/56))
            self._render_call(label,'Widget','SetRenderScale',Scale={'X':scale,'Y':scale})
            self._render_call(slot,'CanvasPanelSlot','SetSize',InSize={'X':width/scale,'Y':height/scale})
        self.set_text(self.scale_label,f'TEXT {text_scale:.2f}x')

    def scroll_offset(self):
        with self._planner.prepare(self.scroll,self._function('ScrollBox','GetScrollOffset')).invoke() as result:
            return float(result.return_value)

    def set_text(self,label,text):
        if label in (self.readiness_label,self.summary,self.preview,self.key_preview,self.subtitle,self.scale_label,*self.panel_titles,*self.metadata_labels):
            key=('chrome',label.index)
            if self._text.get(key) != text:
                self._render_call(label,'TextBlock','SetText',InText=text)
                self._text[key]=text
            return
        return super().set_text(label,text)


class ScrollWorkspaceMenu(ModsWorkspaceMenu):
    def __init__(self,session,registry,**options):
        options.setdefault('view_factory',ScrollWorkspaceView)
        NativeManagementMenu.__init__(self,session,registry,panel_factory=ScrollWorkspacePanel,**options)
        self._field_context=None
        self._scroll_poll=0.
        self._capture_owner=None
        self._capturing_target=None

    def _cancel_key_capture(self):
        if self._capture_owner is not None:
            self._capture_owner.cancel_capture(self)
        self._capture_owner=None
        self._capturing_target=None

    def _revoke(self):
        self._accept_input=False
        while self.actions:
            group=self.actions[:48]
            if not self.panel.menu.remove_controls(group):
                raise RuntimeError('Control removal deferred; close this native menu')
            del self.actions[:len(group)]

    def _sync_key_capture(self):
        target=getattr(self.view,'capture_target',None)
        if target==self._capturing_target:return
        self._cancel_key_capture()
        if target is None:return
        service=getattr(self.panel.scope._session,'_key_binding_owner',None)
        if service is None:raise ManagementError('Keyboard listener is not ready')
        service.begin_capture(self,lambda key:self._finish_key_capture(target,key))
        self._capture_owner,self._capturing_target=service,target

    def _finish_key_capture(self,target,key):
        self._capture_owner,self._capturing_target=None,None
        if self.panel.state!='open' or getattr(self.view,'capture_target',None)!=target:return
        self.view.capture_target=None
        try:
            selection,binding_id=target
            mod=self.view.registry.view(selection)
            if mod['protected']:raise ManagementError('Protected core mod')
            updated=self.view.registry.set_keybind(selection,binding_id,None if key=='Escape' else key)
            if self.view.selection == selection:self.view.selection=updated
            conflict=self.view.registry.key_conflicts().get(key,()) if key!='Escape' else ()
            self.view.status=('Unbound ' if key=='Escape' else 'Bound '+key+' to ')+mod['name']+' / '+binding_id
            if conflict:
                names={v['id']:v['name'] for v in self.view.registry.views()}
                self.view.status+=' — Conflict: '+', '.join(names[m]+' / '+b for m,b in conflict)
        except Exception as error:self.view.status=f'Rebind failed: {error}'
        self.refresh()

    def _bind(self):
        super()._bind()
        self._sync_key_capture()

    def hide(self):
        self._cancel_key_capture()
        if hasattr(self.view,'capture_target'):self.view.capture_target=None
        if hasattr(self.panel,'restore_child_focus'):self.panel.restore_child_focus()
        return super().hide()

    def _close(self):
        self._cancel_key_capture()
        if hasattr(self.panel,'restore_child_focus'):self.panel.restore_child_focus()
        return super()._close()

    def _paint_frame(self):
        if len(self.frame.controls)!=CONTROL_COUNT:self.frame=replace(self.frame,controls=expand_controls(self.frame.controls))
        self.panel.layout(self.view)
        try:
            owner=self.view.registry.select('sdk.management')
            theme=self.view.registry.option(owner,'theme')
            scale=self.view.registry.option(owner,'text_scale')
        except ManagementError:theme,scale='World Builder',1.
        self.panel.paint_appearance(theme,scale)
        self.panel.set_text(self.panel.title,"MATT'S E33 MODS")
        self.panel.set_text(self.panel.subtitle,{'list':'MOD WORKSPACE','options':'MOD CONFIGURATION','all_keys':'GLOBAL KEYBINDS'}.get(self.view.screen,self.frame.title)[:38])
        headings=('MOD SUMMARY','OPTIONS','KEYBINDS') if self.view.screen=='options' else ('ALL SDK KEYBINDS','','') if self.view.screen=='all_keys' else ('INSTALLED SDK MODS','MOD WORKSPACE','') if self.view.screen=='list' else ('MOD CONTROLS','DETAILS','')
        for widget,title in zip(self.panel.panel_titles,headings):self.panel.set_text(widget,title)
        summary=getattr(self.view,'summary','') if self.view.screen in ('list','all_keys') else self.frame.status
        if self.view.screen=='all_keys':
            summary+='   |   '+(self.view.conflict_key or self.view.key_filter)+'   |   '+str(self.view.total_rows)+' bindings'
            if self.view.total_rows==0:summary+='   |   No matching bindings'
        if self.frame.status:summary=self.frame.status
        self.panel.set_text(self.panel.summary,summary)
        progress = getattr(self.view.registry, '_startup_progress', None)
        if hasattr(self.panel, 'readiness_label'):
            show = self.view.screen == 'list' and progress is not None
            for widget in (self.panel.readiness_label,self.panel.readiness_track,self.panel.readiness_fill):
                self.panel.direct(widget,'Widget','SetVisibility',InVisibility=self.panel.invisible if show else self.panel.collapsed)
            if show:
                completed, total = progress['completed'], progress['total']
                fraction = min(1., completed / max(1,total)) if not progress['finished'] else 1.
                state = 'Complete' if progress['finished'] else 'Loading'
                if progress['failed']: state += f" ({progress['failed']} failed)"
                self.panel.set_text(self.panel.readiness_label,f'SDK Mods Readiness: {completed}/{total}  |  {state}')
                self.panel.position(self.panel.readiness_slot,674,1014,980*fraction,10)
        # Long descriptions stop above inspector buttons; full detail is available
        # in the Details / actions screen and diagnostic export.
        ratio=max(1.,scale/TEXT_DEFAULT)
        dw,dh=(394,540) if self.view.screen=='options' else (1180,142) if self.view.screen=='list' else (1180,600)
        font=36*min(.48*(48/36)*scale,dh/56)
        width=max(8,int(dw/(font*.65)));height=max(1,int(dh/(font*1.3)))
        self.panel.set_text(self.panel.detail,bounded_detail('\n\n'.join(filter(None,(self.error,self.frame.status,self.frame.description))),width=width,height=height))
        if self.view.screen=='list' and hasattr(self.panel,'preview'):
            mod=next((v for v in self.view.registry.views() if v['id']==self.view.selected_mod),None)
            options=[];keys=[]
            if mod:
                options=['OPTIONS  '+str(len(mod['options']))]+([f"{o['title']}: {o['value']}" for o in mod['options'][:4]] or ['No configurable options'])
                keys=['KEYBINDS  '+str(len(mod['keybinds']))]+([f"{b['title']}: {b['value'] or 'Unbound'}" for b in mod['keybinds'][:4]] or ['No exposed keybinds'])
                values=(('AUTHOR',mod['author'] or 'Unknown'),('VERSION',mod['version'] or 'Unknown'),('TYPE','Core SDK mod' if mod['protected'] else 'SDK mod'),('MODULE',mod['folder']))
                for widget,(title,value) in zip(self.panel.metadata_labels,values):self.panel.set_text(widget,title+'\n'+display_line(value,max(10,int(25/ratio))))
            font=36*.44*(48/36)*scale
            pw=max(8,int(580/(font*.65)));ph=max(1,int(280/(font*1.6)))
            self.panel.set_text(self.panel.preview,bounded_detail('\n\n'.join(options),width=pw,height=ph))
            self.panel.set_text(self.panel.key_preview,bounded_detail('\n\n'.join(keys),width=pw,height=ph))
        for i,control in enumerate(self.frame.controls):
            label=control.label
            if self.view.screen=='list' and not self.view.native_scroll_list and (i<48 or i>=81) and (i if i<48 else i-81)%6==1 and label in ('ON','OFF'):label=''
            bounds=getattr(self.panel,'text_bounds',{}).get(getattr(self.panel.labels[i],'index',None))
            if bounds:
                _,w,h=bounds
                font=36*min(.53*(48/36)*scale,max(.25,h/56))
                limit=max(4,int(w/(font*.50)))
            else:limit=38
            self.panel.set_text(self.panel.labels[i],display_line(label,limit))
            self.panel.set_enabled(i,bool(control.enabled))
            self.panel.set_visible(i,bool(control.label))
            accent=THEMES.get(self.panel.appearance[0],THEMES['World Builder'])[2]
            self.panel._render_call(self.panel.buttons[i],'Button','SetBackgroundColor',InBackgroundColor=dict(zip(('R','G','B','A'),(*accent,1.))))
        for row,(selected,enabled,conflict) in enumerate(getattr(self.view,'row_states',[])):
            token = self.view.mod_token(row) if self.view.screen == 'list' and self.view.native_scroll_list else row_token(row)
            accent=(.30,.12,.04) if conflict else (.06,.26,.32) if selected else THEMES.get(self.panel.appearance[0],THEMES['World Builder'])[2]
            self.panel._render_call(self.panel.buttons[token],'Button','SetBackgroundColor',InBackgroundColor=dict(zip(('R','G','B','A'),(*accent,1.))))
            if self.view.screen=='list':
                color=(.035,.42,.20) if enabled else (.14,.16,.18)
                self.panel._render_call(self.panel.buttons[token+1],'Button','SetBackgroundColor',InBackgroundColor=dict(zip(('R','G','B','A'),(*color,1.))))
        self._paint_field()

    def poll_scroll(self):
        if self.panel.state!='open' or self.failure or self._presentation_suspended:
            self._cancel_key_capture()
            return
        if not isinstance(self.view,ScrollWorkspaceView):return
        now=time.monotonic()
        if now<self._scroll_poll:return
        self._scroll_poll=now+.1
        changed=False
        if self.view.capture_target is None:
            value=round(TEXT_MIN+self.panel.slider_value()*(TEXT_MAX-TEXT_MIN),2)
            if abs(value-self.panel.slider_scale)>.015:
                owner=self.view.registry.select('sdk.management')
                self.view.registry.set_option(owner,'text_scale',max(TEXT_MIN,min(TEXT_MAX,value)))
                changed=True
        # All map widgets/labels occupy permanent positions. Native Slate owns
        # scrolling; only the bounded handler window changes, without repaint,
        # relayout, view.render(), scroll reset, or text replacement.
        if getattr(self.view, 'native_scroll_list', False):
            first=max(0,min(int(self.panel.scroll_offset()//row_height(self.view.screen)),max(0,self.view.total_rows-1)))
            rebind=self.view.update_scroll_bindings(first)
            if changed:
                self.refresh()
            elif rebind:
                self._revoke()
                self._bind()
            return
        if self.view.screen not in ('list','all_keys','options','keybinds'):
            if changed:self.refresh()
            return
        visible=10 if self.view.screen in ('list','options') else 7
        start=min(max(0,int(self.panel.scroll_offset()//row_height(self.view.screen))),max(0,self.view.total_rows-visible))
        if start!=self.view.scroll_start:self.view.scroll_start=start;changed=True
        if self.view.screen=='options':
            key_start=min(max(0,int(self.panel.key_scroll_offset()//64)),max(0,self.view.key_total-10))
            if key_start!=self.view.key_scroll_start:self.view.key_scroll_start=key_start;changed=True
        if changed:self.refresh()
