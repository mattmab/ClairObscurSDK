"""Public entry point for SDK-owned story playback, without editor UI."""

def _provider(session):
    """Install the bundled runtime lazily; importing does not touch the game."""
    provider=getattr(session,'_scene_pack_provider',None)
    if provider is None:
        from .scene_runtime.runtime import Runtime
        from .scene_runtime.scene import validate
        provider=(Runtime,validate)
        session._scene_pack_provider=provider
    return provider


def prepare_provider(session):
    """Import the pure Python scene catalog during loading, without engine I/O.

    Actor spawning and asset loads retain their existing per-scene owners. This
    avoids importing the full catalog just after initial control is released.
    """
    _provider(session)


def register_provider(session,factory,validate):
    if not callable(factory) or not callable(validate):raise TypeError('Scene playback provider callbacks required')
    previous=getattr(session,'_scene_pack_provider',None)
    if previous is not None and previous!=(factory,validate):
        # A reloaded module may replace callbacks only with no live playback.
        if any(not owner.closed for owner in getattr(session,'_scene_pack_playbacks',())):raise RuntimeError('Scene pack playback still owns the previous provider')
    session._scene_pack_provider=(factory,validate)
    background=getattr(session,'_scene_pack_background',set())
    for key,document in getattr(session,'_scene_pack_documents',{}).items():
        if key not in background:_warm(session,document)

def register_document(session,key,document,*,warm=True):
    """Declare portable content during loading; never spawn actors or play it."""
    documents=getattr(session,'_scene_pack_documents',None)
    if documents is None:documents={};session._scene_pack_documents=documents
    if key not in documents and len(documents)>=16:raise ValueError('Scene pack document count bound')
    documents[key]=document
    background=getattr(session,'_scene_pack_background',None)
    if background is None:background=set();session._scene_pack_background=background
    if warm:background.discard(key)
    else:background.add(key)
    if warm and getattr(session,'_scene_pack_provider',None) is not None:_warm(session,document)

def _warm(session,document):
    from ._reader import shared_operation
    with shared_operation(session.pid,_executable=session._transport._executable):return _warm_in_operation(session,document)

def _warm_in_operation(session,document):
    factory,validate=_provider(session)
    document=validate(document);paths=factory.required_assets(document)[3]
    if len(paths)>128:raise ValueError('Scene pack asset count bound')
    resources=getattr(session,'_scene_pack_resources',None)
    if resources is None:
        from .story_narrative_resources import NarrativeResources
        from ._metadata_stabilization import process_preparation
        resources=NarrativeResources(process_preparation(session).scope);session._scene_pack_resources=resources
    assets=getattr(session,'_scene_pack_assets',None)
    if assets is None:assets={};session._scene_pack_assets=assets
    for path in paths:assets[path]=resources.load(path)

def warm_step(session,key,*,budget_ms=15.,max_assets=2):
    """Warm a declared scene incrementally after essential gameplay is ready.

    A single engine load cannot be preempted. The time budget is checked between
    loads and max_assets also bounds work when all resources are already cached.
    """
    import time
    from ._reader import shared_operation
    if not 1<=budget_ms<=50 or type(max_assets) is not int or not 1<=max_assets<=8:raise ValueError('Scene warm-up budget')
    provider=_provider(session)
    documents=getattr(session,'_scene_pack_documents',{})
    if key not in documents:raise KeyError(key)
    with shared_operation(session.pid,_executable=session._transport._executable):
        factory,validate=provider;document=validate(documents[key]);paths=factory.required_assets(document)[3]
        if len(paths)>128:raise ValueError('Scene pack asset count bound')
        resources=getattr(session,'_scene_pack_resources',None)
        if resources is None:
            from .story_narrative_resources import NarrativeResources
            from ._metadata_stabilization import process_preparation
            resources=NarrativeResources(process_preparation(session).scope);session._scene_pack_resources=resources
        assets=getattr(session,'_scene_pack_assets',None)
        if assets is None:assets={};session._scene_pack_assets=assets
        start=time.perf_counter();count=0
        for path in paths:
            if path in assets:continue
            assets[path]=resources.load(path);count+=1
            if count>=max_assets or (time.perf_counter()-start)*1000>=budget_ms:break
        return all(path in assets for path in paths)

class Playback:
    @property
    def _closed(self):return self.closed

    def __init__(self,scope,document,*,start_at=0.):
        scope._check();session=scope._session
        provider=_provider(session)
        self.document=provider[1](document)
        if type(start_at) not in (int,float) or not 0<=start_at<self.document['duration']:raise ValueError('Scene start time outside document')
        self.start_at=float(start_at);self.runtime=provider[0]();self.runtime.session=scope
        self.started=False;self.closed=False;self.captions=None;self.input_panel=None
        owners=getattr(session,'_scene_pack_playbacks',None)
        if owners is None:owners=[];session._scene_pack_playbacks=owners
        owners.append(self);scope._reference_owners.append(self)
    def start(self):
        if self.closed or self.started:raise RuntimeError('Scene pack playback is one-shot')
        self.started=True
        from ._reader import shared_operation
        scope=self.runtime.session
        with shared_operation(scope.pid,_executable=scope._session._transport._executable):
            try:
                if getattr(scope._session._transport,'story_scene_controls_protocol',0)!=1:raise RuntimeError('Update the native SDK for story cinematic input controls')
                from .cinematic_context_panel import CinematicContextPanel
                self.input_panel=CinematicContextPanel(scope);self.input_panel.build();self.input_panel.open()
                from .scene_captions import SceneCaptions
                self.captions=SceneCaptions(scope);self.captions.build()
                result=self.runtime.start(self.document,start_at=self.start_at,story_controls=True)
                if self.captions is not None:self.captions.show();self.captions.update(self.document.get('captions',()),self.start_at)
                return result
            except BaseException:
                # An uncertain native owner must retain the input gate until its
                # established teardown path has released the scene.
                if not self.runtime.uncertain and self.runtime.scope is None:self._close_ui()
                raise
    def _close_ui(self):
        if self.captions is not None:
            if not self.captions.close():return False
            self.captions=None
        if self.input_panel is not None:
            if not self.input_panel.close():return False
            self.input_panel=None
        return True
    def poll(self):
        if self.closed:return 'finished'
        if not self.started:return 'prepared'
        self.runtime.poll()
        status=self.runtime.status()
        if self.captions is not None:self.captions.update(self.document.get('captions',()),status.get('elapsed',0.),paused=status.get('paused',False),skip_progress=status.get('skip_progress',0.))
        if status.get('uncertain'):raise RuntimeError('Scene playback outcome is uncertain')
        if status.get('state')=='finished' and self.runtime.scope is None:
            if not self._close_ui():return 'cleanup_pending'
            self.closed=True;return 'finished'
        if status.get('state') in ('failed','interrupted'):raise RuntimeError('Story cinematic '+status['state'])
        return status.get('state','playing')
    def close(self):
        if self.closed:return True
        if self.started:
            self.runtime.stop()
            if self.runtime.scope is not None:return False
        if not self._close_ui():return False
        self.closed=True;return True
    def retire_world(self):
        if self.closed:return 'ack'
        result=self.runtime.retire_world() if self.started else 'ack'
        if result=='ack':
            if self.input_panel is not None:
                result=self.input_panel.retire_world(native_retirement_ack=True)
                if result!='ack':return result
                self.input_panel=None
            if self.captions is not None:self.captions.close();self.captions=None
            self.closed=True
        return result
