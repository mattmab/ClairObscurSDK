"""Folder/thumbnail browser, scene workspace and owned engine previews."""
from datetime import datetime
import math, textwrap, time, logging, json, hashlib
from concurrent.futures import ThreadPoolExecutor
from expedition33.catalog import capture_selected
import struct
from . import thumbnail_cache as cache
from expedition33.widgets import OwnedMenuPanel
from expedition33.catalog import capture
from expedition33.values import read_object_reference
from .browser import Browser
LOG=logging.getLogger('expedition33.world_builder.preview')

class CatalogMenu(OwnedMenuPanel):
    PAGE=18
    def __init__(self,mod):
        super().__init__(mod.session,controls=51,cached_construction=True,selected_results=True)
        self.mod=mod;self.library=mod.library;self.browser=Browser(self.library.store.root.parent)
        self.offset=0;self.kind='mesh';self.query='';self.selected=None;self.workspace='Build'
        self.folder='/Game/';self.folders=True;self.favorites=False
        self.bindings=[];self.rows=[];self.images=[];self.thumbnails={};self.pending=[];self.gallery=[];self.signature=None
        self.preview_failures={};self.preview_job=None;self.processing=[];self.preview_worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix="builder-thumbnails")
        self.displayed={};self.cache_stats=dict(imported=0,page_load_ms=0.)
        from .background_cache import BackgroundCache
        self.background=BackgroundCache(self.library.store.root.parent);self.background_rows=-1;self.background_paint_at=0.
        cache.ROOT.mkdir(parents=True,exist_ok=True)
        from .gallery import Gallery
        self.batch_gallery=Gallery(self);self.capture_paused=False;self.capture_queue=[];self.map_job=None;self.library_assets=False
        self.map_views_file=self.library.store.root.parent/'map-views.json'
        try:self.map_views=json.loads(self.map_views_file.read_text(encoding='utf8'))
        except (OSError,ValueError):self.map_views={}
    def _mutate(self,method,*args,**kwargs):
        was_uncertain=self.uncertain
        try:return super()._mutate(method,*args,**kwargs)
        except Exception as error:
            # A validated rejection did not touch the widget tree. Do not retry
            # the failed call, but keep unrelated cleanup/input operations usable.
            if not was_uncertain and getattr(error,'outcome',None)=='not_dispatched':
                self.uncertain=False
            import traceback
            path=self.library.store.root.parent/'menu-error.log'
            with path.open('a',encoding='utf8') as log:log.write(traceback.format_exc()+'\n')
            raise
    def invalidate_native_images(self):
        # Native camera exit releases its texture leases, including on Escape.
        # Disk PNGs survive; UObject identities must never survive that exit.
        if self.preview_job and self.preview_job.get('background'):self.background.interrupted(self.preview_job['asset'])
        self.thumbnails.clear();self.pending=[];self.signature=None
        self.displayed.clear()
        self.map_job=None
        if self.preview_job and self.preview_job.get('future'):
            self.preview_job['future'].cancel()
        self.preview_job=None
        self.capture_paused=True;self.batch_gallery.paused=True
    def _render_call(self,obj,owner,name,**arguments):
        try:return super()._render_call(obj,owner,name,**arguments)
        except Exception:
            with (self.library.store.root.parent/'menu-error.log').open('a',encoding='utf8') as log:log.write(repr((obj,owner,name,arguments))+'\n')
            raise
    def _call(self,obj,owner,name,**arguments):
        if self.state=='building' and (owner=='EditableTextBox' or name in ('SetRenderScale','SetRenderTransformPivot')):
            with self._construction_call(obj,self._function(owner,name),**arguments):pass
            return
        return super()._call(obj,owner,name,**arguments)
    def label(self,x,y,w,h,scale=.62):
        label=self._label(x,y,w/scale,h/scale)
        self._call(label,'Widget','SetRenderTransformPivot',Pivot={'X':0.,'Y':0.})
        self._call(label,'Widget','SetRenderScale',Scale={'X':scale,'Y':scale})
        return label
    def button(self,x,y,w,h):
        button=self._spawn('Button');self._place(button,x,y,w,h);self.buttons.append(button)
        self._call(button,'Button','SetBackgroundColor',InBackgroundColor={'R':.07,'G':.14,'B':.18,'A':1.})
        label=self.label(x+10,y+8,w-20,h-16);self.labels.append(label)
        i=len(self.buttons)-1;self._visible[i]=True;self._enabled[i]=True
    def build(self):
        from expedition33.enums import describe_enums
        self.state='building';observed=capture()
        self.player=self._one(o for o in observed.select('PlayerController') if not o.object_flags&0x30)
        self.library.refresh(force=False,observed=observed)
        engines={o.index for o in observed.select('GameEngine')}
        self.catalog=observed.subset(o for o in observed.objects if o.index in observed.classes or o.class_name in ('Function','ScriptStruct','Enum') or o.name in ('Default__GameplayStatics','Default__WidgetBlueprintLibrary') or o.index==self.player.index or o.index in engines)
        enum=self.catalog.find_path('/Script/UMG.ESlateVisibility','Enum');descriptor=describe_enums(self.catalog,[enum])[enum.index]
        def visibility(name):return descriptor.value(next(m.name for m in descriptor.members if m.name.endswith('::'+name)))
        self.invisible=visibility('HitTestInvisible');self.visible=visibility('Visible');self.collapsed=visibility('Collapsed')
        self._planner=self.scope.invocation_planner(selected_results=True,catalog=self.catalog);self._layout_queue=[]
        self.widget=self._construction_call(self._default('WidgetBlueprintLibrary'),self._function('WidgetBlueprintLibrary','Create'),WorldContextObject=self.player,WidgetType=self._class('CommonActivatableWidget'),OwningPlayer=self.player).return_value
        self.tree,c=read_object_reference(self._planner._catalog,self.widget,self._class('UserWidget'),'WidgetTree');self._planner.refresh_from(c)
        self.canvas=self._spawn('CanvasPanel')
        backdrop=self._spawn('Border');slot=self._place(backdrop,0,0,0,0)
        self._call(slot,'CanvasPanelSlot','SetAnchors',InAnchors={'Minimum':{'X':0.,'Y':0.},'Maximum':{'X':1.,'Y':1.}})
        self._call(backdrop,'Border','SetBrushColor',InBrushColor={'R':.012,'G':.018,'B':.028,'A':.98})
        self.title=self.label(24,20,1300,48,.9);self.breadcrumb=self.label(24,73,660,35)
        self.detail=self.label(1360,145,530,180);self.footer=self.label(24,1030,1300,45,.57)
        for i in range(self.PAGE):
            x=24+(i%6)*218;y=205+(i//6)*250
            self.button(x,y,210,238)
            slot,c=read_object_reference(self._planner._catalog,self.labels[-1],self._class('Widget'),'Slot');self._planner.refresh_from(c)
            self._call(slot,'CanvasPanelSlot','SetPosition',InPosition={'X':float(x+10),'Y':float(y+170)})
            self._call(slot,'CanvasPanelSlot','SetSize',InSize={'X':310.,'Y':100.})
            art=self._spawn('Image');self._place(art,x+8,y+8,194,150);self._call(art,'Widget','SetVisibility',InVisibility=self.collapsed);self.images.append(art)
        for layout in ((24,973,640,45),(680,973,640,45),(700,70,150,38),(860,70,150,38),(1020,70,150,38),(1180,70,140,38)):self.button(*layout)
        for i in range(4):self.button(1360+i*134,75,128,48)
        for i in range(8):self.button(1360+(i%2)*270,825+(i//2)*59,260,50)
        for i in range(14):self.button(1360+(i%2)*270,340+(i//2)*55,260,48)
        self.button(1730,16,160,40)
        self.field1=self._spawn('EditableTextBox');self._place(self.field1,1360,220,530,48)
        self.field2=self._spawn('EditableTextBox');self._place(self.field2,1360,278,530,48)
        self.search=self._spawn('EditableTextBox');self._place(self.search,24,120,1296,58)
        self.map_name=self._spawn('EditableTextBox');self._place(self.map_name,1360,750,530,55)
        for widget,text in ((self.field1,'18'),(self.field2,'600'),(self.search,''),(self.map_name,'Builder '+datetime.now().strftime('%Y-%m-%d %H-%M'))):
            self._call(widget,'EditableTextBox','SetText',InText=text)
            self._call(widget,'EditableTextBox','SetForegroundColor',Color={'R':.015,'G':.02,'B':.03,'A':1.})
        self.image=self._spawn('Image');self._place(self.image,1385,355,480,360);self._call(self.image,'Widget','SetVisibility',InVisibility=self.collapsed)
        self._flush_layout()
        self._mutate(self.scope.assign_object,self.tree,self._class('WidgetTree'),'RootWidget',self.canvas,expected=None,allow_mutation=True,catalog=self._planner._catalog)
        self.assigned=True;self.state='built';return self
    def set_text(self,label,text):
        if label in (self.breadcrumb,self.footer):
            if self._text.get(label.index)!=text:
                self._render_call(label,'TextBlock','SetText',InText=text);self._text[label.index]=text
            return
        return super().set_text(label,text)
    def text(self,widget):
        with self._planner.prepare(widget,self._function('EditableTextBox','GetText')).invoke() as result:return str(result.return_value)
    def clear_images(self,purge=False):
        for image in [*self.images,*([self.image] if hasattr(self,'image') else [])]:
            self._render_call(image,'Image','SetBrushResourceObject',ResourceObject=None)
            self._render_call(image,'Widget','SetVisibility',InVisibility=self.collapsed)
        self.pending=[]
        self.displayed.clear()
        if purge:
            self.cancel_preview()
            if self.mod.started:self.mod.scene_command(39)
            self.thumbnails.clear()
    def all_rows(self):
        if self.workspace=='Library' and not self.library_assets:return [dict(path=r['asset'],name=r['asset'].rsplit('.',1)[-1],kind=r['kind'],id=r['id']) for r in self.library.owned.values() if r['id']!=self.library.preview_key and self.query.casefold() in r['asset'].casefold()]
        if self.workspace=='Maps':return [dict(r,kind='map') for r in self.library.store.list() if self.query.casefold() in r['name'].casefold()]
        if not self.library.registry_complete:self.library.refresh(force=False)
        return self.browser.rows(self.library.rows,self.query,self.kind,self.folder,self.folders,self.favorites)
    def paint(self):
        rows=self.all_rows();count=len(rows)
        self.offset=min(self.offset,max(0,((count-1)//self.PAGE)*self.PAGE));self.rows=rows[self.offset:self.offset+self.PAGE]
        signature=tuple((r['kind'],r.get('path',r.get('id'))) for r in self.rows)
        if signature!=self.signature:
            self.clear_images();self.signature=signature
        assets=list(dict.fromkeys(r.get('cover',r.get('path')) for r in self.rows if r['kind']!='map'))
        cached=[(asset,cache.thumbnail_key(asset)) for asset in assets if asset and asset not in self.thumbnails and asset not in self.preview_failures]
        cached += [('map:'+row['id'],self.map_key(row['id'])) for row in self.rows if row['kind']=='map' and 'map:'+row['id'] not in self.thumbnails]
        self.import_textures([(asset,key) for asset,key in cached if cache.cached_png(key)])
        self.pending=[asset for asset in assets if asset and asset not in self.thumbnails and asset not in self.preview_failures and (not self.preview_job or asset!=self.preview_job['asset'])]
        for row in self.rows:
            asset='map:'+row['id'] if row['kind']=='map' else row.get('cover',row.get('path'))
            if asset in self.thumbnails:self.show_texture(asset,False)
        with self.paint_batch():
            self.set_text(self.title,'WORLD BUILDER  /  '+self.workspace)
            self.set_text(self.labels[50],'Close / F7')
            self.set_text(self.breadcrumb,f"{self.folder if self.folders else 'All assets'}  |  {count} entries  |  Page {1+self.offset//self.PAGE}/{max(1,math.ceil(count/self.PAGE))}")
            for i in range(self.PAGE):
                valid=i<len(self.rows);self.set_enabled(i,valid);text=''
                if valid:
                    r=self.rows[i];name=r['name'];text='\n'.join(name[j:j+19] for j in range(0,min(len(name),38),19))
                    if r['kind']=='folder':text+=f"\n{r['count']} assets / Open folder"
                    elif r['kind']=='map':text+=f"\n{r['count']} tracked objects"
                    elif r.get('path') in self.browser.favorites:text+='  [*]'
                self.set_text(self.labels[i],text)
            labels=['Previous','Next','Favorites ON' if self.favorites else 'Favorites','Folders ON' if self.folders else 'All assets',self.kind.title(),'Up folder','Build','Gallery','Library','Maps','Load map' if self.workspace=='Maps' else 'Spawn page' if self.workspace=='Gallery' else 'Spawn selected','Preview','Favorite / unfavorite','Save map','Load selected map','Clear scene','Resume camera','Refresh catalog']
            for i,label in enumerate(labels,self.PAGE):self.set_text(self.labels[i],label)
            extra=[]
            if self.workspace=='Gallery':extra=['Packing: '+('Tight' if self.batch_gallery.tight else 'Spaced'),'Spawn first batch','Previous batch','Next batch','Clear gallery','Pause / resume','Visit next','Resume camera','Save galleries','Rebuild saved','Free camera','Retry failed']
            elif self.workspace=='Library':extra=['Favorite / unfavorite','Save category/tags','Quick icons','Resume capture','Pause capture','Cancel capture','Index loaded meshes','All registered meshes','Retry cleanup','Scene objects' if self.library_assets else 'Asset tools','Visit selected','Duplicate selected','Delete selected','AFK cache: '+('ON' if self.background.mode=='afk' else 'OFF')]
            for j in range(14):
                self.set_visible(36+j,j<len(extra));self.set_text(self.labels[36+j],extra[j] if j<len(extra) else '')
            for field in (self.field1,self.field2):self._render_call(field,'Widget','SetVisibility',InVisibility=self.visible if extra else self.collapsed)
            if extra:self._render_call(self.image,'Widget','SetVisibility',InVisibility=self.collapsed)
            if self.workspace=='Maps':
                self.set_text(self.labels[29],'Take map thumbnail');self.set_text(self.labels[30],'Visit saved view')
            detail=self.batch_gallery.summary()+'\nBatch size / spacing (cm)' if self.workspace=='Gallery' else self.library.message
            if self.workspace=='Library':detail+='\nCategory / tags fields'+(f'\nIcons: {len(self.capture_queue)} queued / '+('paused' if self.capture_paused else 'running') if self.library_assets else '')

            if self.selected:detail+=('\n'+self.selected['name'][:42]) if extra else ('\n\n'+self.selected['name'][:75]+'\n'+self.selected.get('path',self.selected.get('world',''))[:110])
            detail="\n".join(textwrap.fill(line,width=48,break_long_words=True,break_on_hyphens=False) for line in detail.splitlines())
            self.set_text(self.detail,detail)
            tracked=len(self.library.owned)-int(self.library.preview_key in self.library.owned)
            bg=self.background.status()
            self.set_text(self.footer,f"{len(self.library.rows)} assets | {tracked} tracked | Cache {bg['cached']}/{bg['total']} | {bg['failed']} skipped | Background {('AFK fast' if bg['mode']=='afk' else 'idle-time') if bg['enabled'] else 'paused'}")
    def open(self):
        self.mod.scene_command(45,objects=(self.widget,))
        self.mod.automatic(False);super().open()
        self.mod.hud._render_call(self.mod.hud.widget,'Widget','SetVisibility',InVisibility=self.mod.hud.collapsed)
        self.bindings=[]
        for start in range(0,len(self.buttons),24):self.bindings.extend(self.menu.bind_controls([(b,lambda event,i=i:self.click(i)) for i,b in enumerate(self.buttons) if start<=i<start+24]))
    def click(self,i):
        try:
            if 18<=i<=23:self.selected=None
            if i<self.PAGE:
                if i>=len(self.rows):return
                self.selected=self.rows[i]
                if self.selected['kind']=='folder':self.folder=self.selected['path'];self.offset=0;self.selected=None
                elif self.selected['kind']=='map':self.show_map()
                else:
                    if self.workspace=='Library':
                        metadata=self.browser.metadata.get(self.selected['path'],{})
                        for field,value in ((self.field1,metadata.get('category','Props')),(self.field2,metadata.get('tags',''))):self._render_call(field,'EditableTextBox','SetText',InText=value)
                    self.preview(self.selected['path'])
            elif i==18:self.offset=max(0,self.offset-self.PAGE)
            elif i==19:
                if len(self.rows)==self.PAGE:self.offset+=self.PAGE
            elif i==20:self.favorites=not self.favorites;self.offset=0
            elif i==21:self.folders=not self.folders;self.offset=0
            elif i==22:self.kind='actor' if self.kind=='mesh' else 'mesh';self.offset=0
            elif i==23:self.folder=self.folder.rstrip('/').rsplit('/',1)[0]+'/' if self.folder!='/Game/' else '/Game/';self.offset=0
            elif 24<=i<=27:
                self.workspace=('Build','Gallery','Library','Maps')[i-24];self.offset=0;self.selected=None
                for field,value in ((self.field1,'1000' if self.workspace=='Gallery' else 'Props'),(self.field2,'600' if self.workspace=='Gallery' else '')):self._render_call(field,'EditableTextBox','SetText',InText=value)
            elif i==28:
                if self.workspace=='Gallery':self.start_gallery()
                elif self.workspace=='Maps':self.load_map()
                else:self.library.spawn(self.asset())
            elif i==29:
                if self.workspace=='Maps':self.take_map_thumbnail()
                else:self.mod.start_booth(self.asset());return
            elif i==30:
                if self.workspace=='Maps':self.visit_map()
                else:self.browser.favorite(self.asset())
            elif i==31:self.library.save(self.text(self.map_name))
            elif i==32:self.load_map()
            elif i==33:self.cancel_preview();self.batch_gallery.clear();self.gallery=[];self.library.clear()
            elif i==34:self.hide();return
            elif i==35:self.library.refresh();self.signature=None
            elif i==50:self.hide();return
            elif i>=36:self.workspace_action(i-36)
        except Exception as e:self.library.message=str(e)
        self.paint()
    def asset(self):
        if not self.selected or self.selected['kind'] in ('folder','map'):raise ValueError('Select a mesh or actor first')
        return self.selected['path']
    def load_map(self):
        if not self.selected or self.selected['kind']!='map':raise ValueError('Choose a saved map in the Maps tab')
        self.cancel_preview();self.library.load(self.selected['id'])
    def start_gallery(self):
        assets=self.browser.rows(self.library.rows,self.query,self.kind,self.folder,False,self.favorites)
        if not self.query and self.folders:assets=[r for r in assets if r['path'].startswith(self.folder)]
        self.batch_gallery.start([r['path'] for r in assets],self.text(self.field1),self.text(self.field2))
    def adopt(self,c):
        # Scene actors are disposable; Unreal may reuse their object slots for
        # imported textures. Refresh observations before planning a new call.
        old=self._planner._catalog
        changed=any(o.index in old.by_index and any(getattr(old.by_index[o.index],k)!=getattr(o,k) for k in ('serial','address','name','class_index')) for o in c.objects)
        if changed:self._planner.refresh_from(capture())
        else:self._planner.adopt_observations(c)
    def bounds(self,key):
        row=self.library.owned[key];c=capture_selected(self.mod.session.pid,[tuple(row['actor'])]);actor=c.by_index[row['actor'][0]];self.adopt(c)
        with self._planner.prepare(actor,self._function('Actor','GetActorBounds'),bOnlyCollidingComponents=False,bIncludeFromChildActors=True).invoke() as result:
            return ([result.outputs['Origin'][x] for x in ('X','Y','Z')],[result.outputs['BoxExtent'][x] for x in ('X','Y','Z')])
    def workspace_action(self,i):
        g=self.batch_gallery
        if self.workspace=='Gallery':
            if i==0:
                g.tight=not g.tight
                if g.assets:g.request(0)
            elif i==1:self.start_gallery()
            elif i==2:g.request(-1)
            elif i==3:g.request(1)
            elif i==4:g.clear()
            elif i==5:g.paused=not g.paused
            elif i==6:g.visit()
            elif i in (7,10):self.hide()
            elif i==8:g.save()
            elif i==9:g.rebuild()
            elif i==11:g.queue.extend(r['asset'] for r in g.failures);g.failures=[];g.paused=False
        elif self.workspace=='Library':
            if i==0:self.browser.favorite(self.asset())
            elif i==1:self.browser.tag(self.asset(),self.text(self.field1),self.text(self.field2));self.library.message='Saved category and tags'
            elif i==2:self.capture_queue=list(dict.fromkeys(r.get('cover',r.get('path')) for r in self.rows if r['kind'] in ('mesh','folder')));self.capture_paused=False
            elif i==3:self.background.set_enabled(True);self.capture_paused=False
            elif i==4:
                self.capture_paused=True;self.background.set_enabled(False)
                if not self.preview_job or self.preview_job.get('background'):self.cancel_preview()
            elif i==5:self.capture_paused=True;self.capture_queue=[];self.background.set_enabled(False);self.cancel_preview()
            elif i==6:self.library.refresh(force=False);self.signature=None
            elif i==7:self.library.refresh();self.signature=None
            elif i==8:self.cancel_preview();self.preview_failures.clear();self.signature=None
            elif i==13:
                self.background.set_mode('idle' if self.background.mode=='afk' else 'afk')
                if self.background.mode=='afk':self.background.set_enabled(True)
                self.library.message='AFK cache runs after 5 seconds idle; game input pauses capture. Pause capture stops it.'
            elif i==9:self.library_assets=not self.library_assets;self.selected=None;self.offset=0;self.signature=None
            elif i in (10,11,12):
                if not self.selected or 'id' not in self.selected:raise ValueError('Select a spawned scene object')
                key=self.selected['id']
                if i==10:
                    center,extent=self.bounds(key);radius=max(200.,sum(v*v for v in extent)**.5*2.5);self.mod.command(42,values=[center[0]-radius,center[1],center[2]+radius*.3,-17,0,0,0,0]);self.hide()
                elif i==11:self.library.duplicate(key)
                else:self.library.delete(key);self.selected=None;self.signature=None
    def map_key(self,key):return hashlib.sha256(('e33-map-view:'+key).encode()).hexdigest()
    def show_map(self):
        self._render_call(self.image,'Widget','SetVisibility',InVisibility=self.collapsed)
        if not self.selected or self.selected['kind']!='map':return
        key=self.map_key(self.selected['id']);path=cache.ROOT/(key+'.png')
        if not path.exists():self.library.message='No map thumbnail yet; load the map, frame a view and take one';return
        self.import_texture('map:'+self.selected['id'],key);self.show_texture('map:'+self.selected['id'],True)
    def take_map_thumbnail(self):
        if not self.selected or self.selected['kind']!='map':raise ValueError('Choose a saved map')
        if getattr(self.library,'active_map',None)!=self.selected['id']:raise ValueError('Load or save this map before taking its thumbnail')
        self.cancel_preview();key=self.map_key(self.selected['id']);self.mod.command(43)
        _,_,d,_=self.library.context();rot=[d['ControlRotation'].fields[k] for k in ('Pitch','Yaw','Roll')]
        self.map_job=dict(id=self.selected['id'],key=key,ready=time.monotonic()+.25,pose=[*self.mod.last['position'],*rot,0,0]);self.library.message='Capturing map thumbnail'
    def visit_map(self):
        if not self.selected or self.selected['kind']!='map':raise ValueError('Choose a saved map')
        row=self.map_views.get(self.selected['id'])
        if not row:raise ValueError('Take a map thumbnail to save its view')
        _,_,_,world=self.library.context()
        if row['world']!=world:raise ValueError('Load the correct game level first')
        self.mod.command(42,values=row['pose']);self.hide()
    def import_texture(self,asset,key):
        self.import_textures([(asset,key)])
    def import_textures(self,entries):
        entries=list(dict((asset,key) for asset,key in entries if asset not in self.thumbnails).items())
        if not entries:return
        started=time.perf_counter()
        if len(self.thumbnails)+len(entries)>120:self.clear_images(purge=True);self.signature=None
        imported=[]
        for asset,key in entries:
            try:
                self.mod.command(38,thumbnail_key=key)
                imported.append((asset,struct.unpack_from('<iiQ',self.mod.last_raw,3568)))
            except Exception as error:
                self.preview_failures[asset]=str(error);LOG.exception('Cached thumbnail import failed: %s',asset)
        if imported:
            c=capture_selected(self.mod.session.pid,[identity for _,identity in imported]);self.adopt(c)
            for asset,identity in imported:self.thumbnails[asset]=c.by_index[identity[0]]
        self.cache_stats['imported']+=len(imported)
        self.cache_stats['page_load_ms']=round((time.perf_counter()-started)*1000,1)
    def cancel_preview(self):
        job=self.preview_job
        if job is not None:
            if job.get('background'):self.background.interrupted(job['asset'])
            if job.get('future') is not None:
                try:job['future'].result()
                except Exception:pass
            self.library.clear_preview();self.preview_job=None
        if self.mod.started:self.mod.scene_command(36)
        if job is not None and job.get('background') and job.get('future') is None:
            for suffix in ('.base.rgb','.normal.rgb'):(cache.ROOT/(job['key']+suffix)).unlink(missing_ok=True)
    def collect_processing(self,wait=False):
        for job in list(self.processing):
            if not wait and not job['future'].done():continue
            try:
                elapsed=job['future'].result();self.library.mark('cpu_decode_light_write',time.perf_counter()-elapsed)
                self.background.finish(job['asset'])
            except Exception as error:
                self.background.finish(job['asset'],error);LOG.exception('Thumbnail processing failed')
            self.processing.remove(job)
    def poll(self):
        self.collect_processing()
        if not self.mod.active or self.mod.booth_pending:return
        if self.background_rows!=len(self.library.rows):
            self.background.sync(self.library.rows);self.background_rows=len(self.library.rows)
        busy=self.mod.thumbnail_input_busy();idle=self.background.input(busy)
        if self.preview_job and self.preview_job.get('background'):
            # A completed CPU job can be collected during input; all engine
            # work waits until the user has been idle again.
            if (not self.background.enabled or busy or time.monotonic()-self.background.last_input<5.) and self.preview_job['stage']<2:return
        if self.state!='open' and self.preview_job is None:
            if idle:self.start_background()
            return
        if self.map_job:
            job=self.map_job
            if time.monotonic()<job['ready']:return
            try:
                self.mod.command(37,thumbnail_key=job['key'],thumbnail_stage=0)
                path=cache.ROOT/(job['key']+'.base.png');cache.read_png(path);path.replace(cache.ROOT/(job['key']+'.png'))
                self.map_views[job['id']]=dict(pose=job['pose'],world=self.library.world)
                tmp=self.map_views_file.with_suffix('.tmp');tmp.write_text(json.dumps(self.map_views),encoding='utf8');tmp.replace(self.map_views_file)
                self.thumbnails.pop('map:'+job['id'],None);self.show_map();self.library.message='Map thumbnail and view saved'
            except Exception as error:
                LOG.exception('Map thumbnail failed');self.library.message='Map thumbnail failed: '+str(error)[:160]
            finally:self.map_job=None;self.mod.scene_command(36)
            self.paint();return
        if self.state=='open' and not (self.background.mode=='afk' and idle):
            query=self.text(self.search)
            if query!=self.query:self.query=query;self.offset=0;self.selected=None;self.paint();return
        if self.preview_job is not None:
            job=self.preview_job
            started=time.perf_counter()
            try:
                if time.monotonic()<job['ready']:return
                if job['stage']<2:
                    if job.get('background'):
                        job['readback_polls']=job.get('readback_polls',0)+1
                        if job['readback_polls']>100:raise RuntimeError('Asynchronous thumbnail readback timed out')
                        op=49 if job.get('async_started') else 48
                        self.mod.command(op,thumbnail_key=job['key'] if op==48 else None)
                        ready,fmt=struct.unpack_from('<II',self.mod.last_raw,3560)
                        self.cache_stats['readback_game_max_ms']=struct.unpack_from('<d',self.mod.last_raw,3576)[0];self.cache_stats['readback_format']=fmt;self.cache_stats['readback_ready']=ready
                        self.library.mark('async_readback_poll',started)
                        if op==48:job['async_started']=bool(ready)
                        elif ready==2:job['stage']=2
                        job['ready']=time.monotonic()+.01
                    else:
                        self.mod.command(37,thumbnail_key=job['key'],thumbnail_stage=job['stage']);self.library.mark('export_'+str(job['stage']),started);job['stage']+=1;job['ready']=time.monotonic()+.1
                    if job['stage']==2:
                        if not job.get('background'):
                            cleanup_started=time.perf_counter();self.library.clear_preview();self.mod.scene_command(36);self.library.mark('capture_cleanup',cleanup_started)
                        job['future']=self.preview_worker.submit(cache.compose_timed,job['key'])
                        if job.get('background'):
                            self.processing.append(job);self.preview_job=None
                            if self.background.current==job['asset']:self.background.current=None
                elif job['future'].done():
                    elapsed=job['future'].result();self.library.mark('cpu_decode_light_write',time.perf_counter()-elapsed);self.preview_job=None;self.background.finish(job['asset'])
                    if not job.get('background'):self.preview(job['asset'],select=self.selected is not None and self.selected.get('path')==job['asset'])
            except Exception as error:
                self.background.finish(job['asset'],error)
                self.preview_failed(job['asset'],error);self.cancel_preview()
                return
            if job.get('background'):self.background.cost(time.perf_counter()-started)
            if self.state=='open' and (not job.get('background') or self.preview_job is None):
                if not job.get('background') or self.background.mode!='afk' or time.monotonic()>=self.background_paint_at:
                    if job.get('background') and self.background.mode=='afk':
                        bg=self.background.status();self.set_text(self.footer,f"AFK cache {bg['cached']}/{bg['total']} | {bg['remaining']} remaining | {bg['failed']} skipped | Game input pauses capture")
                    else:self.paint()
                    self.background_paint_at=time.monotonic()+2.
            return
        if self.state!='open':return
        if self.batch_gallery.queue and not self.batch_gallery.paused:
            deadline=time.monotonic()+.15
            for _ in range(16):
                self.batch_gallery.tick()
                if not self.batch_gallery.queue or self.batch_gallery.paused or time.monotonic()>=deadline:break
            if time.monotonic()-self.batch_gallery.last_paint>=.5 or not self.batch_gallery.queue:
                self.set_text(self.detail,self.batch_gallery.summary()+'\nBatch size / spacing (cm)')
                self.batch_gallery.last_paint=time.monotonic()
            return
        if self.capture_queue and not self.capture_paused:
            asset=self.capture_queue.pop(0)
            try:self.preview(asset,False)
            except Exception as error:self.preview_failed(asset,error);self.cancel_preview()
            self.paint();return
        if self.gallery:
            asset,transform=self.gallery.pop(0)
            try:self.library.spawn(asset,transform)
            except Exception as e:self.library.message=str(e);self.gallery=[]
            self.paint();return
        if self.pending:
            if len(self.thumbnails)>=120:self.clear_images(purge=True);self.signature=None;self.paint();return
            asset=self.pending.pop(0)
            try:self.preview(asset,select=self.selected is not None and self.selected.get('path')==asset)
            except Exception as error:
                self.preview_failed(asset,error);self.cancel_preview()
            self.paint()
            return
        if idle:self.start_background()
    def start_background(self):
        if self.preview_job or self.map_job or self.batch_gallery.queue or self.capture_queue or len(self.processing)>=2:return
        asset=self.background.take()
        if not asset:return
        started=time.perf_counter();message=self.library.message
        try:
            self.library.thumbnail_preview(asset)
            self.preview_job=dict(asset=asset,key=cache.thumbnail_key(asset),stage=0,ready=time.monotonic(),background=True,created=time.monotonic())
        except Exception as error:
            self.background.finish(asset,error);LOG.exception('Background thumbnail failed: %s',asset)
            self.library.clear_preview();self.mod.scene_command(36)
        finally:
            self.library.message=message;self.background.cost(time.perf_counter()-started)
    def preview_failed(self,asset,error):
        self.preview_failures[asset]=str(error)
        LOG.exception('Preview failed for %s',asset)
        if self.selected and self.selected.get('path')==asset:
            self.library.message='Preview failed: '+str(error)[:180]+'; click Preview to retry'
    def show_texture(self,asset,select):
        texture=self.thumbnails[asset]
        for i,row in enumerate(self.rows):
            if ('map:'+row['id'] if row['kind']=='map' else row.get('cover',row.get('path')))==asset and self.displayed.get(i)!=texture:
                self._render_call(self.images[i],'Image','SetBrushResourceObject',ResourceObject=texture)
                self._render_call(self.images[i],'Widget','SetVisibility',InVisibility=self.invisible)
                self.displayed[i]=texture
        if select:
            self._render_call(self.image,'Image','SetBrushResourceObject',ResourceObject=texture)
            self._render_call(self.image,'Widget','SetVisibility',InVisibility=self.invisible)
    def preview(self,asset,select=True):
        if asset not in self.thumbnails and len(self.thumbnails)>=120:self.clear_images(purge=True);self.signature=None
        if select:
            self._render_call(self.image,'Widget','SetVisibility',InVisibility=self.collapsed)
            if self.preview_job is not None and self.preview_job['asset']!=asset:self.cancel_preview()
            self.library.message='Loading preview: '+self.library.known.get(asset,{}).get('name',asset)
        if asset not in self.thumbnails:
            key=cache.thumbnail_key(asset);path=cache.ROOT/(key+'.png')
            if cache.cached_png(key):
                self.import_texture(asset,key)
                if asset not in self.thumbnails:return
            else:
                if self.preview_job is None:
                    for suffix in ('.base.png','.normal.png'):(cache.ROOT/(key+suffix)).unlink(missing_ok=True)
                    message=self.library.message;self.library.preview(asset);self.library.message=message
                    self.preview_job=dict(asset=asset,key=key,stage=0,ready=time.monotonic()+.1)
                elif self.preview_job['asset']!=asset and asset not in self.pending:self.pending.insert(0,asset)
                return
        self.show_texture(asset,select)
        if select:self.library.message='Thumbnail preview: '+self.library.known.get(asset,{}).get('name',asset)
        if asset in self.pending:self.pending.remove(asset)
    def hide(self):
        self.gallery=[];self.batch_gallery.paused=True;self.capture_paused=True
        if self.map_job:self.map_job=None;self.mod.scene_command(36)
        if self.state=='open':self._render_call(self.buttons[0],'Widget','SetUserFocus',PlayerController=self.player)
        self.cancel_preview()
        if self.bindings:
            while self.bindings:
                group=self.bindings[:24]
                if not self.menu.remove_controls(group):return False
                del self.bindings[:len(group)]
        result=super().hide()
        if result:
            self.mod.hud._render_call(self.mod.hud.widget,'Widget','SetVisibility',InVisibility=self.mod.hud.invisible)
            self.mod.automatic(True)
        return result
    def close(self):
        if self.state=='open':self.hide()
        if self.state!='closed':self.clear_images(purge=True);self.preview_worker.shutdown(wait=True);self.collect_processing(wait=True)
        return super().close()
