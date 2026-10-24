"""Start passive, copied map observations before gameplay activation."""
from expedition33.admission_monitor import ReadOnlyAdmissionMonitor
from .context_observer import ContextObserver


class LoadingContext:
    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.pid=session.pid;self.monitor=None;self.released=False

    def prepare(self,context):
        pid=self.pid
        self.monitor=ReadOnlyAdmissionMonitor(lambda:ContextObserver(pid),interval=.1,max_age=1.)
        self.mod._loading_context=self
        self._prepare_gate(context)

    def _prepare_gate(self,context):
        transport=getattr(self.session,'_transport',None)
        if getattr(transport,'map_load_gate_protocol',0)!=1:return
        gate=getattr(self.mod,'_native_gate',None)
        from expedition33.map_load_gate import MapLoadGate
        from .state import Assignments
        from expedition33.paths import settings_dir
        assignments=Assignments(settings_dir()/'WorldBuilderMapLoader'/'assignments.json')
        worlds=tuple(assignments.values)
        if gate is not None and not gate.closed:
            gate.update_worlds(worlds);return
        if worlds:self.mod._native_gate=MapLoadGate(self.session,context,worlds)

    def observe_title(self,context):
        registry=self.session._process_ui.registry
        enabled=registry._settings.get('e33.worldbuilder-map-loader').get('enabled') is True
        if enabled:self._prepare_gate(context)
        else:
            gate=getattr(self.mod,'_native_gate',None)
            if gate is not None and not gate.closed:gate.close()

    def bind(self,context,*,preparing=False):
        # Only the owner thread may hold the current possessed pawn. Begin
        # during loading rather than waiting for gameplay-mod activation.
        if self.released or self.mod.session is not None or context.kind!='world':return
        observation=self.monitor.snapshot() if self.monitor is not None else None
        value=observation.admission if observation is not None else None
        if value is None or not value.ready or tuple(context.world)[-3:]!=value.visit:return
        if not getattr(self.mod,'_startup_assignments',{}).get(value.world):return
        self.mod.hold_player(self.session,value.copy())

    def take(self):
        monitor,self.monitor=self.monitor,None
        self.released=True
        return monitor

    def close(self):
        if not self.released:self.mod.release_player()
        if self.monitor is not None and self.monitor.close(timeout=2.):self.monitor=None
