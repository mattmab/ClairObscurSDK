"""Unified console and native management with optional v19 key delivery."""
from expedition33.management import ModDefinition, Action, Keybind, Option
from expedition33.management_console import ConsoleMenu
from expedition33.management_service import NativeMenuService
from expedition33.pause_menu import PauseMenuEntry
from expedition33.mods_workspace import ModsWorkspaceMenu, ModsWorkspaceView, THEMES
from expedition33.mods_workspace_scroll import ScrollWorkspaceMenu, ScrollWorkspaceView


class Mod:
    def __init__(self):
        self.menu = None
        self.native = None
        self.registry = None
        self.pause = None

    def management(self):
        return ModDefinition('sdk.management', 'SDK Management', protected=True,
            options=(Option('theme', 'Menu theme', 'choice', 'World Builder', choices=tuple(THEMES)),
                     Option('text_scale', 'Menu text size', 'float', 1.35, minimum=.75, maximum=2.75)),
            description='Shared registry, console fallback, native UMG menu and configurable keys. Key delivery requires --keybinds.',
            keybinds=(Keybind('closemenu', 'Close Mods menu', 'Escape', self.close_menu),),
            actions=(Action('shutdown', 'Stop the SDK controller cleanly', self.shutdown),))

    def enable(self, session):
        self.registry = session.mods
        process_ui=getattr(session._session,'_process_ui',None)
        if process_ui is not None:
            from expedition33.process_ui_routes import ProcessMenuRoute,ProcessEntryRoute
            self.native=ProcessMenuRoute(process_ui)
            self.pause=ProcessEntryRoute(process_ui)
            session._session._native_menu_service=self.native
            self.menu=ConsoleMenu(session.mods,session.console,native=self.native)
            return
        readiness = getattr(session._session, '_menu_readiness', None)
        self.native = NativeMenuService(session, session.mods,
            view_factory=ScrollWorkspaceView, menu_factory=ScrollWorkspaceMenu, readiness=readiness)
        session._session._native_menu_service = self.native
        self.pause = PauseMenuEntry(session,self.native,readiness=readiness)
        self.menu = ConsoleMenu(session.mods, session.console, native=self.native)

    def prepare(self):
        self.pause.poll()
        self.native.prepare()

    def close_menu(self, argument):
        if self.native is not None and self.native.menu is not None and self.native.menu.panel.state == 'open':
            if getattr(self.native.menu.view, 'editing', None):
                menu=self.native.menu
                cancel=next((token for token,(op,_arg,enabled) in menu.view._commands.items()
                             if op=='cancel' and enabled),None)
                if cancel is not None:
                    return menu.submit(menu.frame.revision,cancel)
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
            if (self.pause is not None and self.pause.available and self.pause.state == 'new'
                    and getattr(self.native, 'ui_ready', True)):
                return
            self.native.poll()
            if self.native.menu is not None and hasattr(self.native.menu, 'poll_scroll'):
                self.native.menu.poll_scroll()

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
