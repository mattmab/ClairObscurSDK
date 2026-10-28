"""Scene Editor's retained game-sequence source workspace.

Import keeps the original asset alive for later owned preview/track conversion.
No Play, game action, Blueprint construction or asset mutation occurs here.
"""
import copy,json,uuid,time
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33._retired_tracking import close_lease_only_scope
from expedition33.cinematics.authored_source import inspect_graph
from expedition33.cinematics.original_game_action import controller_context
from expedition33.cinematics import authored_timeline


class AuthoredWorkspace:
    def __init__(self,*,background_import=False):
        if type(background_import) is not bool:raise ValueError('Background import flag must be Boolean')
        self.background_import=background_import
        self.scope=None;self.graph=None;self.source=None;self.context=None
        self.document=None;self.key=None;self.dirty=False
        self.loading=None;self.load_reader=None;self.loaded_nodes=0
        self.load_job=None;self.load_generation=0;self.load_job_generation=None
        self.load_job_token=None;self.load_job_identity=None;self.load_draft_guard=None;self.cleanup_pending=False
        self.recovered_signature=None
        self.load_timing={}
        self.store=authored_timeline.TimelineStore(Path(__file__).resolve().parents[2]/'settings/SceneEditor/authored')
        data=json.loads(Path(__file__).with_name('authored_catalog.json').read_text(encoding='utf8'))
        if data.get('version')!=1 or type(data.get('sequences')) is not list:
            raise ValueError('Unsupported authored sequence catalog')
        self.catalog=tuple(data['sequences'])
        paths=[row['path'] for row in self.catalog]
        if len(set(paths))!=len(paths):raise ValueError('Duplicate authored sequence source')
    def _context(self,session):
        # The retained selector is scoped to this import owner. Each call still
        # reads the current controller/world; no context or world handle is cached.
        capability=getattr(self.scope._session._transport,'stable_lease_protocol',0)
        if type(capability) is not int or capability!=1:
            return controller_context(session,project=True)
        from expedition33.cinematics.controller_anchor import context_observer
        return context_observer(self.scope)()
    def load(self,session,path):
        if path not in {row['path'] for row in self.catalog}:raise ValueError('Choose a game sequence from the library')
        self.preserve_draft()
        if not self.close():raise RuntimeError('Previous source release is pending')
        self.scope=SessionScope(session)
        try:
            self.context=self._context(session)
            graph=inspect_graph(self.scope,path)
            if self._context(session)!=self.context:
                raise RuntimeError('World changed while reading the source sequence')
            document=authored_timeline.create(graph,next(row['title'] for row in self.catalog if row['path']==path))
            self.graph=graph;self.source=path;self.document=document;self.key=None;self.dirty=True
            return graph
        except BaseException:
            self.close()
            raise
    def close(self):
        if self.load_job is not None:
            self.cancel_load()
            if not self.load_job.close():self.cleanup_pending=True;return False
            self.load_job=None;self.loading=None;self.load_job_generation=None
            self.load_job_token=None;self.load_job_identity=None;self.load_draft_guard=None
        if self.loading is not None:self.loading.close();self.loading=None
        if self.load_reader is not None:self.load_reader.close();self.load_reader=None
        if self.scope is not None:
            # This workspace owns asset leases only. Keep deferred release
            # reachable; never invoke old-world input/camera compensation.
            if not close_lease_only_scope(self.scope):self.cleanup_pending=True;return False
            self.scope=None
        self.cleanup_pending=False
        self.graph=self.source=self.context=None
        return True
    def cancel_load(self):
        """Invalidate outstanding results without blocking the owner thread."""
        if self.load_job is not None:
            self.load_generation+=1;self.load_job.cancel()
    def begin_load(self,session,path):
        if path not in {row['path'] for row in self.catalog}:raise ValueError('Choose a game sequence from the library')
        self.preserve_draft()
        if not self.close():raise RuntimeError('Previous source release is pending')
        from expedition33._reader import ReadBatch
        from expedition33.assets import load_asset
        from expedition33.catalog import capture_selected
        from expedition33.values import read_values_with_references,read_values_many_with_references
        from expedition33.cinematics.authored_source import _inspect_graph_steps
        self.scope=SessionScope(session)
        try:
            started=time.perf_counter();self.load_started=started;self.load_work=0.
            if self.background_import:
                from expedition33._reader import shared_operation
                from expedition33.cinematics.authored_import_job import AuthoredImportJob
                with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
                    if not self.scope._callbacks_ready():raise RuntimeError('World is not admitted for source import')
                    self.context=self._context(session)
                    asset=load_asset(self.scope,path).return_value
                    if asset is None or asset.class_name!='LevelSequence':raise ValueError('Expected a game LevelSequence')
                    if (self._context(session)!=self.context or
                            not self.scope._callbacks_ready()):raise RuntimeError('World changed before reading the source sequence')
                    identity=(asset.index,asset.serial,asset.address)
                self.load_timing=dict(asset_ms=(time.perf_counter()-started)*1000)
                self.load_generation+=1;self.load_job_generation=self.load_generation
                self.load_job_token=getattr(self.scope,'_world_binding_token',None);self.load_job_identity=identity
                self.load_draft_guard=(self.document,authored_timeline.digest(self.document) if self.document is not None else None,self.key,self.dirty)
                self.load_job=AuthoredImportJob(self.scope.pid,identity,executable=self.scope._session._transport._executable)
                self.loading=self.load_job;self.source=path;self.loaded_nodes=0
                self.load_job.start();self.load_work=time.perf_counter()-started
                return
            self.load_reader=ReadBatch(self.scope.pid,share=True,_executable=self.scope._session._transport._executable)
            self.load_reader.warm()
            with self._load_operation():
                self.context=self._context(session)
                asset=load_asset(self.scope,path).return_value
                if asset is None:raise ValueError('Expected a game LevelSequence')
                self.load_timing=dict(asset_ms=(time.perf_counter()-started)*1000)
                catalog=capture_selected(self.scope.pid,((asset.index,asset.serial,asset.address),))
                self.loading=_inspect_graph_steps(catalog,asset,read_values_with_references,read_many=read_values_many_with_references,metrics=self.load_timing)
            self.load_work=time.perf_counter()-started
            self.source=path;self.loaded_nodes=0
        except BaseException:
            self.close();raise
    def _load_operation(self):
        from expedition33._reader import active_reader,shared_operation
        if active_reader() is None:return self.load_reader.bind()
        return shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable)
    def poll_load(self,session,*,nodes=64):
        if self.loading is None:raise RuntimeError('No source import is pending')
        if type(nodes) is not int or not 1<=nodes<=128:raise ValueError('Invalid import work budget')
        try:
            started=time.perf_counter()
            if self.load_job is not None:
                return self._poll_background_load(session,started)
            with self._load_operation():
                for _ in range(nodes):
                    try:self.loaded_nodes=next(self.loading)
                    except StopIteration as done:
                        if self._context(session)!=self.context:raise RuntimeError('World changed while reading the source sequence')
                        graph=done.value
                        document=authored_timeline.create(graph,next(row['title'] for row in self.catalog if row['path']==self.source))
                        self.graph=graph;self.document=document;self.key=None;self.dirty=True;self.loading=None
                        break
            self.load_work=getattr(self,'load_work',0.)+time.perf_counter()-started
            if self.loading is None:
                self.load_timing.update(total_ms=(time.perf_counter()-getattr(self,'load_started',started))*1000,work_ms=self.load_work*1000)
                self.load_reader.close();self.load_reader=None;return True
            return False
        except BaseException:
            self.close();raise
    def _poll_background_load(self,session,started):
        job=self.load_job;result=job.poll();self.loaded_nodes=result.nodes
        if result.state in ('new','running','cancelling'):return False
        if result.state!='completed':raise RuntimeError(result.error or 'Source import cancelled')
        self._check_background_owner(session)
        graph=result.graph
        if type(graph) is not dict or graph.get('sequence')!=self.source:raise RuntimeError('Source import result does not match request')
        document=authored_timeline.create(graph,next(row['title'] for row in self.catalog if row['path']==self.source))
        # Document creation can take long enough for travel to occur; discard
        # the detached result unless the original owner is still admitted.
        self._check_background_owner(session)
        original,signature,key,dirty=self.load_draft_guard
        if (self.document is not original or self.key!=key or self.dirty!=dirty or
                (self.document is not None and authored_timeline.digest(self.document)!=signature)):
            raise RuntimeError('Existing draft changed while importing; it has been preserved')
        self.graph=graph;self.document=document;self.key=None;self.dirty=True
        self.load_timing.update(result.timing or {})
        worker_ms=self.load_timing.pop('total_ms',0.)
        self.load_timing.update(total_ms=(time.perf_counter()-self.load_started)*1000,worker_ms=worker_ms,
            work_ms=(getattr(self,'load_work',0.)+time.perf_counter()-started)*1000+worker_ms)
        self.loading=None;self.load_job=None;self.load_job_generation=None
        self.load_job_token=None;self.load_job_identity=None;self.load_draft_guard=None
        return True
    def _check_background_owner(self,session):
        from expedition33._reader import shared_operation
        from expedition33.catalog import capture_selected
        if self.load_job_generation!=self.load_generation:raise RuntimeError('Source import generation changed')
        self.scope._check()
        if (getattr(self.scope,'_world_binding_token',None)!=self.load_job_token or
                not self.scope._callbacks_ready()):raise RuntimeError('World changed while reading the source sequence')
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            if self._context(session)!=self.context:raise RuntimeError('World changed while reading the source sequence')
            catalog=capture_selected(self.scope.pid,(self.load_job_identity,))
            asset=catalog.by_index[self.load_job_identity[0]]
            if (asset.index,asset.serial,asset.address)!=self.load_job_identity or asset.class_name!='LevelSequence':
                raise RuntimeError('Retained source identity changed')
            # These are independent fresh observations, not an atomic snapshot.
            if (self._context(session)!=self.context or
                    not self.scope._callbacks_ready() or
                    getattr(self.scope,'_world_binding_token',None)!=self.load_job_token):
                raise RuntimeError('World changed while reading the source sequence')
        if self.load_job_generation!=self.load_generation:raise RuntimeError('Source import generation changed')
    def _require_import_idle(self):
        if self.loading is not None:raise ValueError('Wait for source import to finish or cancel it before editing')
    def retime(self,path,start,end):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.document=authored_timeline.retime(self.document,path,start,end);self.dirty=True
    def edit_key(self,section,path,index,*,at,value):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.document=authored_timeline.edit_key(self.document,section,path,index,at=at,value=value);self.dirty=True
    def reset_key(self,section,path,index):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.document=authored_timeline.reset_key(self.document,section,path,index);self.dirty=True
    def replace_cast(self,sequence,guid,profile):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.document=authored_timeline.replace_cast(self.document,sequence,guid,profile);self.dirty=True
    def place_cast(self,sequence,guid,offset,yaw):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.document=authored_timeline.place_cast(self.document,sequence,guid,offset,yaw);self.dirty=True
    def add_npc(self,profile):
        self._require_import_idle()
        key=uuid.uuid4().hex
        self.document=authored_timeline.set_npc(self.document,key,name=profile.title(),profile=profile,
            start=0,end=300,offset=[300.,200.,0.],yaw=0.)
        self.dirty=True;return key
    def edit_npc(self,key,field,value):
        self._require_import_idle()
        row=next(r for r in self.document.get('npc_tracks',[]) if r['id']==key)
        data=dict(name=row['name'],profile=row['profile'],start=row['start'],end=row['end'],
                  offset=list(row['placement']['offset']),yaw=row['placement']['yaw'])
        if field in ('name','profile','start','end','yaw'):data[field]=value
        elif field in ('X','Y','Z'):data['offset']['XYZ'.index(field)]=value
        else:raise ValueError('Unknown NPC track field')
        self.document=authored_timeline.set_npc(self.document,key,**data);self.dirty=True
    def remove_npc(self,key):
        self._require_import_idle()
        self.document=authored_timeline.remove_npc(self.document,key);self.dirty=True
    def place_scene(self,position):
        self._require_import_idle()
        self.document=authored_timeline.place_scene(self.document,position);self.dirty=True
    def rotate_scene(self,yaw):
        self._require_import_idle()
        self.document=authored_timeline.rotate_scene(self.document,yaw);self.dirty=True
    def save(self):
        self._require_import_idle()
        if self.document is None:raise ValueError('Load an authored timeline first')
        self.key=self.store.save(self.document,self.key);self.dirty=False;return self.key
    def channels(self,section):
        if self.document is None:return ()
        return authored_timeline.channels(self.document,section)
    def cast(self,query=''):
        if self.document is None:return ()
        from expedition33.cinematics.authored_cast import bindings
        query=query.casefold()
        return tuple(row for row in bindings(self.document['source'])
                     if query in (row['name']+' '+row['sequence']+' '+str(row['template'])).casefold())
    def load_saved(self,key):
        self._require_import_idle()
        document=self.store.read(key)
        self.preserve_draft()
        if not self.close():raise RuntimeError('Source release is pending')
        self.document=document;self.key=key;self.dirty=False
        # Browsing uses the validated saved snapshot, not live UObject handles.
        # Preview separately resolves and validates the actual source asset.
        self.graph=document['source'];self.source=self.graph['sequence']
    def preserve_draft(self):
        document=self.document
        if not self.dirty or document is None or not any(document.get(field) for field in ('section_edits','key_edits','cast_edits','npc_tracks','scene_position','scene_yaw')):return
        signature=authored_timeline.digest(document)
        if signature==self.recovered_signature:return
        recovery=copy.deepcopy(document);recovery['name']=document['name'][:148]+' (Recovered)'
        # A separate entry preserves the last explicit save as well as the draft.
        self.store.save(recovery)
        self.recovered_signature=signature
    def sections(self,query=''):
        if self.document is None:return ()
        rows=[];query=query.casefold()
        for path,node in self.document['source']['nodes'].items():
            if 'Section' not in node['class_name'] or query not in (path+' '+node['class_name']).casefold():continue
            try:start,end=authored_timeline.source_range(self.document,path)
            except ValueError:continue
            edit=self.document['section_edits'].get(path)
            if edit:start,end=edit['start'],edit['end']
            rows.append(dict(path=path,kind=node['class_name'].removeprefix('MovieScene'),start=start,end=end))
        return tuple(rows)
    def nodes(self,query=''):
        if self.graph is None:return ()
        query=query.casefold()
        return tuple((path,node) for path,node in self.graph['nodes'].items()
                     if not query or query in (path+' '+node['class_name']).casefold())
    def summary(self):
        if self.graph is None:return 'Select a game-authored sequence and choose Load source.'
        nodes=self.graph['nodes'];bindings=0;animations=0
        for node in nodes.values():
            if node['class_name']=='MovieScene':
                bindings+=node['fields'].get('ObjectBindings',{}).get('length',0)
            if node['class_name']=='MovieSceneSkeletalAnimationSection':animations+=1
        return (f'{len(nodes)} source objects | {bindings} bindings | {animations} animation sections\n'
                f'{len(self.graph["pending"])} objects beyond the read limit\n'
                'Edits save separately; previews leave the original source unchanged.')
