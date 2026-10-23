"""Start passive, copied map observations before gameplay activation."""
from expedition33.admission_monitor import ReadOnlyAdmissionMonitor
from .context_observer import ContextObserver


class LoadingContext:
    def __init__(self,mod,session):
        self.mod=mod;self.pid=session.pid;self.monitor=None;self.released=False

    def prepare(self,context):
        pid=self.pid
        self.monitor=ReadOnlyAdmissionMonitor(lambda:ContextObserver(pid),interval=.25,max_age=1.)
        self.mod._loading_context=self

    def bind(self,context,*,preparing=False):
        pass # Read worker owns sampling; never invokes gameplay callbacks.

    def take(self):
        monitor,self.monitor=self.monitor,None
        self.released=True
        return monitor

    def close(self):
        if self.monitor is not None and self.monitor.close(timeout=2.):self.monitor=None
