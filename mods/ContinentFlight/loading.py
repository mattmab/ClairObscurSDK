"""Read-only flight discovery and schema preparation during save loading."""
import time
import logging
from concurrent.futures import ThreadPoolExecutor


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


def prepare_snapshot(pid,static=None):
    from expedition33._reader import ReadBatch
    from expedition33._planning_metadata import MetadataObservations
    from expedition33.invocation import prepare_call
    from . import discover_snapshot, flight_calls
    with ReadBatch(pid):
        snapshot=discover_snapshot(pid)
        catalog,pawn,movement=snapshot
        metadata=MetadataObservations()
        if static is not None:metadata._entries=dict(static._entries)
        def prepare(target,function,**arguments):
            return prepare_call(catalog,target,function,arguments,
                pod_values=True,enum_values=True,_metadata=metadata)
        flight_calls(catalog,pawn,movement,prepare)
        return snapshot,metadata


class LoadingFlight:
    def __init__(self,mod,session):
        self.mod=mod;self.session=session;self.pid=session.pid;self.context=None
        self.worker=None;self.future=None;self.signature=None
        self.next_attempt=0.;self.closed=False;self.failed=False;self.reader=None

    def prepare(self,context):
        self.context=context
        self.static=prepare_static(self.pid,self.session)
        self.mod._loading_static=self.static
        self.mod._loading_owner=self
        self._prepare_reader()

    def _prepare_reader(self):
        if self.reader is None and self.mod.reader is None:
            from expedition33._reader import ReadBatch
            self.reader=ReadBatch(self.pid,share=True)
            with self.reader.bind():pass # Process validation only; no world observations.

    def observe_title(self,context):
        self._prepare_reader()

    def take_reader(self):
        reader,self.reader=self.reader,None
        return reader

    def bind(self,context,*,preparing=False):
        if self.closed or self.failed:return
        if self.context.signature!=context.signature:
            self.mod._loading_flight=None;self.context=context
        if self.future is not None:
            if not self.future.done():return
            future,self.future=self.future,None
            try:result=future.result()
            except Exception as error:
                # Discovery is read-only. A loading pawn may not exist yet;
                # no engine mutation or native invocation has been attempted.
                from . import ExplorationNotReady
                from expedition33 import RuntimeQueryError
                if not (isinstance(error,ExplorationNotReady) or
                        isinstance(error,RuntimeQueryError) and any(code in str(error) for code in
                            ('READ_FAILED','Object identity changed','SELECTED_DEPENDENCY_CHANGED'))):
                    self.failed=True
                    logging.getLogger(__name__).exception('Flight loading preparation unavailable')
                result=None
            if self.signature==context.signature and result is not None:
                self.mod._loading_flight=(context.signature,result)
        if self.failed or self.mod._loading_flight is not None or time.monotonic()<self.next_attempt:return
        self.next_attempt=time.monotonic()+.25
        if self.worker is None:self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='flight-loading')
        self.signature=context.signature
        self.future=self.worker.submit(prepare_snapshot,self.pid,self.static)

    def close(self):
        self.closed=True;self.mod._loading_flight=None
        if self.reader is not None:self.reader.close();self.reader=None
        if self.future is not None:self.future.cancel()
        if self.worker is not None:self.worker.shutdown(wait=False,cancel_futures=True)
