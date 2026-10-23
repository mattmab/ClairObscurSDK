"""Title-only management: persist intent; never enable gameplay callbacks."""
from dataclasses import replace
from .management import ManagementError
from .management_view import MenuFrame,MenuControl
from .mods_workspace_scroll import ScrollWorkspaceView

class TitleRegistryFacade:
    def __init__(self,registry):self._registry=registry;self._settings=registry._settings;self._view=None
    def _check(self):return self._registry._check()
    @property
    def _startup_progress(self):return None # World activation counts do not describe title readiness.
    def select(self,*a,**k):return self._registry.select(*a,**k)
    def installed(self):return self._registry.installed()
    def startup_order(self):return self._registry.startup_order()
    def move_startup(self,*a,**k):return self._registry.move_startup(*a,**k)
    def option(self,*a,**k):return self._registry.option(*a,**k)
    def keybind(self,*a,**k):return self._registry.keybind(*a,**k)
    def _refresh_selection(self,mod_id):
        view=self._view
        if view is not None:
            if view.selection is not None and view.selection.mod_id==mod_id:view.selection=self.select(mod_id)
            if view.editing is not None and view.editing[0].mod_id==mod_id:view.editing=(self.select(mod_id),view.editing[1])
    def view(self,selection):
        value=self._registry.view(selection)
        value['active_enabled']=value['enabled']
        value['enabled']=value.get('desired_enabled',value['enabled'])
        value['actions']=[]
        if not value['active_enabled']:value['description']+='\n\nGameplay activation is deferred until a save is loaded.'
        return value
    def views(self):return tuple(self.view(self.select(v['id'])) for v in self._registry.views())
    def set_enabled(self,selection,enabled):
        result=self._registry.stage_enabled(selection,enabled);self._refresh_selection(selection.mod_id);return result
    def set_option(self,selection,option_id,value,*,reset=False):
        result=self._registry.stage_option(selection,option_id,value,reset=reset);self._refresh_selection(selection.mod_id);return result
    def set_keybind(self,selection,*a,**k):
        result=self._registry.set_keybind(selection,*a,**k);self._refresh_selection(selection.mod_id);return result
    def key_conflicts(self):
        routes={}
        for mod in self.views():
            if mod['enabled']:
                for binding in mod['keybinds']:
                    if binding['value'] is not None:routes.setdefault(binding['value'],[]).append((mod['id'],binding['id']))
        return {key:tuple(rows) for key,rows in routes.items() if len(rows)>1}
    def saved_folder(self,folder):
        records={} if self._settings is None else self._settings.records()
        rows=[(key,record.get('enabled') is True) for key,record in records.items() if record.get('folder')==folder]
        if len(rows)>1:raise ManagementError('Saved folder identity is ambiguous')
        return rows[0] if rows else None
    def stage_saved(self,folder,enabled):
        record=self.saved_folder(folder)
        if record is None:raise ManagementError('This deferred mod has no known saved identity; configure after its first world load')
        return self._registry.stage_saved_enabled(record[0],enabled)
    def _world_only(self,*a,**k):raise ManagementError('Available after loading a save; no gameplay operation was dispatched')
    load=unload=reload=reload_current=install_staged=invoke=request_shutdown=_world_only

class TitleWorkspaceView(ScrollWorkspaceView):
    def __init__(self,registry):
        if isinstance(registry,TitleRegistryFacade):registry=registry._registry
        facade=TitleRegistryFacade(registry);super().__init__(facade);facade._view=self;self._legacy_folder=None
    def render(self):
        if self.screen=='title_legacy':
            self._check();self._invalidate();self.row_states=[];self.total_rows=2;self.scroll_start=0;folder=self._legacy_folder;record=self.registry.saved_folder(folder)
            description='Definition deferred until a save is loaded. Python has not been imported. Options and keybinds become available after an audited startup preparation or the first world load.'
            description+='\n\nSaved preference: '+('enabled' if record and record[1] else 'disabled' if record else 'not configured')
            controls=[]
            for index,(label,op,arg,enabled) in enumerate((('Enable after loading','title_stage_legacy',True,record is not None),('Disable after loading','title_stage_legacy',False,record is not None),('Back','title_back',None,True),('Previous','none',None,False),('Next','none',None,False),('Close','close',None,True))):
                controls.append(MenuControl(index,label,enabled));self._commands[index]=(op,arg,enabled)
            return MenuFrame(self._revision,folder,description,tuple(controls),0,1,self.status,False)
        frame=super().render();controls=[]
        blocked={'action','reload_current','reload','unload','install_staged','diagnostics','shutdown'}
        for c in frame.controls:
            command=self._commands.get(c.token)
            if command is not None:
                operation,arg,enabled=command
                if operation=='load':
                    self._commands[c.token]=('title_legacy',arg,enabled)
                    if c.label=='Load':c=replace(c,label='Deferred')
                elif operation in blocked or operation=='bulk_confirm' and arg=='reload':
                    self._commands[c.token]=(operation,arg,False);c=replace(c,enabled=False)
            controls.append(c)
        return replace(frame,controls=tuple(controls),description='TITLE SCREEN — preferences only. Gameplay mods activate after loading a save.\n\n'+frame.description)
    def activate(self,revision,token,**values):
        self._check()
        if type(revision) is not int or revision!=self._revision or type(token) is not int:raise ManagementError('Stale title menu control')
        command=self._commands.get(token)
        if command is None or not command[2]:raise ManagementError('Title menu control unavailable')
        op,arg,_=command
        if op in ('title_legacy','title_stage_legacy','title_back'):
            self._invalidate()
            if op=='title_legacy':self._legacy_folder=arg;self.screen='title_legacy'
            elif op=='title_back':self.screen='list'
            else:self.registry.stage_saved(self._legacy_folder,arg);self.status='Preference saved; applies after loading a save.'
            return self.render()
        frame=super().activate(revision,token,**values)
        if not frame.closed and op in ('inline_toggle','enable','quick_option','apply','reset','text_scale'):
            self.status='Preference saved; applies after loading a save.';return self.render()
        return frame
