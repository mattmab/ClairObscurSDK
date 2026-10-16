"""Select a World Builder overlay for each vanilla exploration map."""
import time,textwrap
from expedition33.management import ModDefinition,Action,Keybind
from expedition33.paths import settings_dir
from .state import Assignments,Visits

class Mod:
    def __init__(self):
        self.session=None;self.panel=None;self.rows=[];self.offset=0;self.current=None
        self.next_poll=0.;self.message='Choose one saved overlay for each vanilla map.'
        self.visits=Visits();self.assignments=None
    def management(self):
        return ModDefinition('e33.map-overlays','Map Overlays',version='0.1.0',
            description='Requires World Builder enabled. F4: choose a saved overlay for the current vanilla map. Each map remembers its own choice and loads it once per visit, without freecam.',
            actions=(Action('open','Choose overlay for current map',self.open_menu),Action('status','Overlay status',self.status)),
            keybinds=(Keybind('open','Choose map overlay','F4',self.open_menu),))
    def enable(self,session):
        self.session=session;self.assignments=Assignments(settings_dir()/'E33MapOverlays'/'assignments.json')
        session.console.expose('map_overlays',self)
        session.actions.register('map_overlays.status',self.status,mutates=False)
        session.actions.register('map_overlays.open',self.open_menu)
        session.actions.register('map_overlays.choose',self.choose,schema={'type':'object','properties':{'map_id':{'type':'string'}},'required':['map_id'],'additionalProperties':False})
        session.actions.register('map_overlays.clear',self.clear)
    def builder(self):
        # Resolve afresh: World Builder may be disabled/reloaded independently.
        wb=self.session._session.console.dispatcher.namespace.get('world_builder')
        if wb is None or wb.session is None or not hasattr(wb,'load_overlay'):
            raise RuntimeError('Enable the updated World Builder mod first')
        return wb
    def startup_pending(self):
        if self.session is None:return False
        try:self.builder()
        except RuntimeError:return False
        return self.current is None or (bool(self.assignments.values.get(self.current['world'])) and not self.visits.attempted)
    def status(self,_=None):
        return dict(current=self.current,selected=self.assignments.values.get(self.current['world']) if self.current else None,
                    assignments=dict(self.assignments.values),message=self.message)
    def refresh(self):
        wb=self.builder();self.current=wb.overlay_context()
        if not self.current:raise RuntimeError('Load a vanilla exploration map first')
        self.rows=[r for r in wb.library.store.list() if r['world']==self.current['world']]
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
        self.message='Automatic loading disabled for this map. Existing placed objects remain.'
        self.paint();return self.status()
    def load_now(self):
        if self.visits.attempted:raise RuntimeError('Already attempted this visit; reload the vanilla map to avoid duplicate placement')
        self.refresh();key=self.assignments.values.get(self.current['world'])
        if not key:raise ValueError('Choose an overlay first')
        self.close_menu();self.apply(key)
    def apply(self,key):
        self.visits.attempted=True
        try:
            self.builder().load_overlay(key,self.current)
            self.message='Overlay loaded. It will load again on the next visit.'
            __import__('logging').getLogger(__name__).info('Automatic map overlay loaded')
        except Exception as exc:self.message='Overlay not loaded: '+str(exc)
    def open_menu(self,_=None):
        with self.builder().menu_reads():return self._open_menu()
    def _open_menu(self):
        if self.panel is not None:self.close_menu();return
        self.refresh()
        from expedition33.widgets import OwnedMenuPanel
        self.panel=OwnedMenuPanel(self.session,controls=11,cached_construction=True,selected_results=True)
        try:
            self.panel.build();self.paint();self.panel.open()
            self.panel.menu.bind_controls([(button,lambda event,i=i:self.click(i)) for i,button in enumerate(self.panel.buttons)])
        except Exception:
            self.close_menu();raise
    def close_menu(self):
        if self.panel is not None:
            with self.builder().menu_reads():
                if not self.panel.close():raise RuntimeError('Overlay menu cleanup pending')
            self.panel=None
    def paint(self):
        if self.panel is None or self.panel.state not in ('built','open'):return
        with self.builder().menu_reads():return self._paint()
    def _paint(self):
        p=self.panel;key=self.assignments.values.get(self.current['world']);page=self.rows[self.offset:self.offset+6]
        with p.paint_batch():
            p.set_text(p.title,'Map Overlays - '+self.current['world'].rsplit('.',1)[-1])
            p.set_text(p.detail,textwrap.fill(self.message,44)+'\n\nOne overlay per vanilla map. '+str(len(self.rows))+' saves here.\nPage '+str(self.offset//6+1)+'/'+str(max(1,(len(self.rows)+5)//6)))
            for i in range(6):
                row=page[i] if i<len(page) else None
                p.set_text(p.labels[i],('[Selected] ' if row and row['id']==key else '')+row['name']+f" ({row['count']} objects)" if row else ('No saves for this map - Close' if i==0 else ''))
                p.set_visible(i,row is not None or i==0)
            for i,label in enumerate(('Previous','Next','No automatic overlay','Load now','Close'),6):p.set_text(p.labels[i],label)
            p.set_enabled(6,self.offset>0);p.set_enabled(7,self.offset+6<len(self.rows));p.set_enabled(9,bool(key) and not self.visits.attempted)
    def click(self,index):
        try:
            if index==0 and not self.rows:self.close_menu()
            elif index<6:self.choose(self.rows[self.offset+index]['id'])
            elif index==6:self.offset=max(0,self.offset-6)
            elif index==7:self.offset+=6
            elif index==8:self.clear()
            elif index==9:self.load_now()
            elif index==10:self.close_menu()
        except Exception as exc:self.message=str(exc)
        self.paint()
    def poll(self):
        now=time.monotonic()
        if now<self.next_poll:return
        self.next_poll=now+1.
        try:
            ctx=self.builder().overlay_context()
            if self.panel and (not ctx or not self.current or ctx['visit']!=self.current['visit']):self.close_menu()
            self.current=ctx
            due=self.visits.observe(ctx,now)
            if due and ctx and not self.panel:
                key=self.assignments.values.get(ctx['world'])
                if key:self.apply(key)
        except Exception as exc:self.message=str(exc)
    def disable(self):
        self.close_menu();self.session=None
