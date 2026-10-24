"""SDK Management's lifecycle owner for the experimental native frontend."""
from .frontend_rejection import known_rejection
import logging
import time
from ._menu_latency import MenuLatency, measure_method
from . import RuntimeQueryError

from .management import ManagementError
from .management_native import NativeManagementMenu


class NativeMenuService:
    def __init__(self, scope, registry, *, view_factory=None, menu_factory=None, readiness=None):
        if readiness is not None and not callable(readiness):
            raise TypeError('readiness must be a callable or None')
        self.latency = MenuLatency()
        self._menu_factory = menu_factory or NativeManagementMenu
        self._view_options = {} if view_factory is None else {'view_factory': view_factory}
        self._readiness = readiness
        self.scope = scope
        self.registry = registry
        self.menu = None
        self._closed = False
        self._failure = None
        self._frontend_rejection = None
        self._observed = None
        self._prepared_view_state = None
        self._next_poll = 0.
        self._warmup_attempted = False
        self.travel_recovery = None
        self._discovery_retries = 0
        self._next_prepare = 0.

    @property
    def readiness_state(self):
        """True=ready, False=known inactive, None=observation pending."""
        value = True if self._readiness is None else self._readiness()
        if value is not None and type(value) is not bool:
            raise TypeError('readiness must return bool or None')
        return value

    @property
    def ui_ready(self):
        return self.readiness_state is True

    @property
    def travel_recovery_pending(self):
        owner = self.travel_recovery
        return (owner is not None and owner.state in ('traveling', 'recovering')
                and time.monotonic() < owner.deadline)

    @measure_method('service.prepare_total')
    def prepare(self):
        """One owned startup warmup; no attachment, focus or click hooks."""
        self._check()
        if self.travel_recovery_pending or not self.ui_ready:
            return
        if time.monotonic() < self._next_prepare:
            return
        if self._warmup_attempted or self.menu is not None or not self.scope.supports_multi_controls:
            return
        self._warmup_attempted = True
        self.menu = self._menu_factory(self.scope, self.registry,
            cached_construction=True, selected_results=True, read_batches=True, reusable=True, **self._view_options)
        try:
            started = time.perf_counter()
            with self.menu._read_operation():
                self.menu.prepare()
            self._discovery_retries = 0
            self._observed = self._snapshot()
            prepared_state=getattr(self.menu,'prepared_view_state',None)
            self._prepared_view_state = prepared_state() if callable(prepared_state) else None
            logging.getLogger(__name__).info('Native menu ready (detached warmup %.3fs)',
                                            time.perf_counter() - started)
        except BaseException as error:
            panel = self.menu.panel
            from .cinematics.original_game_action import NotReady
            if (isinstance(error,NotReady) and panel.widget is None and panel._planner is None
                    and not panel.children and not panel.assigned and not panel.uncertain):
                # Pure controller discovery raced travel: no engine mutation
                # occurred, so retain no failed frontend and sample again later.
                self.dispose_menu();self._warmup_attempted=False
                self._next_prepare=time.monotonic()+.5
                return
            if (isinstance(error, RuntimeQueryError) and self._discovery_retries < 3
                    and any(code in str(error) for code in ('DESCRIPTOR_IDENTITY_CHANGED',
                        'MATCH_RESULT_LIMIT', 'READ_FAILED', 'Catalog outer missing or changed'))
                    and panel.widget is None and panel._planner is None
                    and not panel.children and not panel.assigned and not panel.uncertain):
                # Discovery only: no widget was constructed or engine call
                # dispatched. Dispose the empty owner before a bounded retry.
                self.dispose_menu()
                self._discovery_retries += 1
                self._warmup_attempted = False
                self._next_prepare = time.monotonic() + .5
                logging.getLogger(__name__).warning('Menu discovery changed during loading; retry %d/3', self._discovery_retries)
                return
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self._failure = f'{type(error).__name__}: {error}'
            logging.getLogger(__name__).exception('Native menu warmup failed; owner retained: %s', self._failure)

    def _check(self):
        if self._closed:
            raise ManagementError('Native menu service is closed')
        self.scope._check()

    @measure_method('service.registry_snapshot')
    def _snapshot(self):
        registry=getattr(getattr(self.menu,'view',None),'registry',self.registry)
        settings=getattr(registry,'_settings',None)
        path=getattr(settings,'path',None)
        try:
            stat=path.stat() if path is not None else None
            stamp=(stat.st_mtime_ns,stat.st_size) if stat is not None else None
        except OSError:stamp=('unavailable',)
        return (registry.views(), registry.installed(),
                dict(getattr(registry, '_startup_progress', {}) or {}),stamp)

    def status(self):
        self._check()
        return {'available': self.scope.supports_multi_controls,
                'state': self.menu.panel.state if self.menu is not None else 'not_created',
                'error': self._failure,
                'cached_widgets': self.menu is not None and self.menu.panel.state == 'built',
                'latency': self.latency.snapshot(),
                'menu_latency': self.menu.latency.snapshot() if getattr(self.menu,'latency',None) is not None else None,
                'widget_latency': self.menu.panel.latency.snapshot() if self.menu is not None and getattr(self.menu.panel,'latency',None) is not None else None,
                'experimental': True,
                'limitations': ('Dispose the cached menu before map travel with mods ui dispose. Key delivery requires --keybinds.'
                    if getattr(self._menu_factory, 'supports_typed_editors', False) else
                    'Native numeric, text and JSON editors are unavailable; use console management. Dispose the cached menu before map travel with mods ui dispose. Key delivery requires --keybinds.')}

    def for_view(self, view_factory):
        """Share the cached native panel with another independently owned view."""
        return NativeMenuRoute(self, view_factory)

    def _warm_menu_plan(self):
        """Repair invalidated planning bytes while detached; acquire no UI owners."""
        if not getattr(self,'_keep_menu_plan_warm',False):return
        if self.menu is None or self.menu.panel.state!='built':return
        session=self.scope._session
        # Another mod can own the native input menu while this cached shell is
        # detached. Rewarm after its close ACK; competing with that owner would
        # reject preparation and incorrectly suspend the Mods frontend.
        if any(menu.active for menu in getattr(session,'_menus',())):return
        cached=getattr(session,'_menu_plan_cache',None)
        if cached is not None and cached is getattr(self,'_primed_menu_cache',None):return
        from ._reader import ReadBatch
        with ReadBatch(self.scope.pid):
            self.menu.panel.prime_menu_plan()
        self._primed_menu_cache=getattr(session,'_menu_plan_cache',None)

    @measure_method('service.open_total')
    def open(self, *, view_factory=None):
        self._check()
        if not self.ui_ready:
            raise ManagementError('Native menu is waiting for a ready world; console management remains available')
        if not self.scope.supports_multi_controls:
            raise ManagementError('Native menu requires the --multi-controls controller; use mods for console management')
        if self._failure:
            raise ManagementError('Native menu failed; close it before reopening: ' + self._failure)
        if self.menu is not None:
            if self.menu.panel.state == 'open':
                return 'Native menu is already open'
            if self.menu.panel.state not in ('closed', 'built'):
                raise ManagementError('Previous native menu still owns resources; close it before reopening')
        # Assign before construction: failures must not discard the cleanup owner.
        if self.menu is None or self.menu.panel.state == 'closed':
            self.menu = self._menu_factory(self.scope, self.registry,
                cached_construction=True, selected_results=True, read_batches=True, reusable=True, **self._view_options)
        try:
            if view_factory is None:
                from .management_view import ManagementView
                view_factory = self._view_options.get('view_factory', ManagementView)
            if self.menu._view_factory is not view_factory:
                self.menu.view.close()
                self.menu._view_factory = view_factory
                self.menu.view = view_factory(self.registry)
            prepared_state=getattr(self.menu,'prepared_view_state',None)
            if callable(prepared_state):
                registry_matches = self._observed == self._snapshot()
                view_matches = (self._prepared_view_state is not None
                                and self._prepared_view_state == prepared_state())
                self.menu._reuse_prepared_frame = registry_matches and view_matches
                self.latency.count('frame.reused' if registry_matches and view_matches else 'frame.repainted')
                if not registry_matches:self.latency.count('frame.registry_changed')
                if not view_matches:self.latency.count('frame.view_changed')
            self._prepared_view_state = None
            self._warm_menu_plan()
            self.menu.open()
            self._observed = self._snapshot()
            self._prepared_view_state = prepared_state() if callable(prepared_state) else None
            logging.getLogger(__name__).info('Native menu open stages (ms): %s',{
                key:round(row['last_ms'],1) for source in (getattr(self.menu,'latency',None),getattr(self.menu.panel,'latency',None))
                if source is not None for key,row in source.snapshot()['timings'].items()
                if key in ('menu.paint_total','menu.bind_controls','widget.layout_total','widget.appearance_total','widget.open_attach_focus','widget.prime_menu_plan')})
        except BaseException as error:
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self._failure = f'{type(error).__name__}: {error}'
            raise
        return 'Native menu opened'

    def close_menu(self):
        self._check()
        if self.menu is not None and self.menu.panel.state == 'open' and not self._failure:
            presentation=getattr(self.menu,'_presentation_owner',None)
            stop=getattr(presentation,'stop_playback',None)
            if callable(stop):
                finished=stop()
                return 'Playback stopped; menu restored' if finished else 'Playback cleanup pending; owner retained'
            prepared_state=getattr(self.menu,'prepared_view_state',None)
            reuse = (callable(prepared_state) and self._prepared_view_state is not None
                     and self._observed == self._snapshot()
                     and self._prepared_view_state == prepared_state())
            if not self.menu.hide():
                raise ManagementError('Native menu detach is pending; keep its owner')
            # Only suspension's revision changed; stale callback revisions were
            # revoked before detach. Any other view/registry change repaints.
            self._prepared_view_state = (prepared_state() if reuse
                and not self.menu.view.closed and self._observed == self._snapshot() else None)
            return 'Native menu closed (owned widgets retained for reopening)'
        if self.menu is not None and self.menu.panel.state == 'built' and not self._failure:
            return 'Native menu is already closed (owned widgets retained)'
        return self.dispose_menu()

    def dispose_menu(self):
        """Release cached widgets; called for failure recovery and shutdown."""
        self._check()
        if self.menu is not None and not self.menu.close():
            raise ManagementError('Native menu cleanup is pending; keep its owner and try close after polling')
        self.menu = None
        self._failure = None
        self._frontend_rejection = None
        self._observed = None
        self._prepared_view_state = None
        return 'Native menu closed'

    @measure_method('service.refresh_total')
    def refresh(self):
        self._check()
        if not self.ui_ready:
            raise ManagementError('Native menu is waiting for a ready world; console management remains available')
        if self._failure:
            raise ManagementError('Native menu refresh is suspended after failure; close it first')
        if self.menu is None or self.menu.panel.state != 'open':
            raise ManagementError('Open the native menu first')
        try:
            self.menu.refresh()
            self._observed = self._snapshot()
            prepared_state=getattr(self.menu,'prepared_view_state',None)
            self._prepared_view_state = prepared_state() if callable(prepared_state) else None
        except BaseException as error:
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self._failure = f'{type(error).__name__}: {error}'
            self.menu._accept_input = False
            raise
        return 'Native menu refreshed'

    @measure_method('service.refresh_detached')
    def _refresh_detached(self):
        self._check()
        if not self.ui_ready or self._failure:
            raise ManagementError('Detached refresh requires explicit UI readiness')
        self.menu.refresh_detached()
        self._observed = self._snapshot()
        prepared_state=getattr(self.menu,'prepared_view_state',None)
        self._prepared_view_state = prepared_state() if callable(prepared_state) else None

    def poll(self):
        self._check()
        if self.travel_recovery_pending:
            return
        state = self.readiness_state
        if state is None:
            # Uncertain observation inhibits new work, but does not prove the
            # previous world retired or authorize touching its UI owners.
            return
        if state is False:
            # Returning to title must still service already-owned UI cleanup.
            # dispose_menu retains its owner if acknowledged cleanup is pending.
            if self.menu is not None:
                self.dispose_menu()
                self._warmup_attempted = False
            return
        self.prepare()
        if self.menu is not None and self.menu.failure:
            self._failure = self.menu.failure
        if (self._failure or self.menu is None or self.menu.panel.state not in ('built','open')):
            return
        try:
            # Other mods' metadata preparation invalidates this shared cache.
            # Repair before readiness consumers can attach, even if presenter
            # refresh is throttled. Fresh prepare keeps all identity guards.
            self._warm_menu_plan()
            progress=getattr(self.registry,'_startup_progress',None)
            if (self.menu.panel.state=='built' and type(progress) is dict
                    and progress.get('finished') is False):
                # Coalesce activation changes into one detached repaint. An open
                # menu still renders progress and explicit open always validates
                # and refreshes its current frame before accepting input.
                return
            if time.monotonic() < self._next_poll:return
            self._next_poll = time.monotonic() + .5
            registry_changed = self._snapshot() != self._observed
            if self.menu.panel.state == 'built':
                prepared_state=getattr(self.menu,'prepared_view_state',None)
                current_state=prepared_state() if callable(prepared_state) else None
                view_changed = (current_state is not None and
                    (self._prepared_view_state is None or self._prepared_view_state != prepared_state()))
                if registry_changed or view_changed:self._refresh_detached()
            elif registry_changed:self.refresh()
        except BaseException as error:
            # Preserve console fallback and the owner; do not replay mutations.
            self._frontend_rejection = known_rejection(error) or getattr(self,'_frontend_rejection',None)
            self._failure = f'{type(error).__name__}: {error}'
            self.menu._accept_input = False
            logging.getLogger(__name__).error('Native menu refresh suspended: %s', self._failure)

    def command(self, arguments):
        verb = arguments.strip().lower() or 'open'
        actions = {'open': self.open, 'close': self.close_menu,
                   'dispose': self.dispose_menu, 'refresh': self.refresh, 'status': self.status}
        if verb not in actions:
            raise ManagementError('Use mods ui [open|close|dispose|refresh|status]')
        return actions[verb]()

    def close(self):
        if self._closed:
            return
        self.dispose_menu()
        self._closed = True
        self.travel_recovery = None
        self.scope = self.registry = None


class NativeMenuRoute:
    """A presenter route; the parent alone owns widgets and native resources."""
    def __init__(self, parent, factory):
        self.parent, self.factory = parent, factory

    @property
    def menu(self):
        menu = self.parent.menu
        return menu if menu is not None and menu._view_factory is self.factory else None

    def open(self):
        if self.parent.menu is not None and self.parent.menu.panel.state == 'open':
            raise ManagementError('Another native view is open')
        return self.parent.open(view_factory=self.factory)

    def status(self):
        return dict(self.parent.status(), shared_panel=True, active_view=self.menu is not None)

    def poll(self):
        pass  # Parent polls shared controls exactly once.

    def close_menu(self):
        if self.menu is not None:
            return self.parent.close_menu()

    def dispose_menu(self):
        return self.close_menu()

    def close(self):
        self.close_menu()
        if self.menu is not None:
            # Release the mod-bound factory even when the tree stays cached.
            from .management_view import ManagementView
            self.parent.menu._view_factory = ManagementView
            self.parent.menu.view = ManagementView(self.parent.registry)
