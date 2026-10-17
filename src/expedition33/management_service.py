"""SDK Management's lifecycle owner for the experimental native frontend."""
import logging
import time
from . import RuntimeQueryError

from .management import ManagementError
from .management_native import NativeManagementMenu


class NativeMenuService:
    def __init__(self, scope, registry, *, view_factory=None, menu_factory=None):
        self._menu_factory = menu_factory or NativeManagementMenu
        self._view_options = {} if view_factory is None else {'view_factory': view_factory}
        self.scope = scope
        self.registry = registry
        self.menu = None
        self._closed = False
        self._failure = None
        self._observed = None
        self._next_poll = 0.
        self._warmup_attempted = False
        self.travel_recovery = None
        self._discovery_retries = 0
        self._next_prepare = 0.

    @property
    def travel_recovery_pending(self):
        owner = self.travel_recovery
        return (owner is not None and owner.state in ('traveling', 'recovering')
                and time.monotonic() < owner.deadline)

    def prepare(self):
        """One owned startup warmup; no attachment, focus or click hooks."""
        self._check()
        if self.travel_recovery_pending:
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
            logging.getLogger(__name__).info('Native menu ready (detached warmup %.3fs)',
                                            time.perf_counter() - started)
        except BaseException as error:
            panel = self.menu.panel
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
            self._failure = f'{type(error).__name__}: {error}'
            logging.getLogger(__name__).exception('Native menu warmup failed; owner retained: %s', self._failure)

    def _check(self):
        if self._closed:
            raise ManagementError('Native menu service is closed')
        self.scope._check()

    def _snapshot(self):
        return (self.registry.views(), self.registry.installed(),
                dict(getattr(self.registry, '_startup_progress', {})))

    def status(self):
        self._check()
        return {'available': self.scope.supports_multi_controls,
                'state': self.menu.panel.state if self.menu is not None else 'not_created',
                'error': self._failure,
                'cached_widgets': self.menu is not None and self.menu.panel.state == 'built',
                'experimental': True,
                'limitations': ('Dispose the cached menu before map travel with mods ui dispose. Key delivery requires --keybinds.'
                    if getattr(self._menu_factory, 'supports_typed_editors', False) else
                    'Native numeric, text and JSON editors are unavailable; use console management. Dispose the cached menu before map travel with mods ui dispose. Key delivery requires --keybinds.')}

    def for_view(self, view_factory):
        """Share the cached native panel with another independently owned view."""
        return NativeMenuRoute(self, view_factory)

    def open(self, *, view_factory=None):
        self._check()
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
            self.menu.open()
            self._observed = self._snapshot()
        except BaseException as error:
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
            if not self.menu.hide():
                raise ManagementError('Native menu detach is pending; keep its owner')
            self._observed = None
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
        self._observed = None
        return 'Native menu closed'

    def refresh(self):
        self._check()
        if self._failure:
            raise ManagementError('Native menu refresh is suspended after failure; close it first')
        if self.menu is None or self.menu.panel.state != 'open':
            raise ManagementError('Open the native menu first')
        try:
            self.menu.refresh()
            self._observed = self._snapshot()
        except BaseException as error:
            self._failure = f'{type(error).__name__}: {error}'
            self.menu._accept_input = False
            raise
        return 'Native menu refreshed'

    def poll(self):
        self._check()
        if self.travel_recovery_pending:
            return
        self.prepare()
        if self.menu is not None and self.menu.failure:
            self._failure = self.menu.failure
        if (self._failure or self.menu is None or self.menu.panel.state != 'open'
                or time.monotonic() < self._next_poll):
            return
        self._next_poll = time.monotonic() + .5
        try:
            if self._snapshot() != self._observed:
                self.refresh()
        except BaseException as error:
            # Preserve console fallback and the owner; do not replay mutations.
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
