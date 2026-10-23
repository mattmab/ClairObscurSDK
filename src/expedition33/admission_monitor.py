"""Background copied readiness observations; never authorizes mutations."""
from dataclasses import dataclass
import math
import logging
import threading
import time


@dataclass(frozen=True)
class Observation:
    sequence: int
    completed_at: float
    admission: object


class ReadOnlyAdmissionMonitor:
    """The worker owns its observer/reader; the host reads one immutable slot.

    Supply a factory, never an existing thread-owned observer or Session.
    Results only schedule UI/activation work. Every mutation still needs its
    current authoritative gate. Stale/missing results mean uncertainty, never
    teardown. Failed read-only runtime queries discard the observer and publish
    uncertainty. A new observer samples on the next schedule; mutations are
    never performed or retried here. Programming/factory/cleanup failures remain
    visible rather than being mistaken for ordinary loading.
    """
    def __init__(self, factory, *, clock=time.monotonic, interval=.1, max_age=.5):
        if not callable(factory):raise TypeError('observer factory must be callable')
        for value in (interval,max_age):
            if type(value) not in (float,int) or not math.isfinite(value) or value<=0:
                raise ValueError('interval and max_age must be finite and positive')
        self._factory=factory;self._clock=clock;self._interval=interval;self._max_age=max_age
        self._owner=threading.get_ident();self._lock=threading.Lock()
        self._latest=None;self._failure=None;self._diagnostic=None;self._query_failures=0;self._stop=threading.Event()
        self.updated=threading.Event();self.closed=threading.Event()
        self._thread=threading.Thread(target=self._run,name='sdk-readiness',daemon=True)
        self._thread.start()

    def _run(self):
        observer=None
        phase='factory'
        try:
            observer=self._factory()
            sequence=0
            while not self._stop.is_set():
                phase='observe'
                try:
                    admission=observer.observe()
                except Exception as error:
                    from expedition33 import RuntimeQueryError, TargetExitedError
                    if not isinstance(error,RuntimeQueryError) or isinstance(error,TargetExitedError):raise
                    # No stale ready packet survives a failed sample. Closing
                    # and replacing the worker-owned reader also drops cached
                    # selectors; this is a new observation, not an operation retry.
                    with self._lock:
                        self._latest=None
                        self._query_failures=min(self._query_failures+1,0xffffffff)
                        self._diagnostic='observe:'+type(error).__name__
                        failures=self._query_failures
                    if failures & (failures-1)==0:
                        # Original read-only traceback stays in local host logs;
                        # only bounded class/counters cross the worker boundary.
                        logging.getLogger('expedition33.readiness.local').exception(
                            'Read-only readiness sample failed; local diagnostic, sample failures=%s',failures)
                    self.updated.set()
                    phase='close'
                    retired,observer=observer,None
                    retired.close()
                    if self._stop.wait(self._interval):break
                    phase='factory'
                    observer=self._factory()
                    continue
                sequence+=1
                result=Observation(sequence,self._clock(),admission)
                with self._lock:self._latest=result
                self.updated.set()
                if self._stop.wait(self._interval):break
        except BaseException as error:
            if phase=='observe':
                logging.getLogger('expedition33.readiness.local').exception(
                    'Read-only readiness observation failed; original local traceback')
            # Only the error class crosses threads; no configuration/error text.
            with self._lock:self._failure=phase+':'+type(error).__name__;self._latest=None
            self.updated.set()
        finally:
            if observer is not None:
                try:observer.close()
                except BaseException as error:
                    with self._lock:
                        if self._failure is None:self._failure='close:'+type(error).__name__
                        self._latest=None
            self.closed.set()

    def _check(self):
        if threading.get_ident()!=self._owner:
            raise RuntimeError('Readiness monitor requires its host owner thread')

    def snapshot(self):
        """O(1), no worker wait or engine query. None is uncertain status."""
        self._check()
        with self._lock:result,failure=self._latest,self._failure
        if failure is not None:
            raise RuntimeError('Background readiness observation failed: '+failure)
        if result is None or self._stop.is_set():return None
        age=self._clock()-result.completed_at
        return result if 0<=age<=self._max_age else None

    def diagnostics(self):
        """Bounded local sampling counters; no exception payload or engine data."""
        self._check()
        with self._lock:
            return dict(query_failures=self._query_failures,last_query_failure=self._diagnostic)

    def close(self, *, timeout=.1):
        """Request owner-thread cleanup; return False while a read is in flight."""
        self._check()
        if type(timeout) not in (float,int) or not math.isfinite(timeout) or not 0<=timeout<=2:
            raise ValueError('close timeout must be 0..2 seconds')
        self._stop.set()
        self._thread.join(timeout)
        return self.closed.is_set()
