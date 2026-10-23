"""Borrowed frontend routes; ProcessUI alone owns and ticks the UI tree."""
from .management import ManagementError


class ProcessMenuRoute:
    def __init__(self,owner,kind='world'):
        self.owner=owner;self.kind=kind;self._closed=False
        self._travel_recovery=None

    def _service(self,*,required=False):
        self.owner._check()
        context=self.owner.context
        service=self.owner.service
        usable=(not self._closed and not self.owner.failed and self.owner.phase=='ready'
            and context is not None and context.kind==self.kind and service is not None)
        if required and not usable:raise ManagementError('Requested process UI context is not ready')
        return service if usable else None

    @property
    def registry(self):return self.owner.registry

    @property
    def menu(self):
        service=self._service();return None if service is None else service.menu
    @property
    def ui_ready(self):return self._service() is not None
    @property
    def travel_recovery(self):return self._travel_recovery
    @travel_recovery.setter
    def travel_recovery(self,value):
        self._travel_recovery=value
        service=self._service()
        if service is not None:service.travel_recovery=value
    @property
    def travel_recovery_pending(self):
        import time
        request=self._travel_recovery
        return request is not None and request.state in ('traveling','recovering') and time.monotonic()<request.deadline

    def status(self):
        service=self._service()
        if service is None:return dict(state='context_pending',available=False,process_ui=self.owner.status())
        return dict(service.status(),process_ui=self.owner.status())
    def prepare(self):pass # Host owns the unique warmup.
    def poll(self):pass # Host owns the unique native UI tick.
    def open(self,*,view_factory=None):
        service=self._service(required=True)
        if self.kind=='title' and view_factory is None:
            # The entry journals title input restoration when the menu closes.
            return self.owner.open()
        return service.open(view_factory=view_factory)
    def close_menu(self):
        service=self._service()
        if service is not None:return service.close_menu()
    def dispose_menu(self):
        service=self._service()
        if service is not None:
            result=service.dispose_menu()
            self.owner._rebuild_requested=True
            return result
    def for_view(self,factory):
        from .management_service import NativeMenuRoute
        return NativeMenuRoute(self,factory)
    def command(self,argument=''):
        verb=argument.strip().casefold() or 'open'
        actions={'open':self.open,'close':self.close_menu,'dispose':self.dispose_menu,'status':self.status}
        if verb not in actions:raise ManagementError('Use mods ui [open|close|dispose|status]')
        return actions[verb]()
    def close(self):
        # Borrower retirement never closes/reparents the host's process scope.
        self.close_menu();self._closed=True


class ProcessEntryRoute:
    def __init__(self,owner,kind='world'):self.owner=owner;self.kind=kind;self._closed=False
    def _entry(self):
        context=self.owner.context
        return (self.owner.entry.entry if not self._closed and self.owner.entry is not None
            and context is not None and context.kind==self.kind else None)
    @property
    def state(self):
        entry=self._entry();return 'new' if entry is None else entry.state
    @property
    def available(self):return self._entry() is not None
    @property
    def timings(self):
        entry=self._entry();return {} if entry is None else entry.timings
    def poll(self):pass
    def close(self):self._closed=True
