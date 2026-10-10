"""Unified console and native management with optional v19 key delivery."""
from expedition33.management import ModDefinition, Action
from expedition33.management_console import ConsoleMenu
from expedition33.management_service import NativeMenuService


class Mod:
    def __init__(self):
        self.menu = None
        self.native = None
        self.registry = None

    def management(self):
        return ModDefinition('sdk.management', 'SDK Management', protected=True,
            description='Shared registry, console fallback, native UMG menu and configurable keys. Key delivery requires --keybinds.',
            actions=(Action('shutdown', 'Stop the SDK controller cleanly', self.shutdown),))

    def enable(self, session):
        self.registry = session.mods
        self.native = NativeMenuService(session, session.mods)
        self.menu = ConsoleMenu(session.mods, session.console, native=self.native)

    def shutdown(self, argument):
        self.registry.request_shutdown()
        return 'Controller shutdown requested; cleanup follows this command.'

    def poll(self):
        if self.native is not None:
            self.native.poll()

    def disable(self):
        try:
            if self.native is not None:
                self.native.close()
                self.native = None
        finally:
            if self.menu is not None:
                self.menu.close()
                self.menu = None
            self.registry = None
