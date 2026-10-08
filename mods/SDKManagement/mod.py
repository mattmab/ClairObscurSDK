"""Unified management harness; console frontend first, UMG/input pending."""
from expedition33.management import ModDefinition
from expedition33.management_console import ConsoleMenu


class Mod:
    def __init__(self):
        self.menu = None

    def management(self):
        return ModDefinition('sdk.management', 'SDK Management', protected=True,
            description='Shared mod registry and console menu. Native UMG and key dispatch pending.')

    def enable(self, session):
        self.menu = ConsoleMenu(session.mods, session.console)

    def disable(self):
        if self.menu is not None:
            self.menu.close()
            self.menu = None
