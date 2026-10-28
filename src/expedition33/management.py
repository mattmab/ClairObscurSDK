"""Shared mod definitions, preferences and owner-thread action dispatch.

No engine/UI dependency. The loader owns lifecycle state; frontends receive copies
and generation tokens, never mod instances or engine pointers.
"""
import copy
from dataclasses import dataclass, field
import json
import math
import threading
import time

from .settings import identifier, _json_value
from .keys import normalize_key, VIRTUAL_KEYS


class ManagementError(RuntimeError):
    pass


@dataclass(frozen=True)
class Option:
    id: str
    title: str
    kind: str
    default: object
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple = ()
    on_change: object = field(default=None, repr=False, compare=False)

    def validate(self, value):
        if self.kind == 'bool':
            valid = type(value) is bool
        elif self.kind in ('int', 'float'):
            valid = (type(value) is int if self.kind == 'int' else type(value) in (int, float))
            try:
                valid = valid and math.isfinite(value)
            except OverflowError:
                valid = False
            valid = valid and (self.minimum is None or value >= self.minimum)
            valid = valid and (self.maximum is None or value <= self.maximum)
        elif self.kind == 'choice':
            valid = any(type(value) is type(choice) and value == choice for choice in self.choices)
        elif self.kind == 'text':
            valid = type(value) is str and len(value) <= 4096 and '\0' not in value
        else:
            raise ManagementError(f'Unsupported option kind {self.kind!r}')
        if not valid:
            raise ManagementError(f'Invalid value for option {self.id!r} ({self.kind})')
        _json_value(value)
        return copy.deepcopy(value)


@dataclass(frozen=True)
class Action:
    id: str
    title: str
    callback: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class Report:
    """Bounded, read-only action result rendered inside the shared native menu."""
    title: str
    description: str
    entries: tuple = ()  # (row label, detail text), no callbacks or object handles

    def __post_init__(self):
        if type(self.entries) is not tuple or len(self.entries) > 1000:
            raise ValueError('Report requires at most 1000 entries')
        for text, limit in ((self.title, 120), (self.description, 4096)):
            if type(text) is not str or len(text) > limit or '\0' in text:
                raise ValueError('Invalid report text')
        for row in self.entries:
            if type(row) is not tuple or len(row) != 2:
                raise ValueError('Report entry requires label and detail')
            for text, limit in zip(row, (160, 4096)):
                if type(text) is not str or len(text) > limit or '\0' in text:
                    raise ValueError('Invalid report entry')


@dataclass(frozen=True)
class Keybind:
    id: str
    title: str
    default: str | None
    callback: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class ModDefinition:
    id: str
    title: str
    description: str = ''
    author: str = ''
    version: str = ''
    protected: bool = False
    options: tuple[Option, ...] = ()
    actions: tuple[Action, ...] = ()
    keybinds: tuple[Keybind, ...] = ()


@dataclass(frozen=True)
class Selection:
    mod_id: str
    generation: int


@dataclass
class _Entry:
    name: str
    definition: ModDefinition
    generation: int
    preferences: dict
    error: str | None = None


class Registry:
    def __init__(self, loader, settings=None):
        self._loader = loader
        self._settings = settings
        self._owner = threading.get_ident()
        self._entries = {}
        self._pending_disables = {}
        self._generation = 0
        self._dispatching = set()
        from .startup_order import StartupOrder
        self._startup_order = StartupOrder(settings.path.parent / "startup-order.json") if settings is not None else None

    def _check(self):
        if threading.get_ident() != self._owner:
            raise ManagementError('Management requires the controller owner thread')

    def _next(self):
        self._generation += 1
        return self._generation

    def register(self, name, definition):
        self._check()
        if not isinstance(definition, ModDefinition):
            raise ManagementError('management() must return a ModDefinition')
        identifier(definition.id)
        if definition.id in self._entries or any(e.name == name for e in self._entries.values()):
            raise ManagementError('Duplicate mod ID or loader name')
        for value in (definition.title, definition.description, definition.author, definition.version):
            if type(value) is not str or len(value) > 8192 or '\0' in value:
                raise ManagementError('Invalid mod metadata text')
        if type(definition.protected) is not bool:
            raise ManagementError('Protected policy must be a boolean')
        for collection, expected in ((definition.options, Option), (definition.actions, Action),
                                     (definition.keybinds, Keybind)):
            if type(collection) is not tuple or len(collection) > 256:
                raise ManagementError('Definitions require bounded tuples of options/actions')
            seen = set()
            for item in collection:
                if not isinstance(item, expected):
                    raise ManagementError('Invalid option/action definition')
                identifier(item.id)
                if item.id in seen:
                    raise ManagementError('Duplicate option/action ID')
                seen.add(item.id)
                if type(item.title) is not str or len(item.title) > 256 or '\0' in item.title:
                    raise ManagementError('Invalid option/action title')
                if expected in (Action, Keybind) and not callable(item.callback):
                    raise ManagementError('Action callback must be callable')
                if expected is Keybind:
                    normalize_key(item.default)
                if expected is Option:
                    if item.on_change is not None and not callable(item.on_change):
                        raise ManagementError('Option callback must be callable')
                    if type(item.choices) is not tuple or len(item.choices) > 256:
                        raise ManagementError('Choices require a bounded tuple')
                    if any(type(choice) not in (str, int, float, bool) for choice in item.choices):
                        raise ManagementError('Choices must be JSON scalars')
                    for bound in (item.minimum, item.maximum):
                        if bound is not None and (type(bound) not in (int, float) or not math.isfinite(bound)):
                            raise ManagementError('Numeric bounds must be finite')
                    if item.minimum is not None and item.maximum is not None and item.minimum > item.maximum:
                        raise ManagementError('Minimum exceeds maximum')
                    item.validate(item.default)
                    _json_value(item.choices and list(item.choices) or [])
        preferences = self._settings.get(definition.id) if self._settings is not None else {}
        for option in definition.options:
            option.validate(preferences.get('options', {}).get(option.id, option.default))
        for binding in definition.keybinds:
            normalize_key(preferences.get('keybinds', {}).get(binding.id, binding.default))
        self._entries[definition.id] = _Entry(name, definition, self._next(), preferences)

    def unregister(self, name):
        self._check()
        for mod_id, entry in tuple(self._entries.items()):
            if entry.name == name:
                self._pending_disables.pop(mod_id, None)
                del self._entries[mod_id]

    def changed(self, name):
        """Loader transition invalidates already-rendered selections/events."""
        self._check()
        for entry in self._entries.values():
            if entry.name == name:
                entry.generation = self._next()

    def select(self, mod_id):
        self._check()
        try:
            entry = self._entries[mod_id]
        except KeyError:
            raise ManagementError(f'No registered mod {mod_id!r}') from None
        return Selection(mod_id, entry.generation)

    def _entry(self, selection):
        self._check()
        if not isinstance(selection, Selection) or self.select(selection.mod_id) != selection:
            raise ManagementError('Stale mod selection; select the mod again')
        return self._entries[selection.mod_id]

    def _enabled(self, entry):
        return any(status.name == entry.name and status.enabled for status in self._loader.status())

    def view(self, selection):
        entry = self._entry(selection)
        definition = entry.definition
        active = self._enabled(entry)
        return {'id': definition.id, 'name': definition.title, 'folder': entry.name,
                'description': definition.description, 'author': definition.author,
                'version': definition.version, 'protected': definition.protected,
                'enabled': active, 'generation': entry.generation,
                'desired_enabled': entry.preferences.get('enabled', active),
                'staged_pending': entry.preferences.get('enabled', active) != active,
                'disable_pending': selection.mod_id in self._pending_disables,
                'error': entry.error, 'persistence': self._settings is not None,
                'cleanup_error': next((getattr(s, 'cleanup_error', None)
                    for s in self._loader.status() if s.name == entry.name), None),
                'preparation_error': next((getattr(s, 'preparation_error', None)
                    for s in self._loader.status() if s.name == entry.name), None),
                'source_sha256': next((getattr(s, 'source_sha256', None)
                    for s in self._loader.status() if s.name == entry.name), None),
                'package_sha256': next((getattr(s, 'package_sha256', None)
                    for s in self._loader.status() if s.name == entry.name), None),
                'options': [{'id': option.id, 'title': option.title, 'kind': option.kind,
                    'value': option.validate(entry.preferences.get('options', {}).get(option.id, option.default)),
                    'default': copy.deepcopy(option.default), 'minimum': option.minimum,
                    'maximum': option.maximum, 'choices': list(option.choices)} for option in definition.options],
                'actions': [{'id': action.id, 'title': action.title} for action in definition.actions],
                'keybinds': [{'id': binding.id, 'title': binding.title,
                    'value': self.keybind(selection, binding.id),
                    'default': normalize_key(binding.default)} for binding in definition.keybinds]}

    def views(self):
        self._check()
        return tuple(self.view(self.select(mod_id)) for mod_id in sorted(self._entries))

    def installed(self):
        self._check()
        return self._loader.discover()

    def request_shutdown(self):
        """Cooperative host stop; the callback returns before resource cleanup."""
        self._check()
        self._loader.request_stop()

    def load(self, folder):
        self._check()
        self._loader.load(folder)
        return next(self.select(mod_id) for mod_id, entry in self._entries.items()
                    if entry.name == folder)

    def set_enabled(self, selection, enabled):
        entry = self._entry(selection)
        if type(enabled) is not bool:
            raise ManagementError('Enabled must be a boolean')
        if not enabled and entry.definition.protected:
            raise ManagementError('This core mod is protected; stop the controller to unload it')
        preferences = copy.deepcopy(entry.preferences)
        preferences.update(enabled=enabled, folder=entry.name)
        if self._settings is not None:
            self._settings.save(selection.mod_id, preferences)
        entry.preferences = preferences
        pending=self._pending_disables.pop(selection.mod_id,None) if enabled else None
        if pending is not None:
            name,instance,scope=pending
            record=self._loader._loaded.get(name)
            lifecycle=getattr(self._loader,'world_lifecycle',None)
            binding=None if lifecycle is None else lifecycle.bindings.get(name)
            if (record is not None and record[1] is instance and record[2] is scope and
                    (lifecycle is None or (binding is not None and binding.scope is scope and binding.state=='bound'))):
                # The pending disable never ran. Release only the opt-in
                # preparation latch; cancelled read-only work still cleans up.
                instance.cancel_disable_preparation()
                self._loader._prepared_disable_scopes.pop(name,None)
                entry.generation=self._next()
                return self.select(selection.mod_id)
        operation = self._loader.enable if enabled else self._loader.disable
        try:operation(entry.name)
        except Exception as error:
            from .mods import ModDisablePending
            if not enabled and isinstance(error,ModDisablePending):
                record=self._loader._loaded.get(entry.name)
                if (record is not None and record[2] is not None and
                        callable(getattr(record[1],'cancel_disable_preparation',None))):
                    self._pending_disables[selection.mod_id]=(entry.name,record[1],record[2])
                    entry.generation=self._next()
                    return self.select(selection.mod_id)
            raise
        self._pending_disables.pop(selection.mod_id,None)
        return self.select(selection.mod_id)

    def poll_pending_disables(self):
        """Retry opted-in user requests only for the still-admitted owner."""
        self._check()
        from .mods import ModDisablePending
        for mod_id,(name,instance,scope) in tuple(self._pending_disables.items()):
            entry=self._entries.get(mod_id);record=self._loader._loaded.get(name)
            if entry is None or record is None or record[1] is not instance or record[2] is not scope:
                self._pending_disables.pop(mod_id,None);continue
            lifecycle=getattr(self._loader,'world_lifecycle',None)
            if lifecycle is not None:
                binding=lifecycle.bindings.get(name)
                if binding is None or binding.scope is not scope or binding.state!='bound':
                    # Retirement owns this scope now. Never dispatch ordinary
                    # disable against an old or unadmitted world.
                    self._pending_disables.pop(mod_id,None);continue
            if entry.preferences.get('enabled') is not False:
                self._pending_disables.pop(mod_id,None)
                instance.cancel_disable_preparation()
                self._loader._prepared_disable_scopes.pop(name,None)
                entry.generation=self._next();continue
            if lifecycle is not None and not lifecycle.allows(name):
                # A transient admission gap may later readmit this exact
                # owner. Keep its request and do not dispatch yet.
                continue
            try:self._loader.disable(name)
            except ModDisablePending:continue
            except Exception as error:
                self._pending_disables.pop(mod_id,None)
                entry.error=type(error).__name__+': '+str(error)
                entry.generation=self._next()
            else:self._pending_disables.pop(mod_id,None)

    def stage_enabled(self, selection, enabled):
        """Persist a desired choice without invoking any mod lifecycle callback."""
        entry = self._entry(selection)
        if type(enabled) is not bool:
            raise ManagementError('Enabled must be a boolean')
        if not enabled and entry.definition.protected:
            raise ManagementError('This core mod is protected; stop the controller to unload it')
        preferences = copy.deepcopy(entry.preferences)
        preferences.update(enabled=enabled, folder=entry.name)
        if self._settings is not None:
            self._settings.save(selection.mod_id, preferences)
        entry.preferences = preferences
        entry.generation = self._next()
        return self.select(selection.mod_id)

    def stage_saved_enabled(self, mod_id, enabled):
        """Stage an already known saved folder without importing legacy code."""
        self._check()
        identifier(mod_id)
        if type(enabled) is not bool:
            raise ManagementError('Enabled must be a boolean')
        if mod_id in self._entries:
            return self.stage_enabled(self.select(mod_id), enabled)
        if self._settings is None or mod_id not in self._settings.records():
            raise ManagementError('No saved mod identity is available for staging')
        preferences = self._settings.get(mod_id)
        folder = preferences.get('folder')
        if folder not in self.installed():
            raise ManagementError('Saved mod folder is missing')
        if not enabled and (mod_id in ('sdk.management', 'sdk.introspection') or
                folder in ('SDKManagement', 'IntrospectionHarness')):
            raise ManagementError('This core mod is protected')
        preferences['enabled'] = enabled
        self._settings.save(mod_id, preferences)
        return mod_id

    def startup_order(self):
        self._check()
        ids=list(self._settings.records()) if self._settings is not None else []
        ids.extend(key for key,entry in self._entries.items() if not entry.definition.protected)
        ids=[key for key in ids if key not in ('sdk.management','sdk.introspection')
             and not (key in self._entries and self._entries[key].definition.protected)]
        return self._startup_order.ordered(ids) if self._startup_order else list(dict.fromkeys(ids))

    def move_startup(self, selection, direction):
        entry=self._entry(selection)
        if entry.definition.protected or self._startup_order is None:
            raise ManagementError('Startup order is unavailable for this mod')
        order=self.startup_order();key=selection.mod_id
        if key not in order:order.append(key)
        if direction=='defaults':
            from .startup_order import DEFAULT_ORDER
            self._startup_order.save(DEFAULT_ORDER)
        else:
            index=order.index(key)
            target=0 if direction=='first' else max(0,index-1) if direction=='earlier' else min(len(order)-1,index+1) if direction=='later' else None
            if target is None:raise ManagementError('Unknown load-order action')
            order.pop(index);order.insert(target,key)
            # Retain temporarily uninstalled custom IDs in the mapping.
            order.extend(k for k in self._startup_order.read() if k not in order)
            self._startup_order.save(order)
        return self.startup_order().index(key)+1

    def restore_enabled(self):
        """Restore explicit saved choices once at host startup; isolate failures."""
        return {mod_id: error for mod_id, error in self.restore_enabled_steps() if error}

    def restore_enabled_steps(self):
        """Restore at most one saved mod per step, on the controller thread.

        Hosts can service UI between steps. Recheck the current preference so a
        user disabling a pending mod in that UI wins over the startup snapshot.
        """
        self._check()
        if self._settings is None:
            return
        attempted = set()
        while True:
            self._check()
            # Read current order/choices after every yield. A newly staged ID
            # can join pending startup; attempted mutations are never replayed.
            mod_id = next((key for key in self.startup_order() if key not in attempted
                and self._settings.get(key).get('enabled') is True), None)
            if mod_id is None:
                return
            attempted.add(mod_id)
            preference = self._settings.get(mod_id)
            folder = preference.get('folder')
            failure = None
            enable_ms = None
            try:
                if folder not in self.installed():
                    raise ManagementError('Saved mod folder is missing')
                selection = self.load(folder)
                if selection.mod_id != mod_id:
                    raise ManagementError('Saved mod identity does not match installed mod')
                entry = self._entry(selection)
                if not self._enabled(entry):
                    started = time.perf_counter()
                    if not hasattr(self, '_startup_activation_started'):
                        self._startup_activation_started = {}
                    self._startup_activation_started[mod_id] = started
                    try:
                        self._loader.enable(folder)
                    finally:
                        enable_ms = (time.perf_counter() - started) * 1000
                else:
                    enable_ms = 0.0
            except Exception as error:
                failure = f'{type(error).__name__}: {error}'
                if mod_id in self._entries:
                    self._entries[mod_id].error = failure
            if not hasattr(self, '_startup_enable_timings'):
                self._startup_enable_timings = {}
            self._startup_enable_timings[mod_id] = enable_ms
            yield mod_id, failure

    def unload(self, selection):
        entry = self._entry(selection)
        if entry.definition.protected:
            raise ManagementError('This core mod is protected; stop the controller to unload it')
        self._loader.unload(entry.name)

    def reload(self, selection, *, expected_sha256, changed_only=False, expected_package_sha256=None):
        entry = self._entry(selection)
        return self._loader.reload(entry.name, expected_sha256=expected_sha256,
                                   changed_only=changed_only, expected_package_sha256=expected_package_sha256)

    def reload_current(self, selection):
        """Reload the currently installed package after capturing its exact digest."""
        entry = self._entry(selection)
        if entry.definition.protected:
            raise ManagementError('This core mod cannot be reloaded')
        snapshot = self._loader._read_source(entry.name)
        return self.reload(selection, expected_sha256=snapshot[2],
                           expected_package_sha256=snapshot[3].sha256)

    def install_staged(self, selection, *, expected_sha256):
        entry = self._entry(selection)
        return self._loader.install_staged(entry.name, expected_sha256=expected_sha256)

    def option(self, selection, option_id):
        entry = self._entry(selection)
        for option in entry.definition.options:
            if option.id == option_id:
                return option.validate(entry.preferences.get('options', {}).get(option.id, option.default))
        raise ManagementError(f'Unknown option {option_id!r}')

    def set_option(self, selection, option_id, value, *, reset=False):
        entry = self._entry(selection)
        if selection.mod_id in self._dispatching:
            raise ManagementError('Recursive management dispatch is not supported')
        option = next((item for item in entry.definition.options if item.id == option_id), None)
        if option is None:
            raise ManagementError(f'Unknown option {option_id!r}')
        value = option.validate(option.default if reset else value)
        preferences = copy.deepcopy(entry.preferences)
        preferences.setdefault('options', {})[option_id] = value
        if self._settings is not None:
            self._settings.save(selection.mod_id, preferences)
        entry.preferences = preferences
        entry.error = None
        if self._enabled(entry) and option.on_change is not None:
            self._callback(selection, option.on_change, value, 'Option saved, but application failed')
        return copy.deepcopy(value)

    def stage_option(self, selection, option_id, value, *, reset=False):
        """Validate/save an option without calling its world-dependent handler."""
        entry = self._entry(selection)
        if selection.mod_id in self._dispatching:
            raise ManagementError('Recursive management dispatch is not supported')
        if type(reset) is not bool:
            raise ManagementError('Reset must be a boolean')
        option = next((item for item in entry.definition.options if item.id == option_id), None)
        if option is None:
            raise ManagementError(f'Unknown option {option_id!r}')
        value = option.validate(option.default if reset else value)
        preferences = copy.deepcopy(entry.preferences)
        preferences.setdefault('options', {})[option_id] = value
        if self._settings is not None:
            self._settings.save(selection.mod_id, preferences)
        entry.preferences = preferences
        entry.generation = self._next()
        return copy.deepcopy(value)

    def apply_options(self, name):
        self._check()
        for entry in self._entries.values():
            if entry.name == name:
                selection = self.select(entry.definition.id)
                for option in entry.definition.options:
                    if option.on_change is not None:
                        self._callback(selection, option.on_change, self.option(selection, option.id),
                                       'Applying saved option failed')
                break

    def _binding(self, entry, binding_id):
        binding = next((b for b in entry.definition.keybinds if b.id == binding_id), None)
        if binding is None:
            raise ManagementError(f'Unknown keybind {binding_id!r}')
        return binding

    def keybind(self, selection, binding_id):
        entry = self._entry(selection)
        binding = self._binding(entry, binding_id)
        return normalize_key(entry.preferences.get('keybinds', {}).get(binding.id, binding.default))

    def key_conflicts(self):
        """Report enabled mod collisions; conflicting keys are never dispatched."""
        self._check()
        keys = {}
        for mod_id, entry in self._entries.items():
            if not self._enabled(entry):
                continue
            for binding in entry.definition.keybinds:
                key = self.keybind(self.select(mod_id), binding.id)
                if key is not None:
                    keys.setdefault(key, []).append((mod_id, binding.id))
        return {key: tuple(owners) for key, owners in keys.items() if len(owners) > 1}

    def set_keybind(self, selection, binding_id, key=None, *, reset=False):
        entry = self._entry(selection)
        binding = self._binding(entry, binding_id)
        if selection.mod_id in self._dispatching:
            raise ManagementError('Recursive management dispatch is not supported')
        key = normalize_key(binding.default if reset else key)
        preferences = copy.deepcopy(entry.preferences)
        preferences.setdefault('keybinds', {})[binding.id] = key
        if self._settings is not None:
            self._settings.save(selection.mod_id, preferences)
        entry.preferences = preferences
        # Queued deliveries and rendered controls from the old map are revoked.
        entry.generation = self._next()
        return self.select(selection.mod_id)

    def key_routes(self):
        """Snapshot routing metadata; it grants no engine or callback authority.

        The native adapter must attach a session/map generation to each event.
        Delivery must call dispatch_key, which revalidates these observations.
        """
        self._check()
        conflicts = self.key_conflicts()
        routes = []
        lifecycle=getattr(self._loader,'world_lifecycle',None)
        for mod_id, entry in self._entries.items():
            if not self._enabled(entry):
                continue
            if lifecycle is not None and not lifecycle.allows(entry.name):continue
            selection = self.select(mod_id)
            for binding in entry.definition.keybinds:
                key = self.keybind(selection, binding.id)
                if key is not None and key not in conflicts:
                    routes.append((selection, binding.id, key, VIRTUAL_KEYS[key]))
        return tuple(routes)

    def dispatch_key(self, selection, binding_id, key):
        entry = self._entry(selection)
        binding = self._binding(entry, binding_id)
        key = normalize_key(key)
        if not self._enabled(entry):
            raise ManagementError('Enable the mod before dispatching its keybinds')
        if key is None or self.keybind(selection, binding_id) != key:
            raise ManagementError('Key mapping changed; discard the stale delivery')
        if key in self.key_conflicts():
            raise ManagementError('Conflicting key mapping; remap or unbind it first')
        return self._callback(selection, binding.callback, None, 'Keybind callback failed')

    def _callback(self, selection, callback, argument, phase):
        entry = self._entry(selection)
        lifecycle=getattr(self._loader,'world_lifecycle',None)
        if lifecycle is not None and not lifecycle.allows(entry.name):
            raise ManagementError('Gameplay callback is waiting for its admitted world')
        if selection.mod_id in self._dispatching:
            raise ManagementError('Recursive management dispatch is not supported')
        self._dispatching.add(selection.mod_id)
        try:
            return callback(argument)
        except BaseException as error:
            try:
                detail = str(error)[:2048]
            except BaseException:
                detail = '<exception formatting failed>'
            entry.error = f'{phase}: {type(error).__name__}: {detail}'
            raise ManagementError(entry.error) from None
        finally:
            self._dispatching.discard(selection.mod_id)

    def action_callback(self, selection, action_id, argument=None):
        """Capture a generation-checked action for native button/key frontends.

        The event is transport metadata, never an implicit mod argument. Resolve
        the action again on every delivery so a disabled/reloaded mod cannot be
        reached through a cached bound method. The frontend owns unregistration.
        """
        entry = self._entry(selection)
        if not self._enabled(entry):
            raise ManagementError('Enable the mod before binding its actions')
        if not any(action.id == action_id for action in entry.definition.actions):
            raise ManagementError(f'Unknown action {action_id!r}')
        _json_value(argument)
        if len(json.dumps(argument, ensure_ascii=True, allow_nan=False)) > 65536:
            raise ManagementError('Action arguments exceed 64 KiB')
        captured = copy.deepcopy(argument)

        def dispatch(_event=None):
            return self.invoke(selection, action_id, captured)

        return dispatch

    def invoke(self, selection, action_id, argument=None):
        entry = self._entry(selection)
        if not self._enabled(entry):
            raise ManagementError('Enable the mod before invoking its actions')
        _json_value(argument)
        if len(json.dumps(argument, ensure_ascii=True, allow_nan=False)) > 65536:
            raise ManagementError('Action arguments exceed 64 KiB')
        action = next((item for item in entry.definition.actions if item.id == action_id), None)
        if action is None:
            raise ManagementError(f'Unknown action {action_id!r}')
        return self._callback(selection, action.callback, copy.deepcopy(argument), 'Action failed')
