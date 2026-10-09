"""Shared mod definitions, preferences and owner-thread action dispatch.

No engine/UI dependency. The loader owns lifecycle state; frontends receive copies
and generation tokens, never mod instances or engine pointers.
"""
import copy
from dataclasses import dataclass, field
import json
import math
import threading

from .settings import identifier, _json_value


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
class ModDefinition:
    id: str
    title: str
    description: str = ''
    author: str = ''
    version: str = ''
    protected: bool = False
    options: tuple[Option, ...] = ()
    actions: tuple[Action, ...] = ()


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
        self._generation = 0
        self._dispatching = set()

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
        for collection, expected in ((definition.options, Option), (definition.actions, Action)):
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
                if expected is Action and not callable(item.callback):
                    raise ManagementError('Action callback must be callable')
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
        self._entries[definition.id] = _Entry(name, definition, self._next(), preferences)

    def unregister(self, name):
        self._check()
        for mod_id, entry in tuple(self._entries.items()):
            if entry.name == name:
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
        return {'id': definition.id, 'name': definition.title, 'folder': entry.name,
                'description': definition.description, 'author': definition.author,
                'version': definition.version, 'protected': definition.protected,
                'enabled': self._enabled(entry), 'generation': entry.generation,
                'error': entry.error, 'persistence': self._settings is not None,
                'options': [{'id': option.id, 'title': option.title, 'kind': option.kind,
                    'value': option.validate(entry.preferences.get('options', {}).get(option.id, option.default)),
                    'default': copy.deepcopy(option.default), 'minimum': option.minimum,
                    'maximum': option.maximum, 'choices': list(option.choices)} for option in definition.options],
                'actions': [{'id': action.id, 'title': action.title} for action in definition.actions]}

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

    def set_enabled(self, selection, enabled):
        entry = self._entry(selection)
        if type(enabled) is not bool:
            raise ManagementError('Enabled must be a boolean')
        if not enabled and entry.definition.protected:
            raise ManagementError('This core mod is protected; stop the controller to unload it')
        operation = self._loader.enable if enabled else self._loader.disable
        operation(entry.name)
        # Enabled state belongs only to the loader. Preference restoration is not
        # automatic startup execution of arbitrary mods.
        return self.select(selection.mod_id)

    def unload(self, selection):
        entry = self._entry(selection)
        if entry.definition.protected:
            raise ManagementError('This core mod is protected; stop the controller to unload it')
        self._loader.unload(entry.name)

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

    def _callback(self, selection, callback, argument, phase):
        entry = self._entry(selection)
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
