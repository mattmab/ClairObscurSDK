"""SDK Management's lifecycle owner for the experimental native frontend."""
import logging
import time

from .management import ManagementError
from .management_native import NativeManagementMenu


class NativeMenuService:
    def __init__(self, scope, registry):
        self.scope = scope
        self.registry = registry
        self.menu = None
        self._closed = False
        self._failure = None
        self._observed = None
        self._next_poll = 0.

    def _check(self):
        if self._closed:
            raise ManagementError('Native menu service is closed')
        self.scope._check()

    def _snapshot(self):
        return (self.registry.views(), self.registry.installed())

    def status(self):
        self._check()
        return {'available': self.scope.supports_multi_controls,
                'state': self.menu.panel.state if self.menu is not None else 'not_created',
                'error': self._failure,
                'experimental': True,
                'limitations': 'Slow construction/cleanup; numeric, text and JSON editors and keybinds pending'}

    def open(self):
        self._check()
        if not self.scope.supports_multi_controls:
            raise ManagementError('Native menu requires the --multi-controls controller; use mods for console management')
        if self._failure:
            raise ManagementError('Native menu failed; close it before reopening: ' + self._failure)
        if self.menu is not None:
            if self.menu.panel.state == 'open':
                return 'Native menu is already open'
            if self.menu.panel.state != 'closed':
                raise ManagementError('Previous native menu still owns resources; close it before reopening')
        # Assign before construction: failures must not discard the cleanup owner.
        self.menu = NativeManagementMenu(self.scope, self.registry,
            cached_construction=True, selected_results=True, read_batches=True)
        logging.getLogger(__name__).info('Opening experimental native menu; construction may take several minutes')
        try:
            self.menu.open()
            self._observed = self._snapshot()
        except BaseException as error:
            self._failure = f'{type(error).__name__}: {error}'
            raise
        return 'Native menu opened'

    def close_menu(self):
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
                   'refresh': self.refresh, 'status': self.status}
        if verb not in actions:
            raise ManagementError('Use mods ui [open|close|refresh|status]')
        return actions[verb]()

    def close(self):
        if self._closed:
            return
        self.close_menu()
        self._closed = True
        self.scope = self.registry = None
