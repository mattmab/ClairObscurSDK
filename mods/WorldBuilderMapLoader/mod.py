"""WorldBuilder Map Loader: independent runtime maps during normal gameplay."""
import time,logging
LOG=logging.getLogger("expedition33.worldbuilder_map_loader")
from expedition33.management import ModDefinition,Action,Keybind
from expedition33.management_native import display_detail,display_line
from expedition33.paths import settings_dir
from .state import Assignments,Visits
from expedition33.map_runtime import MapRuntime,context
from .prepared_maps import PreparedMapStore
from .context_observer import ContextObserver
from expedition33.admission_monitor import ReadOnlyAdmissionMonitor
from expedition33._reader import ReadBatch
from expedition33._reader import active_reader
from contextlib import contextmanager

@contextmanager
def reads(pid):
    if active_reader() is not None:yield active_reader()
    else:
        with ReadBatch(pid,share=True) as reader:yield reader

class Mod:
    def __init__(self):
        self.session=None;self.panel=None;self.rows=[];self.offset=0;self.current=None
        self.next_poll=0.;self.message='Choose one saved WorldBuilder map for each vanilla world.'
        self.visits=Visits();self.assignments=None;self.runtime=None
        self.timings={};self._visit_observed_at=None
        self._context_monitor=None
        self._world_retiring=False;self._retirement_result=None
        self._disable_preparing=False
    def management(self):
        return ModDefinition('e33.worldbuilder-map-loader','WorldBuilder Map Loader',version='0.2.2',
            description='Load finished WorldBuilder maps during exploration. F2: choose one map per vanilla world. No editor required.',
            actions=(Action('open','Choose map for current world',self.open_menu),Action('status','Map loader status',self.status),Action('unload','Unload placed map',self.unload)),
            keybinds=(Keybind('open','Choose WorldBuilder map','F2',self.open_menu),))
    def prepare_startup(self,context):
        # Files/config only. The host does not supply a Session or world API.
        started=time.perf_counter()
        root=settings_dir()
        current=root/'WorldBuilderMapLoader'/'assignments.json'
        legacy=root/'E33MapOverlays'/'assignments.json'
        # Read legacy choices without migration writes; normal enable preserves
        # the existing migration and re-reads settings changed after preparation.
        assignments=Assignments(current if current.exists() else legacy)
        self._startup_store=PreparedMapStore(root/'E33WorldBuilder'/'maps')
        self._startup_store.prepare(assignments.values.values())
        self._mark('startup_prepare',started)
    def enable(self,session):
        self._world_retiring=False;self._retirement_result=None
        self._disable_preparing=False
        started=time.perf_counter()
        self.session=session
        self._startup_map_loaded=False
        self.visits=Visits();self.current=None;self.next_poll=0.
        self.message='Waiting for a stable exploration pawn.'
        self.check_legacy()
        self.assignments=Assignments(settings_dir()/'WorldBuilderMapLoader'/'assignments.json',legacy=settings_dir()/'E33MapOverlays'/'assignments.json')
        root=settings_dir()/'E33WorldBuilder'/'maps'
        prepared=getattr(self,'_startup_store',None)
        self.store=prepared if prepared is not None and prepared.root==root else PreparedMapStore(root)
        self.runtime=MapRuntime(session)
        prepared_context=getattr(self,'_loading_context',None)
        if prepared_context is not None and not prepared_context.released:
            self._context_monitor=prepared_context.take()
            observation=self._context_monitor.snapshot()
            if observation is not None and observation.admission is not None:
                token=session.mods._loader.world_lifecycle.current_token
                value=observation.admission
                if token is not None and value.visit==token[0][1:]:self.current=value.copy()
        session.console.expose('worldbuilder_map_loader',self)
        session.actions.register('worldbuilder_map_loader.status',self.status,mutates=False)
        session.actions.register('worldbuilder_map_loader.open',self.open_menu)
        session.actions.register('worldbuilder_map_loader.choose',self.choose,schema={'type':'object','properties':{'map_id':{'type':'string'}},'required':['map_id'],'additionalProperties':False})
        session.actions.register('worldbuilder_map_loader.load',self.load_now)
        session.actions.register('worldbuilder_map_loader.unload',self.unload)
        session.actions.register('worldbuilder_map_loader.clear',self.clear)
        self._mark('enable',started)
    def prepare_loading_ui(self,session):
        from .loading_context import LoadingContext
        return LoadingContext(self,session)
    def _mark(self,stage,started):
        elapsed=(time.perf_counter()-started)*1000
        row=self.timings.setdefault(stage,dict(calls=0,total_ms=0.,max_ms=0.))
        row['calls']+=1;row['total_ms']+=elapsed;row['max_ms']=max(row['max_ms'],elapsed)
        return elapsed
    def timing_status(self):
        # Explicitly contains no selected map, assignment, world, path or content.
        return dict(preparation=dict(getattr(getattr(self,'_startup_store',None),'stats',{})),stages={k:dict(v) for k,v in self.timings.items()},runtime={k:dict(v) for k,v in getattr(self.runtime,'profile',{}).items()})
    def check_legacy(self):
        # Refuse to overlap even with an unmodified old package. Repeat before
        # every load in case an archive was installed during this session.
        root=settings_dir().parent
        if (root.parent/'SDK_Mods'/'E33MapOverlays.sdkmod').exists() or (root/'mods'/'E33MapOverlays'/'mod.py').exists():
            raise RuntimeError('Old Map Overlays is installed. Move its package/cache to the local rollback folder before using WorldBuilder Map Loader.')
    def startup_pending(self):
        if self.session is None:return False
        return self.current is None or (bool(self.assignments.values.get(self.current['world'])) and not self.visits.attempted)
    def startup_ready(self):
        if self.session is None or not self.current or not self.current.get('ready'):return False
        return not self.assignments.values.get(self.current['world']) or self._startup_map_loaded
    def status(self,_=None):
        return dict(current=self.current,selected=self.assignments.values.get(self.current['world']) if self.current else None,
                    assignments=dict(self.assignments.values),message=self.message,objects=len(self.runtime.objects) if self.runtime else 0)
    def refresh(self):
        self.current=context(self.session)
        if not self.current:raise RuntimeError('Load a vanilla exploration map first')
        self.rows=[r for r in self.store.list() if r['world']==self.current['world']]
        self.offset=min(self.offset,max(0,((len(self.rows)-1)//6)*6))
    def choose(self,map_id):
        expected=self.current
        self.refresh()
        if expected and expected['visit']!=self.current['visit']:raise RuntimeError('Map changed; choose again')
        if map_id not in {r['id'] for r in self.rows}:raise ValueError('Choose a save belonging to this vanilla map')
        self.assignments.select(self.current['world'],map_id)
        self.message=('Assigned for the next map visit.' if self.visits.attempted else 'Assigned. Close this menu to load, or use Load now.')
        self.paint();return self.status()
    def clear(self):
        expected=self.current
        self.refresh()
        if expected and expected['visit']!=self.current['visit']:raise RuntimeError('Map changed; choose again')
        self.assignments.select(self.current['world'],None)
        self.message='Automatic loading disabled for this world. Use Unload to remove this loader\'s props.'
        self.paint();return self.status()
    def load_now(self,_=None):
        self.refresh();key=self.assignments.values.get(self.current['world'])
        if not key:raise ValueError('Choose a map first')
        if not self.current['ready'] or not self.visits.stable(self.current,time.monotonic()):raise RuntimeError('Wait for a stable exploration pawn before loading')
        self.close_menu();return self.apply(key)
    def unload(self,_=None):
        if self.runtime:self.runtime.close()
        self.visits.attempted=True
        self.message='Map unloaded. Automatic loading remains paused for this visit; Load Now can reload.'
        return self.status()
    def apply(self,key):
        self.visits.attempted=True
        total_started=time.perf_counter()
        try:
            self.check_legacy()
            started=time.perf_counter()
            data=self.store.read(key)
            self._mark('map_read_validate',started)
            if data['world']!=self.current['world']:raise ValueError('Saved map belongs to a different vanilla world')
            started=time.perf_counter()
            self.runtime.close()
            self._mark('previous_map_cleanup',started)
            started=time.perf_counter()
            result=self.runtime.load(data,self.current)
            self._startup_map_loaded=True
            self._mark('placement',started)
            self.message=f"Loaded {result['objects']} props. It will load again on the next visit."
            if isinstance(result,dict) and result.get('skipped_world_edits'):
                self.message=f"Loaded {result['objects']} props; skipped {result['skipped_world_edits']} existing-world edits. Original save unchanged."
        except Exception as exc:self.message='Map not loaded: '+str(exc)
        finally:
            self._mark('apply_total',total_started)
            LOG.info('Map loader timing: %s',self.timing_status())
        return self.status()
    def open_menu(self,_=None):
        with reads(self.session.pid):return self._open_menu()
    def _open_menu(self):
        if self.panel is not None:self.close_menu();return
        self.refresh()
        from expedition33.widgets import OwnedMenuPanel
        self.panel=OwnedMenuPanel(self.session,controls=12,cached_construction=True,selected_results=True)
        try:
            self.panel.build();self.paint();self.panel.open()
            self.panel.menu.bind_controls([(button,lambda event,i=i:self.click(i)) for i,button in enumerate(self.panel.buttons)])
        except Exception:
            self.close_menu();raise
    def close_menu(self):
        if self.panel is not None:
            with reads(self.session.pid):
                if not self.panel.close():raise RuntimeError('Map loader menu cleanup pending')
            self.panel=None
    def paint(self):
        if self.panel is None or self.panel.state not in ('built','open'):return
        with reads(self.session.pid):return self._paint()
    def _paint(self):
        p=self.panel;key=self.assignments.values.get(self.current['world']);page=self.rows[self.offset:self.offset+6]
        with p.paint_batch():
            p.set_text(p.title,'WorldBuilder Map Loader - '+self.current['world'].rsplit('.',1)[-1])
            p.set_text(p.detail,display_detail(self.message,width=44,height=12)+'\n\nOne saved map per vanilla world. '+str(len(self.rows))+' saves here.\nPage '+str(self.offset//6+1)+'/'+str(max(1,(len(self.rows)+5)//6)))
            for i in range(6):
                row=page[i] if i<len(page) else None
                p.set_text(p.labels[i],display_line(('[Selected] ' if row and row['id']==key else '')+row['name']+f" ({row['count']} objects)",80) if row else ('No saves for this map - Close' if i==0 else ''))
                p.set_visible(i,row is not None or i==0)
            for i,label in enumerate(('Previous','Next','No automatic map','Load Now / Reload','Close','Unload map'),6):p.set_text(p.labels[i],label)
            p.set_enabled(6,self.offset>0);p.set_enabled(7,self.offset+6<len(self.rows));p.set_enabled(9,bool(key))
    def click(self,index):
        try:
            if index==0 and not self.rows:self.close_menu()
            elif index<6:self.choose(self.rows[self.offset+index]['id'])
            elif index==6:self.offset=max(0,self.offset-6)
            elif index==7:self.offset+=6
            elif index==8:self.clear()
            elif index==9:self.load_now()
            elif index==10:self.close_menu()
            elif index==11:self.unload()
        except Exception as exc:self.message=str(exc)
        self.paint()
    def poll(self):
        if self._world_retiring or self._disable_preparing:return
        now=time.monotonic()
        if now<self.next_poll:return
        self.next_poll=now+1.
        try:
            started=time.perf_counter()
            if self._context_monitor is None:
                pid=self.session.pid
                self._context_monitor=ReadOnlyAdmissionMonitor(
                    lambda:ContextObserver(pid),interval=1.,max_age=2.)
            observation=self._context_monitor.snapshot()
            self._mark('context_observation',started)
            # Pending/stale reads are uncertainty, not a missing-world result.
            # Preserve Visits and all owners until a completed sample exists.
            if observation is None:return
            value=observation.admission
            ctx=value.copy() if value is not None else None
            if ctx and (not self.current or ctx['visit']!=self.current['visit']):self._visit_observed_at=now
            if self.panel and (not ctx or not self.current or ctx['visit']!=self.current['visit']):self.close_menu()
            if self.runtime.started and ctx and self.runtime.visit!=ctx['visit']:self.runtime.close()
            self.current=ctx
            due=self.visits.observe(ctx,now)
            if due and ctx and not self.panel:
                key=self.assignments.values.get(ctx['world'])
                if key:
                    if self._visit_observed_at is not None:
                        self.timings['visit_to_apply']=dict(calls=1,total_ms=(now-self._visit_observed_at)*1000,max_ms=(now-self._visit_observed_at)*1000)
                    self.apply(key)
        except Exception as exc:self.message=str(exc)
    def revoke_world(self,context):
        self._world_retiring=True
        self.visits.attempted=True # Revoke automatic placement without settings writes.

    def begin_world_retirement(self,context):
        if self._retirement_result is not None:return self._retirement_result
        self._world_retiring=True
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if self._retirement_result in ('ack','unknown'):return self._retirement_result
        settled=True
        if self._context_monitor is not None:
            settled=self._context_monitor.close(timeout=0)
            if settled:self._context_monitor=None
        if not settled:
            self._retirement_result='pending';return 'pending'
        outcomes=[]
        # Explicit domain retire APIs own their exact native journals. Never
        # substitute the graceful close paths, which can restore old game state.
        for owner in (self.panel,self.runtime):
            if owner is None:continue
            retire=getattr(owner,'retire_world',None)
            if not callable(retire):outcomes.append('unknown');continue
            try:
                outcome=retire()
                if type(outcome) is not str or outcome not in ('ack','pending','unknown'):
                    raise RuntimeError('Invalid map owner retirement ACK')
            except BaseException:outcome='unknown'
            outcomes.append(outcome)
            if owner is self.panel and outcome=='ack':self.panel=None
        if 'unknown' in outcomes:self._retirement_result='unknown'
        elif not settled or 'pending' in outcomes:self._retirement_result='pending'
        else:self._retirement_result='ack'
        return self._retirement_result

    def prepare_disable(self):
        # Stop passive work before any game-facing cleanup can begin. Keep this
        # latch while another mod's barrier is pending; poll must not restart it.
        self._disable_preparing=True
        if self._context_monitor is None:return True
        settled=self._context_monitor.close(timeout=2.)
        if type(settled) is not bool:raise RuntimeError('Invalid map observer shutdown ACK')
        if settled:self._context_monitor=None
        return settled

    def disable(self):
        if not self.prepare_disable():
            from expedition33.mods import ModDisablePending
            raise ModDisablePending('Map context observer cleanup pending; disable has not started')
        self.close_menu()
        if self.runtime:self.runtime.close()
        self.session=None
