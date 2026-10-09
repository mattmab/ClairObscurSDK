"""Unified management harness; console frontend first, UMG/input pending."""
from expedition33.management import ModDefinition, Action
from expedition33.management_console import ConsoleMenu


class Mod:
    def __init__(self):
        self.menu = None
        self.registry = None

    def management(self):
        return ModDefinition('sdk.management', 'SDK Management', protected=True,
            description='Shared mod registry and console menu. Native UMG and key dispatch pending.',
            actions=(Action('shutdown', 'Stop the SDK controller cleanly', self.shutdown),))

    def enable(self, session):
        self.registry = session.mods
        self.menu = ConsoleMenu(session.mods, session.console)

    def shutdown(self, argument):
        self.registry.request_shutdown()
        return 'Controller shutdown requested; cleanup follows this command.'

    def disable(self):
        if self.menu is not None:
            self.menu.close()
            self.menu = None
        self.registry = None
