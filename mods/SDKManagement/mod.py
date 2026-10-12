"""Unified console and native management with optional v19 key delivery."""
from expedition33.management import ModDefinition, Action, Keybind
from expedition33.management_console import ConsoleMenu
from expedition33.management_service import NativeMenuService
from expedition33.pause_menu import PauseMenuEntry


class Mod:
    def __init__(self):
        self.menu = None
        self.native = None
        self.registry = None
        self.pause = None

    def management(self):
        return ModDefinition('sdk.management', 'SDK Management', protected=True,
            description='Shared registry, console fallback, native UMG menu and configurable keys. Key delivery requires --keybinds.',
            keybinds=(Keybind('closemenu', 'Close Mods menu', 'Escape', self.close_menu),),
            actions=(Action('shutdown', 'Stop the SDK controller cleanly', self.shutdown),))

    def enable(self, session):
        self.registry = session.mods
        self.native = NativeMenuService(session, session.mods)
        session._session._native_menu_service = self.native
        self.pause = PauseMenuEntry(session,self.native)
        self.menu = ConsoleMenu(session.mods, session.console, native=self.native)

    def prepare(self):
        self.pause.poll()
        self.native.prepare()

    def close_menu(self, argument):
        if self.native is not None and self.native.menu is not None and self.native.menu.panel.state == 'open':
            return self.native.close_menu()

    def shutdown(self, argument):
        self.registry.request_shutdown()
        return 'Controller shutdown requested; cleanup follows this command.'

    def poll(self):
        # Cinematic spawn recovery takes priority over rebuilding travel UI.
        # Console commands, transport polling and shutdown remain serviced.
        if self.native is not None and self.native.travel_recovery_pending:
            return
        if self.pause is not None:
            self.pause.poll()
        if self.native is not None:
            # A travel reset must reattach the pause entry before rebuilding
            # the detached menu on a subsequent poll.
            if self.pause is not None and self.pause.available and self.pause.state == 'new':
                return
            self.native.poll()

    def disable(self):
        try:
            if self.pause is not None:
                self.pause.close()
                self.pause = None
            if self.native is not None:
                self.native.close()
                self.native = None
        finally:
            if self.menu is not None:
                self.menu.close()
                self.menu = None
            self.registry = None
