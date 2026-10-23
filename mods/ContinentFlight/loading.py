"""Read-only flight discovery and schema preparation during save loading."""
from expedition33.admission_monitor import ReadOnlyAdmissionMonitor


def prepare_static(pid,session=None):
    from expedition33._reader import ReadBatch
    from expedition33.catalog import capture_matching
    from expedition33.reflection import describe
    from expedition33.enums import describe_enums
    from expedition33._planning_metadata import MetadataObservations
    from . import FLIGHT_FUNCTIONS
    with ReadBatch(pid):
        discover=lambda:capture_matching(pid,names=(*FLIGHT_FUNCTIONS,'Vector','EMovementMode'))
        if session is None:catalog=discover()
        else:
            # Stabilize only admitted Script metadata, before saving copied
            # schemas. Later native target retention must not change a zero
            # descriptor serial and force all schema reads back into activation.
            from expedition33._metadata_stabilization import prepare_discovery
            catalog,_=prepare_discovery(session,discover)
        metadata=MetadataObservations()
        functions=[o for o in catalog.objects if o.class_name=='Function'
            and o.name in FLIGHT_FUNCTIONS and catalog.path_name(o).startswith('/Script/Engine.')]
        structs=[o for o in catalog.objects if o.class_name=='ScriptStruct'
            and catalog.path_name(o)=='/Script/CoreUObject.Vector']
        enums=[o for o in catalog.objects if o.class_name=='Enum'
            and catalog.path_name(o)=='/Script/Engine.EMovementMode']
        metadata.read('struct',catalog,(*functions,*structs),describe)
        metadata.read('enum',catalog,enums,describe_enums)
        return metadata


def prepare_snapshot(pid,static=None,cached=None):
    from expedition33._reader import ReadBatch
    from expedition33._planning_metadata import MetadataObservations
    from expedition33.invocation import prepare_call
    from . import discover_snapshot, flight_calls
    with ReadBatch(pid):
        snapshot=discover_snapshot(pid,cached) if cached is not None else discover_snapshot(pid)
        catalog,pawn,movement=snapshot
        metadata=MetadataObservations()
        if static is not None:metadata._entries=dict(static._entries)
        def prepare(target,function,**arguments):
            return prepare_call(catalog,target,function,arguments,
                pod_values=True,enum_values=True,_metadata=metadata)
        flight_calls(catalog,pawn,movement,prepare)
        return snapshot,metadata


class FlightObserver:
    """Worker-owned copied discovery, independent of owner-thread UI builds."""
    def __init__(self,pid,static):
        from expedition33._reader import ReadBatch
        self.pid=pid;self.static=static;self.catalog=None
        self.reader=ReadBatch(pid,share=True)

    def observe(self):
        from . import ExplorationNotReady
        with self.reader.bind():
            try:
                result=prepare_snapshot(self.pid,self.static,self.catalog)
            except ExplorationNotReady:
                self.catalog=None
                return None
            self.catalog=result[0][0]
            return result

    def close(self):
        self.reader.close();self.catalog=None


class LoadingFlight:
    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.pid=session.pid;self.context=None
        self.monitor=None;self.closed=False;self.reader=None;self._observing=False

    def prepare(self,context):
        self.context=context
        self.static=prepare_static(self.pid,self.session)
        self.mod._loading_static=self.static
        self.mod._loading_owner=self
        self._prepare_reader()
        self._ensure_monitor()

    def _ensure_monitor(self):
        if self._observing:return True
        if self.monitor is not None:
            if not self.monitor.close(timeout=0.):return False
            self.monitor=None
        # Capture only pid/copied metadata: no Session or scopes on the worker.
        pid,static=self.pid,self.static
        self.monitor=ReadOnlyAdmissionMonitor(lambda:FlightObserver(pid,static),interval=.1,max_age=1.)
        self._observing=True
        return True

    def activated(self):
        # Activation already consumed the copied result. Stop sampling without
        # waiting on a read-only query; retain its owner until cleanup ACKs.
        self._observing=False
        if self.monitor is not None and self.monitor.close(timeout=0.):self.monitor=None

    def _prepare_reader(self):
        if self.reader is None and self.mod.reader is None:
            from expedition33._reader import ReadBatch,active_reader
            self.reader=ReadBatch(self.pid,share=True)
            # A menu callback can already own shared IO. Store our unstarted
            # owner there; the mod borrows that operation and binds its own
            # worker later, without retaining or closing the caller's reader.
            if active_reader() is None:
                with self.reader.bind():pass

    def observe_title(self,context):
        self.context=context;self.mod._loading_flight=None
        self._prepare_reader()
        if self.mod.session is None or self.mod.disabled:self._ensure_monitor()

    def take_reader(self):
        reader,self.reader=self.reader,None
        return reader

    @staticmethod
    def matches(context,result):
        from expedition33.cinematics.history import identity
        catalog,pawn,_=result[0]
        pc=catalog.by_index.get(context.controller[1])
        if pc is None or identity(pc)!=context.controller:return False
        worlds=[o for o in catalog.outer_chain(pawn) if o.class_name=='World']
        pc_worlds=[o for o in catalog.outer_chain(pc) if o.class_name=='World']
        return (len(worlds)==len(pc_worlds)==1 and
            identity(worlds[0])==identity(pc_worlds[0])==context.world)

    def bind(self,context,*,preparing=False):
        if self.closed:return
        self.context=context;self.mod._loading_flight=None
        if self.mod.session is not None and not self.mod.disabled:return
        self._prepare_reader()
        if not self._ensure_monitor():return
        observation=self.monitor.snapshot() if self.monitor is not None else None
        result=observation.admission if observation is not None else None
        if result is not None and self.matches(context,result):
            self.mod._loading_flight=(context.signature,result)

    def take_snapshot(self):
        # Harvest the latest worker result at enable, even if UI construction
        # kept the owner from polling the loading coordinator in the meantime.
        if self.context is not None:self.bind(self.context)
        result,self.mod._loading_flight=self.mod._loading_flight,None
        return result

    def close(self):
        self.closed=True;self.mod._loading_flight=None
        if self.reader is not None:self.reader.close();self.reader=None
        if self.monitor is not None and self.monitor.close(timeout=2.):self.monitor=None
