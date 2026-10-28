"""UMG-independent frontend. Only the registered `mods` command owns input."""
import json

from .management import ManagementError


HELP = '''Mods menu: every navigation command starts with mods.
mods                         list loaded mods and installed folders
mods load FOLDER              load trusted local mod metadata (executes Python)
mods select MOD_ID            select a registered mod
mods enable | disable        change selected mod's lifecycle state
mods options | actions       show selected mod's settings/actions
mods set OPTION_ID JSON      validate, save and apply an option
mods reset OPTION_ID         restore an option default
mods action ACTION_ID [JSON] invoke an enabled mod's action
mods keys                    show bindings and enabled-mod conflicts
mods bind BINDING_ID KEY      save a single-key mapping
mods unbind BINDING_ID        remove the mapping
mods resetkey BINDING_ID      restore the binding default
mods unload                  unload selected mod and revoke its resources
mods shutdown                stop the SDK controller cleanly (leave game running)
mods back | quit             leave selection or close this menu
mods ui [open|close|refresh|status]  experimental native menu
mods open                    open the Mods menu in the current context
mods help                    show this help
Key preferences are available; native key delivery requires a supporting controller.
Native Unreal commands and py commands remain available at all times.'''


class ConsoleMenu:
    def __init__(self, registry, console, *, native=None):
        self.native = native
        self.registry = registry
        self.selection = None
        self._closed = False
        self._handle = console.register('mods', self.command, owner=self)

    def close(self):
        if not self._closed:
            self._closed = True
            self.selection = None
            self._handle.remove()

    def _selected(self):
        if self.selection is None:
            raise ManagementError('Use mods select MOD_ID first')
        return self.registry.view(self.selection)

    def _list(self):
        views = self.registry.views()
        print('SDK mods — console management (UMG not required)')
        for view in views:
            print(f"  {view['id']}: {view['name']} — {'disabling' if view.get('disable_pending') else 'enabled' if view['enabled'] else 'disabled'}"
                  + (' [core]' if view['protected'] else ''))
        loaded = {view['folder'] for view in views}
        available = [name for name in self.registry.installed() if name not in loaded]
        if available:
            print('Installed but not loaded: ' + ', '.join(available))
        print('Use mods select MOD_ID, mods load FOLDER, or mods help.')

    def command(self, arguments):
        if self._closed:
            raise ManagementError('Mods menu is closed')
        parts = arguments.strip().split(None, 1)
        verb, tail = (parts[0].lower(), parts[1] if len(parts) > 1 else '') if parts else ('list', '')
        if verb == 'open':
            if tail:raise ManagementError('Use mods open')
            verb,tail='ui','open'
        if verb in ('list', 'help', 'back', 'quit', 'enable', 'disable', 'unload', 'options', 'actions', 'keys', 'shutdown') and tail:
            raise ManagementError(f'mods {verb} takes no arguments')
        if verb == 'ui':
            if self.native is None:
                raise ManagementError('Native menu is unavailable; console management remains available')
            print(self.native.command(tail))
        elif verb == 'shutdown':
            self.registry.request_shutdown()
            print('Controller shutdown requested; cleanup follows this command.')
        elif verb == 'help':
            print(HELP)
        elif verb in ('list', 'back'):
            self.selection = None
            self._list()
        elif verb == 'quit':
            self.selection = None
            print('Mods menu closed. Type mods to reopen.')
        elif verb == 'load':
            if not tail:
                raise ManagementError('Use mods load FOLDER')
            self.registry.load(tail)
            self._list()
        elif verb == 'select':
            self.selection = self.registry.select(tail)
            print(json.dumps(self._selected(), ensure_ascii=False, indent=2))
        elif verb in ('enable', 'disable'):
            self._selected()
            self.selection = self.registry.set_enabled(self.selection, verb == 'enable')
            state=self._selected()
            print(f"{self.selection.mod_id}: {'disabling' if state.get('disable_pending') else 'enabled' if state['enabled'] else 'disabled'}")
        elif verb == 'unload':
            self._selected()
            self.registry.unload(self.selection)
            self.selection = None
            self._list()
        elif verb in ('options', 'actions'):
            print(json.dumps(self._selected()[verb], ensure_ascii=False, indent=2))
        elif verb == 'keys':
            print(json.dumps({'bindings': self._selected()['keybinds'],
                             'conflicts': self.registry.key_conflicts()}, indent=2))
        elif verb in ('bind', 'unbind', 'resetkey'):
            self._selected()
            values = tail.split()
            if len(values) != (2 if verb == 'bind' else 1):
                raise ManagementError('Use mods help for binding syntax')
            self.selection = self.registry.set_keybind(self.selection, values[0],
                values[1] if verb == 'bind' else None, reset=verb == 'resetkey')
            print('Saved key preference: ' + repr(self.registry.keybind(self.selection, values[0])))
            conflicts = self.registry.key_conflicts()
            if conflicts:
                print('Conflicting keys will not dispatch: ' + json.dumps(conflicts))
        elif verb in ('set', 'reset', 'action'):
            self._selected()
            values = tail.split(None, 1)
            if not values or (verb == 'set' and len(values) != 2) or (verb == 'reset' and len(values) != 1):
                raise ManagementError('Use mods help for the command syntax')
            argument = json.loads(values[1]) if len(values) == 2 else None
            if verb == 'action':
                result = self.registry.invoke(self.selection, values[0], argument)
            else:
                result = self.registry.set_option(self.selection, values[0], argument, reset=verb == 'reset')
            print(repr(result))
        else:
            raise ManagementError('Unknown menu command; use mods help')
