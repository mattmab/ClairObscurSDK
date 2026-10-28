"""Background read-only authored graph observation.

The caller retains the source asset on its own SessionScope and checks its
world epoch before accepting a result.  This object receives only process and
object identity values; it never receives or manipulates a game session,
lease, widget, controller or mutable workspace.
"""
import threading
import time
import json
import re
from dataclasses import dataclass

from .. import RuntimeQueryError
from .._reader import ReadBatch, ReadCancelled
from ..catalog import capture_selected
from ..values import read_values_with_references, read_values_many_with_references
from .authored_source import DEFAULT_GRAPH_NODES, MAX_GRAPH_NODES, _inspect_graph_steps


@dataclass(frozen=True)
class ImportSnapshot:
    state: str
    nodes: int
    graph: object = None
    timing: object = None
    error: str = ''


def _partial_read_failure(error):
    """Recognize only the native reader's specific partial-copy response."""
    prefix='Read worker rejected query: '
    if type(error) is not RuntimeQueryError or not str(error).startswith(prefix):return False
    lines=str(error)[len(prefix):].splitlines()
    if not lines:return False
    try:row=json.loads(lines[-1])
    except (ValueError,TypeError):return False
    return (type(row) is dict and set(row)=={'event','message'} and row['event']=='error'
        and type(row['message']) is str
        and re.fullmatch(r'READ_FAILED address=0x[0-9a-fA-F]+(?: size=[0-9]+ received=[0-9]+ '
                         r'region_state=0x[0-9a-fA-F]+ region_protect=0x[0-9a-fA-F]+)? win32=299',
                         row['message']) is not None)


class AuthoredImportJob:
    """Own a single worker and publish only after its reader is closed.

    ``cancel`` only signals.  ``close`` never waits for the worker and returns
    false while the caller must retain the source lease and poll again.  A
    cancelled job never returns a graph, even if work raced with cancellation.
    """
    def __init__(self,pid,identity,*,executable=None,max_nodes=DEFAULT_GRAPH_NODES):
        if type(pid) is not int or not 0<pid<=0xffffffff:raise ValueError('Expected a process ID')
        if (type(identity) is not tuple or len(identity)!=3 or any(type(v) is not int for v in identity)
                or not 0<=identity[0]<100000000 or not -0x80000000<=identity[1]<=0x7fffffff
                or not 0x10000<=identity[2]<=0x7fffffffffff):
            raise ValueError('Expected an exact retained source identity')
        if type(max_nodes) is not int or not 1<=max_nodes<=MAX_GRAPH_NODES:raise ValueError('Invalid authored graph limit')
        self.pid=pid;self.identity=identity;self.executable=executable;self.max_nodes=max_nodes
        self._cancel=threading.Event();self._lock=threading.Lock();self._thread=None
        self._nodes=0;self._result=None

    def start(self):
        with self._lock:
            if self._thread is not None:raise RuntimeError('Import job cannot be started again')
            if self._cancel.is_set():raise RuntimeError('Cancelled import job cannot start')
            self._thread=threading.Thread(target=self._run,name='e33-authored-import',daemon=True)
            self._thread.start()
        return self

    def cancel(self):
        self._cancel.set()

    def close(self):
        self.cancel()
        thread=self._thread
        return thread is None or not thread.is_alive()

    def poll(self):
        thread=self._thread
        if thread is None or thread.is_alive():
            with self._lock:nodes=self._nodes
            if thread is None:return ImportSnapshot('cancelled' if self._cancel.is_set() else 'new',nodes)
            return ImportSnapshot('cancelling' if self._cancel.is_set() else 'running',nodes)
        # Read the result after observing thread exit.  Reading it before the
        # liveness check can race with the worker publishing and exiting.
        with self._lock:nodes=self._nodes;result=self._result
        if self._cancel.is_set():return ImportSnapshot('cancelled',nodes)
        if result is None:return ImportSnapshot('failed',nodes,error='Import worker exited without a result')
        return result

    def _run(self):
        started=time.perf_counter();result=None
        try:
            # ContextVar binding and reader IO belong to this thread.  No
            # fallback reader or retained SessionScope crosses the boundary.
            for attempt in range(2):
                metrics={};transient=None;read_failure=None
                if self._cancel.is_set():raise ReadCancelled('Authored import cancelled')
                line_options=({'_line_limit':16*1024*1024}
                    if getattr(ReadBatch,'supports_source_line_limit',False) is True else {})
                with ReadBatch(self.pid,share=True,_executable=self.executable,_cancel=self._cancel,**line_options):
                    try:
                        try:catalog=capture_selected(self.pid,(self.identity,))
                        except RuntimeQueryError as error:
                            read_failure=error;raise
                        asset=catalog.by_index[self.identity[0]]
                        if (asset.index,asset.serial,asset.address)!=self.identity or asset.class_name!='LevelSequence':
                            raise ValueError('Retained sequence identity changed')
                        steps=_inspect_graph_steps(catalog,asset,read_values_with_references,
                            max_nodes=self.max_nodes,read_many=read_values_many_with_references,metrics=metrics)
                        try:
                            while True:
                                if self._cancel.is_set():raise ReadCancelled('Authored import cancelled')
                                try:nodes=next(steps)
                                except StopIteration as done:
                                    graph=done.value;break
                                except RuntimeQueryError as error:
                                    read_failure=error;raise
                                if nodes==1 or nodes%64==0:
                                    with self._lock:self._nodes=nodes
                        finally:steps.close()
                        if self._cancel.is_set():raise ReadCancelled('Authored import cancelled')
                    except ReadCancelled:
                        raise
                    except RuntimeQueryError as error:
                        if attempt or error is not read_failure or not _partial_read_failure(error):raise
                        transient=error
                # The failed reader is fully closed on this thread before the
                # complete, read-only operation is retried with fresh identity
                # validation. Never retain its partial graph or timings.
                if transient is None:break
                if self._cancel.is_set():raise ReadCancelled('Authored import cancelled')
                with self._lock:self._nodes=0
            if attempt:metrics['read_retries']=attempt
            metrics['total_ms']=(time.perf_counter()-started)*1000
            result=ImportSnapshot('completed',len(graph['nodes']),graph,dict(metrics))
        except ReadCancelled:
            result=ImportSnapshot('cancelled',self._nodes)
        except BaseException as error:
            result=ImportSnapshot('failed',self._nodes,error=type(error).__name__+': '+str(error))
        # Reaching here means the owner-thread reader cleanup has completed.
        with self._lock:self._result=result
