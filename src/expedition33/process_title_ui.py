"""A dedicated pre-gameplay UI owner; never polls gameplay mods or global keys."""
from .invocation import InvocationError
from .multi_controls import ControlBindBatchRejected
from .frontend_rejection import FrontendRejection
from ._metadata_stabilization import UnstableUIIdentity


def _recoverable_frontend(error):
    return isinstance(error,UnstableUIIdentity) or (isinstance(error,InvocationError) and error.outcome=='not_dispatched' and
            error.native_error==202) or isinstance(error,ControlBindBatchRejected)


def _failure_record(error):
    record=dict(type=type(error).__name__,native_error=error.native_error,outcome=error.outcome)
    if isinstance(error,UnstableUIIdentity):record['role']=error.role
    return record


class ProcessTitleUI:
    def __init__(self, session, registry, *, scope_factory=None, service_factory=None,
                 entry_factory=None, view_factory=None, menu_factory=None):
        self.session=session;self.registry=registry
        self._factories=(scope_factory,service_factory,entry_factory,view_factory,menu_factory)
        self.scope=self.service=self.entry=None
        self._ready=None
        self.cleanup_pending=False
        self._lease_journal=[]
        self.frontend_failed=None
        self.frontend_cleanup_pending=False

    @property
    def active(self):
        return (self.scope is not None or self.service is not None or self.entry is not None
                or bool(self._lease_journal))

    def _capture_leases(self):
        # Capture ONLY this title scope tree before a child close clears lists.
        # Never enumerate the shared Session's unrelated mod leases.
        known={id(lease) for lease in self._lease_journal}
        scopes=[self.scope] if self.scope is not None else []
        seen=set()
        while scopes:
            scope=scopes.pop()
            if id(scope) in seen:continue
            seen.add(id(scope))
            for lease in tuple(getattr(scope,'_leases',())):
                if id(lease) not in known and getattr(lease,'_state',None)!='released':
                    self._lease_journal.append(lease);known.add(id(lease))
            scopes.extend(tuple(getattr(scope,'_children',())))

    def _create(self):
        from ._scope import SessionScope
        from .management_service import NativeMenuService
        from .title_menu import TitleMenuEntry
        from .title_management import TitleWorkspaceView
        from .mods_workspace_scroll import ScrollWorkspaceMenu
        sf,nf,ef,vf,mf=self._factories
        self.scope=(sf or SessionScope)(self.session,lease_owner='SDKTitleUI')
        # Assign every owner before subsequent work can fail; failed construction
        # remains reachable for acknowledged cleanup, never silently recreated.
        self.service=(nf or NativeMenuService)(self.scope,self.registry,
            view_factory=vf or TitleWorkspaceView,menu_factory=mf or ScrollWorkspaceMenu,
            readiness=lambda:self._ready)
        self.entry=(ef or TitleMenuEntry)(self.scope,self.service,readiness=lambda:self._ready)

    def poll(self, readiness):
        if readiness is not None and type(readiness) is not bool:
            raise TypeError('Title readiness must be bool or None')
        if self.cleanup_pending and readiness is not False:
            # A fast return to title must finish prior acknowledged retirement
            # before any owner can be reused or a replacement can be created.
            self.poll(False)
            if self.active:return
        self._ready=readiness
        if readiness is False:
            if self.active:self.session.poll()
            try:self.close()
            except RuntimeError as error:
                if str(error) not in ('Pause entry detach deferred; retain its owner',
                        'Title entry detach deferred; retain its owner',
                        'Native menu detach is pending; keep its owner',
                        'Native title leases cleanup pending; retain owner',
                        'Native menu cleanup is pending; keep its owner and try close after polling'):
                    raise
                self.cleanup_pending=True
            return
        if not self.active:
            if self.frontend_failed is not None:return
            if readiness is not True:return
            self._create()
        # This exact dedicated tick intentionally bypasses ModLoader.poll,
        # Console.poll and KeybindService construction before first world.
        try:
            self.session.poll()
            if self.frontend_failed is not None:
                self._recover_frontend()
                return
            if self._recover_recorded_failure():return
            self._capture_leases()
            if self.service is not None:
                self.service.poll()
                if self._recover_recorded_failure():return
                self._capture_leases()
                menu=self.service.menu
                # Expose the title button only after the reusable shell is built.
                # An already attached entry retains its ordinary cleanup/input path.
                built=(menu is not None and getattr(getattr(menu,'panel',None),'state',None)
                       in ('built','open'))
                if self.entry is not None and (built or getattr(self.entry,'state',None)=='attached'):
                    self.entry.poll()
                    self._capture_leases()
                if menu is not None and hasattr(menu,'poll_scroll'):menu.poll_scroll()
        except (InvocationError,ControlBindBatchRejected,UnstableUIIdentity) as error:
            if not _recoverable_frontend(error):raise
            self.frontend_failed=_failure_record(error)
            self.frontend_cleanup_pending=True
            self._recover_frontend()

    def _recover_recorded_failure(self):
        # Native callbacks contain their exceptions. Only copied evidence from
        # the exact typed rejection, never a generic failure string, can select
        # frontend-only acknowledged cleanup here.
        service=self.service
        if service is None:return False
        record=getattr(service,'_frontend_rejection',None)
        if record is None:
            record=getattr(getattr(service,'menu',None),'_frontend_rejection',None)
        if not isinstance(record,FrontendRejection):return False
        self.frontend_failed=dict(type=record.kind,native_error=record.native_error,
            outcome=record.outcome)
        if record.kind=='UnstableUIIdentity':
            if record.native_error!=0 or record.outcome!='not_dispatched' or record.role not in UnstableUIIdentity.ROLES:
                self.frontend_failed=None
                return False
            self.frontend_failed['role']=record.role
        self.frontend_cleanup_pending=True
        self._recover_frontend()
        return True

    def _recover_frontend(self):
        self._capture_leases()
        if self.service is not None and self.service.menu is not None:
            try:self.service.dispose_menu()
            except RuntimeError as error:
                if str(error)!='Native menu cleanup is pending; keep its owner and try close after polling':raise
                self.frontend_cleanup_pending=True
                return False
        if self.frontend_failed is not None and self.frontend_failed['type']=='UnstableUIIdentity':
            state=getattr(self.entry,'state',None) if self.entry is not None else 'closed'
            if state!='attached':
                if state not in ('new','building','failed','closed'):
                    raise RuntimeError('Unattached title entry outcome unresolved; retain owner')
                # The pure preflight did not attach this entry. Its partially
                # built owners still require ordinary ordered close/lease ACKs.
                try:self.close()
                except RuntimeError as error:
                    if str(error) not in ('Pause entry detach deferred; retain its owner',
                            'Title entry detach deferred; retain its owner',
                            'Native menu detach is pending; keep its owner',
                            'Native title leases cleanup pending; retain owner',
                            'Native menu cleanup is pending; keep its owner and try close after polling'):
                        raise
                    self.frontend_cleanup_pending=True
                    return False
                self.frontend_cleanup_pending=False
                return True
        if self.entry is not None:
            if not self.entry.restore_title_input_after_menu_close():
                self.frontend_cleanup_pending=True
                return False
        self.frontend_cleanup_pending=False
        # Keep the bounded diagnostic separately. Future ticks never rebuild or
        # auto-open this failed optional frontend; console/core stay available.
        return True

    def open(self):
        if self.frontend_failed is not None:
            raise RuntimeError('Title frontend is suspended after a rejected invocation')
        if self._ready is not True or self.entry is None:
            raise RuntimeError('Title frontend is not ready')
        try:return self.entry.open()
        except (InvocationError,ControlBindBatchRejected,UnstableUIIdentity) as error:
            if not _recoverable_frontend(error):raise
            self.frontend_failed=_failure_record(error)
            self.frontend_cleanup_pending=True
            self._recover_frontend()
            return 'Title frontend rejected invocation; cleanup retained, core remains available'

    def close(self):
        self._ready=False
        self._capture_leases()
        if self.service is not None:
            menu=self.service.menu
            if menu is not None and (menu.panel.state=='open' or getattr(self.service,'_failure',None)):
                # Native menu hide restores its captured input mode. It must
                # acknowledge before the title entry can restore title UI mode
                # and focus or relinquish its presentation journal.
                self.service.close_menu()
                if self.service.menu is not None and menu.panel.state not in ('built','closed'):
                    raise RuntimeError('Title native menu hide acknowledgement is unresolved; keep all owners')
        if self.entry is not None:
            self.entry.close()  # Deferred acknowledgement raises; keep owner.
            self.entry=None
        if self.service is not None:
            self.service.close()  # Menu must detach before its scope releases.
            self.service=None
        if self.scope is not None:
            self.scope.close()
            self.scope=None
        self._lease_journal=[lease for lease in self._lease_journal if lease._state!='released']
        if self._lease_journal:
            if any(lease._state!='pending_release' for lease in self._lease_journal):
                raise RuntimeError('Native title leases have unresolved outcomes; retain owner')
            # Session.poll alone retries its acknowledged GC deferrals. This
            # journal never calls release(), especially for unknown outcomes.
            raise RuntimeError('Native title leases cleanup pending; retain owner')
        self.cleanup_pending=False

    def status(self):
        native=self.service.status() if self.service is not None else {}
        return dict(active=self.active, readiness=self._ready,
            cleanup_pending=self.cleanup_pending,
            pending_leases=len(self._lease_journal),
            entry_state=getattr(self.entry,'state',None),
            entry_timings=dict(getattr(self.entry,'timings',{})),
            menu_state=native.get('state'), failed=native.get('error') is not None or self.frontend_failed is not None,
            frontend_failure=self.frontend_failed and dict(self.frontend_failed),
            frontend_cleanup_pending=self.frontend_cleanup_pending,
            latency=native.get('latency'),menu_latency=native.get('menu_latency'),
            widget_latency=native.get('widget_latency'))
