"""Local static catalog models for the experimental mesh SDK. MIT code only."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,time
from expedition33.management import ModDefinition,Action
from expedition33._scope import SessionScope
from expedition33.procedural_mesh import Tetrahedron
from expedition33.catalog import capture_matching
from .catalog import prepare,entries,DEFAULT_ROOT
from .browser import BrowserView

class Mod:
    def __init__(self):
        self.scope=None;self.model=None;self.pending=[];self.last={};self.session=None;self.catalog=None;self.future=None;self.pool=None;self.native=None;self.shared=None;self.entries=[];self.open_pending=False;self.next_poll=0;self.painted=None;self.skin_path=None;self.driver_index=None
        self.rig=None;self.follow_character=False;self.prepared_skin=None;self.next_character_check=0;self.rig_future=None;self.replacement_asset='2b'
        self._world_retiring=False;self._retirement_token=None;self._retirement_futures=[]
    @property
    def busy(self):return self.model is not None or self.future is not None
    def summary(self):return str(self.last) if not self.model else f"{self.last.get('state')} - {self.last.get('asset')} - {self.last.get('uploaded',0)}/{self.last.get('sections',0)} sections"
    def management(self):
        return ModDefinition('sdk.catalog-models','Asset Creator/Main Character Replacer',version='0.3.0',
            description='EXPERIMENTAL. User-supplied models only. Animation is not 1:1; loading needs improvement and meshes may lag.',
            actions=(Action('browse','Browse model catalog',lambda _:self.open()),Action('preview_2b','Preview 2B on current character (experimental)',lambda _:self.replacement_preview()),Action('replace_2b','Replace selected character with 2B',lambda _:self.select_replacement('2b')),Action('replace_ayane','Replace selected character with Ayane (prototype)',lambda _:self.select_replacement('ayane')),Action('destroy','Destroy current model / restore character',lambda _:self.destroy())))
    def enable(self,session):
        self._world_retiring=False;self._retirement_token=None;self._retirement_futures=[]
        if getattr(session._session._transport,'mesh_protocol',0)!=3:raise RuntimeError('Asset Creator requires SDK RC6 or newer with mesh protocol 3; public RC5 is unsupported')
        from .library import entries as user_entries
        self.entries=user_entries()+entries(DEFAULT_ROOT);self.shared=getattr(session._session,'_native_menu_service',None)
        if self.shared is None:raise RuntimeError('Enable SDK Management first')
        self.native=self.shared.for_view(lambda registry:BrowserView(registry,self));self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='CatalogStatic')
        self.session=session;session.console.register('catalog',self.command,owner=self)
    def command(self,args):
        key=args.strip()
        if key=='preview 2b':return self.replacement_preview()
        if key=='replace 2b':return self.select_replacement('2b')
        if key=='replace ayane':return self.select_replacement('ayane')
        if key=='shaders':return self.shader_samples()
        if key.startswith('shaders '):return self.shader_samples(int(key.split()[1]))
        if key=='nearest':return self.shader_nearest()
        if key in ('','open'):return self.open()
        if key=='list':return self.entries
        if key.startswith('spawn '):return self.spawn(key[6:])
        if key in ('bird','2b'):return self.spawn(key)
        if key=='destroy':return self.destroy()
        if key in ('status',''):return self.status()
        raise ValueError('catalog open | list | spawn <id> | bird | 2b | destroy | status')
    def open(self):
        from .library import entries as user_entries
        self.entries=user_entries()+entries(DEFAULT_ROOT)
        self.open_pending=True
        return 'Opening model catalog'
    def spawn(self,key='bird'):
        if self.busy:raise RuntimeError('Destroy the current model first')
        if key in ('ayane','2b'):
            from .library import prepare_static
            self.future=self.pool.submit(prepare_static,key)
            self.last=dict(state='preparing',asset=key)
            return self.last
        from .catalog import TARGETS
        identity=TARGETS.get(key,key)
        if not any(r['id']==identity and r['available'] for r in self.entries):raise ValueError('Catalog entry unavailable')
        cache=Path(__file__).resolve().parent/'cache'/hashlib.sha256(identity.encode()).hexdigest()[:20]
        self.future=self.pool.submit(prepare,DEFAULT_ROOT,identity,cache)
        self.last=dict(state='preparing',asset=identity)
        return self.last
    def replacement_preview(self):
        if self.busy:raise RuntimeError('Destroy the current model first')
        from .character import resolve
        self._prepare_rig(resolve(self.session.pid))
        return self.last
    def _prepare_rig(self,rig):
        from .character import collect
        from .skin import prepare_skin
        self.rig=rig;self.driver_index=rig['driver']
        bones=collect(self.session,self.driver_index)
        cache=Path(__file__).resolve().parent/'cache'/'character-replacement'
        from .custom_skin import prepare_custom_skin
        from .library import package
        self.future=self.pool.submit(prepare_custom_skin,cache/self.replacement_asset,bones,package(self.replacement_asset))
        self.last=dict(state='preparing',asset=self.replacement_asset+' replacement',character=rig['character'])
    def select_replacement(self,model):
        if model not in ('2b','ayane'):raise ValueError('Choose 2b or ayane')
        from .library import package
        if not (package(model)/'manifest.json').is_file():raise ValueError('Download and convert this model first; see README')
        self.destroy();self.replacement_asset=model
        self.replacement_profile=13
        return self.replacement_enable()
    def replacement_material(self,profile):
        if type(profile) is not int or profile not in (2,10,11,13):raise ValueError("Unsupported replacement material candidate")
        self.destroy();self.replacement_profile=profile
        return self.replacement_enable()
    def replacement_enable(self):
        if not self.busy:
            result=self.replacement_preview();self.follow_character=True;return result
        if not self.skin_path or self.last.get('state')!='rig-preview':raise RuntimeError('Start and inspect replacement preview first')
        from .character import resolve
        if resolve(self.session.pid)['token']!=self.rig['token']:raise RuntimeError('Character changed; refresh the preview')
        self.model.hide_driver();self.follow_character=True;self.last['state']='replacement';return self.status()
    def _bind_rig(self):
        from .character import resolve
        if resolve(self.session.pid)['token']!=self.rig['token']:
            raise RuntimeError('Character changed during preparation; retrying')
        self.model.bind_skin(self.skin_path,self.driver_index,self.rig['visuals'],self.rig.get('combat_manager'))
        self.last['state']='rig-preview';self.last['character']=self.rig['character']
        if self.follow_character:self.model.hide_driver();self.last['state']='replacement'
    def shader_samples(self,batch=1):
        if type(batch)is not int or not 1<=batch<=4:raise ValueError('Choose batch 1..4')
        self.destroy()
        from .lit_samples import prepare_lit_samples
        cache=Path(__file__).resolve().parent/'cache'/'shader-comparison'
        self.future=self.pool.submit(prepare_lit_samples,DEFAULT_ROOT,cache,batch)
        self.last=dict(state='preparing',asset='shader-comparison')
        return self.last
    def _begin(self,data):
        self.sample_mapping=data.get("sample_mapping",[])
        self.skin_path=data.get("skin")
        self.scope=SessionScope(self.session,lease_owner='CatalogModels');self.model=Tetrahedron(self.scope)
        try:
            from expedition33.assets import load_asset
            from expedition33.procedural_mesh import MATERIAL_PROFILES
            # Converted models declare materials on each section, not only in
            # the optional top-level list. Load them before taking the catalog
            # snapshot so previews also work in maps that never used them.
            profiles=list(data.get('material_profiles',()))
            profiles.extend((getattr(self,'replacement_profile',2) if self.skin_path else row.get('profile',2))
                            for row in data['sections'] if row.get('texture'))
            for profile in dict.fromkeys(profiles):
                load_asset(self.scope,MATERIAL_PROFILES[profile][0])
            self.model.spawn(ground=True)
            names=('Widget3DPassThrough_Opaque','SetVectorParameterValue','DefaultImagePlateMaterial','Default__KismetStringLibrary','Default__KismetRenderingLibrary','ImportFileAsTexture2D',
                   'CreateDynamicMaterialInstance','SetTextureParameterValue','K2_GetTextureParameterValue','Conv_StringToName','Texture2D','Texture','MaterialInterface','MaterialInstanceDynamic')
            from expedition33.procedural_mesh import MATERIAL_PROFILES
            names=names+tuple(path.rsplit('.',1)[1] for path,_,_ in MATERIAL_PROFILES)
            self.catalog=capture_matching(self.session.pid,names=tuple(dict.fromkeys(names)))
            self.pending=list(enumerate(data['sections']))
            self.last=dict(state='uploading',asset=data['id'],sections=len(self.pending),uploaded=0,vertices=data['vertices'],batch=data.get('batch'),samples=[r['id'] for r in self.sample_mapping])
            return self.last
        except BaseException:
            self._retire();raise
    def poll(self):
        if self.session is None or self._world_retiring:return
        if self.open_pending:
            self.open_pending=False
            if self.shared.menu is not None and self.shared.menu.panel.state=='open':self.shared.close_menu()
            self.native.open()
        if time.monotonic()<self.next_poll:return
        self.next_poll=time.monotonic()+(.05 if self.pending or self.future else .5)
        if self.future and self.future.done():
            future=self.future;self.future=None
            try:
                data=future.result()
                if data.get('skin'):self.prepared_skin=data
                if self.model:
                    self.skin_path=data['skin'];self._bind_rig()
                else:self._begin(data)
            except Exception as error:
                self._retire();self.last=dict(state='waiting-for-character' if self.follow_character else 'failed',error=str(error))
        if self.model:
            if self.model.status()['state']==0:
                self._retire();self.last=dict(state='retired-on-travel')
            elif self.pending:
                index,row=self.pending[0]
                try:
                    self.model.upload_section(row['mesh'],index)
                    if row['texture']:self.model.set_image_plate_texture(self.catalog,row['texture'],index,profile=getattr(self,'replacement_profile',2) if self.skin_path else row.get('profile',2),tint_gain=row.get('tint_gain',0))
                    self.pending.pop(0);self.last['uploaded']=index+1
                    if not self.pending:
                        self.last['state']='spawned'
                        if self.skin_path:
                            self._bind_rig()
                except Exception as error:
                    message=str(error);self._retire();self.last=dict(state='failed',error=message)
        if self.follow_character and self.rig_future and self.rig_future.done():
            check=self.rig_future;self.rig_future=None
            try:
                rig=check.result()
                if not self.model or not self.rig or rig['token']!=self.rig['token']:
                    if self.model:self.model.unbind_skin()
                    self._prepare_rig(rig)
            except Exception as error:
                self._retire();self.last=dict(state='waiting-for-character',error=str(error))
            self.next_character_check=time.monotonic()+(.2 if self.rig and self.rig.get('combat_manager') else 1)
        if self.follow_character and not self.model and not self.future and not self.pending and not self.rig_future and time.monotonic()>=self.next_character_check:
            from .character import resolve
            self.rig_future=self.pool.submit(resolve,self.session.pid,self.session._session._transport._executable)
        summary=self.summary()
        if summary!=self.painted and self.native.menu is not None and self.native.menu.panel.state=='open':
            self.shared.refresh();self.painted=summary
    def shader_nearest(self):
        if not self.model or not getattr(self,'sample_mapping',None):raise RuntimeError('No comparison grid')
        from expedition33.procedural_mesh import discover
        from expedition33.catalog import capture_selected
        from expedition33.values import read_values_with_references
        pawn=discover(self.session.pid)[0]
        c=capture_selected(self.session.pid,[(pawn.index,pawn.serial,pawn.address)])
        v,c=read_values_with_references(c,pawn,fields=('RootComponent',))
        root=next(x for k,x in v.values.items() if k[1]=='RootComponent')
        v,c=read_values_with_references(c,root,fields=('RelativeLocation','AttachParent'))
        values={k[1]:x for k,x in v.values.items()}
        if values.get('AttachParent') is not None:raise RuntimeError('Dismount before identifying a sample')
        pos=values['RelativeLocation']
        if hasattr(pos,'fields'):pos=pos.fields
        if hasattr(pos,'keys'):pos=[pos[k] for k in ('X','Y','Z')]
        elif hasattr(pos,'x'):pos=[pos.x,pos.y,pos.z]
        origin=self.model.status()['position']
        distances=[(sum((pos[i]-origin[i]-r['local_center'][i])**2 for i in (0,1))**.5,r) for r in self.sample_mapping]
        distance,row=min(distances,key=lambda pair:pair[0])
        return dict(candidate=row['id'],distance_cm=round(distance,1),path=row['path'],parameter=row['parameter'],row=row['row'],column=row['column'])
    def status(self):return dict(self.last,native=self.model.status() if self.model else None)
    def _retire(self):
        if self.future:self.future.cancel();self.future=None
        if self.scope:self.scope.close()
        self.scope=None;self.model=None;self.pending=[];self.catalog=None;self.skin_path=None;self.last=dict(state='destroyed');return self.last
    def destroy(self):
        if self.rig_future:self.rig_future.cancel();self.rig_future=None
        self.follow_character=False;self.rig=None;self.prepared_skin=None
        return self._retire()
    def disable(self):
        self.open_pending=False
        if self.native:self.native.close()
        self.destroy()
        if self.pool:self.pool.shutdown(wait=True,cancel_futures=True)
        self.session=None;self.pool=None;self.native=None;self.shared=None

    def revoke_world(self,context):
        self._world_retiring=True;self._retirement_token=context.previous_token
        self.open_pending=False;self.follow_character=False;self.pending=[]
        self._retirement_futures=[future for future in (self.future,self.rig_future) if future is not None]
        for future in self._retirement_futures:future.cancel()

    def begin_world_retirement(self,context):
        return self.poll_world_retirement(context)

    def poll_world_retirement(self,context):
        if context.previous_token!=self._retirement_token:return 'unknown'
        # Preparation workers do local conversion or read-only observation.
        # Discard results only once they settle; never upload into a new world.
        if any(not future.done() for future in self._retirement_futures):return 'pending'
        if self.model is not None:
            if not self.model.retire_world():return 'pending'
            self.model=None
        if self.scope is not None:
            from expedition33._retired_tracking import close_lease_only_scope
            if not close_lease_only_scope(self.scope):return 'pending'
            self.scope=None
        if self.pool is not None:self.pool.shutdown(wait=False,cancel_futures=True)
        self.future=self.rig_future=self.pool=None;self._retirement_futures=[]
        self.catalog=self.rig=self.prepared_skin=self.skin_path=self.driver_index=None
        self.native=self.shared=self.session=None
        self.last=dict(state='world-retired')
        return 'ack'
