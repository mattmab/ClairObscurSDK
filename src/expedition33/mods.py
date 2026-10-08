"""Explicit loading of trusted local Python mods; this is not a sandbox.

Enabled mods own resource scopes on one loader-owned Session. Disabling one mod
does not detach another mod's transport or console. No sys.path changes occur.
"""
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import threading
import uuid

from .sdk import Session
from ._scope import SessionScope


class ModError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModStatus:
    name: str
    enabled: bool


def _error(phase, error):
    try:
        detail = str(error)[:4096]
    except BaseException:
        detail = '<exception formatting failed>'
    return ModError(f'Mod {phase} failed: {type(error).__name__}: {detail}')


class ModLoader:
    def __init__(self, root):
        self.root = Path(root).resolve(strict=True)
        self._loaded = {}
        self._owner = threading.get_ident()
        self._session = None
        self._polling = False
        self._disabling = set()

    def _check_thread(self):
        if threading.get_ident() != self._owner:
            raise ModError('Mods must be managed on their owning Python thread')

    def discover(self):
        self._check_thread()
        return tuple(sorted(path.parent.name for path in self.root.glob('*/mod.py')
                            if path.resolve().is_relative_to(self.root)))

    def load(self, name):
        self._check_thread()
        if name in self._loaded:
            return
        if name not in self.discover():
            raise ModError(f'No local mod named {name!r}')
        path = (self.root / name / 'mod.py').resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise ModError('Mod entry point is outside the configured directory')
        key = '_expedition33_mod_' + uuid.uuid4().hex
        spec = importlib.util.spec_from_file_location(key, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            spec.loader.exec_module(module)
            instance = module.Mod()
            if not callable(getattr(instance, 'enable', None)) or not callable(getattr(instance, 'disable', None)):
                raise TypeError('Mod must define enable(session) and disable()')
        except BaseException as error:
            sys.modules.pop(key, None)
            raise _error('load', error) from None
        self._loaded[name] = [key, instance, None]

    def enable(self, name, *, console=False, console_key=None):
        record = self._record(name)
        if record[2] is not None:
            return
        if self._session is None:
            self._session = Session()
        session = SessionScope(self._session)
        record[2] = session
        try:
            if console:
                self._session.console.enable()
                if console_key is not None:
                    self._session.console.set_toggle_key(console_key)
                # Preserve the single-mod convenience alias without replacing
                # another enabled mod's binding. Other modules can expose names.
                if 'my_mod' not in self._session.console.dispatcher.namespace:
                    session.console.expose('my_mod', record[1])
            record[1].enable(session)
        except BaseException as error:
            failure = _error('enable', error)
            try:
                self.disable(name)
            except ModError as cleanup:
                failure = ModError(f'{failure}; cleanup: {cleanup}')
            raise failure from None

    def disable(self, name):
        record = self._record(name)
        if name in self._disabling:
            raise ModError('Recursive mod disable is not supported')
        session = record[2]
        if session is None:
            return
        self._disabling.add(name)
        failure = None
        try:
            record[1].disable()
        except BaseException as error:
            failure = _error('disable', error)
        finally:
            try:
                session.close()
            except BaseException as error:
                close_error = _error('session cleanup', error)
                failure = ModError(f'{failure}; {close_error}') if failure else close_error
            record[2] = None
            if not any(value[2] is not None for value in self._loaded.values()):
                shared, self._session = self._session, None
                try:
                    shared.close()
                except BaseException as error:
                    close_error = _error('shared session cleanup', error)
                    failure = ModError(f'{failure}; {close_error}') if failure else close_error
            self._disabling.discard(name)
        if failure:
            raise failure from None

    def poll(self, name=None):
        """Drain shared transport once, then poll selected/all enabled mods."""
        self._check_thread()
        if self._polling:
            raise ModError('Recursive mod polling is not supported')
        selected = tuple(self._loaded) if name is None else (name,)
        if name is not None and self._record(name)[2] is None:
            raise ModError(f'Mod {name!r} is disabled')
        shared = self._session
        if shared is None:
            return 0
        self._polling = True
        try:
            shared.console.poll()
            # Console actions may disable the last mod and close this session.
            if self._session is not shared:
                return 0
            delivered = shared.poll()
            failures = []
            records = [(key, self._loaded.get(key)) for key in selected]
            for key, record in records:
                if record is None or self._loaded.get(key) is not record or record[2] is None:
                    continue
                callback = getattr(record[1], 'poll', None)
                if callback is not None:
                    try:
                        callback()
                    except BaseException as error:
                        failures.append(str(_error('poll', error)))
            if failures:
                raise ModError('; '.join(failures))
            return delivered
        finally:
            self._polling = False

    def unload(self, name):
        self._check_thread()
        if name not in self._loaded:
            return
        try:
            self.disable(name)
        finally:
            key, _, _ = self._loaded.pop(name)
            sys.modules.pop(key, None)

    def _record(self, name):
        self._check_thread()
        try:
            return self._loaded[name]
        except KeyError:
            raise ModError(f'Mod {name!r} is not loaded') from None

    def status(self):
        self._check_thread()
        return tuple(ModStatus(name, record[2] is not None) for name, record in self._loaded.items())

    def close(self):
        self._check_thread()
        failures = []
        for name in tuple(self._loaded):
            try:
                self.unload(name)
            except ModError as error:
                failures.append(str(error))
        if failures:
            raise ModError('; '.join(failures))

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
