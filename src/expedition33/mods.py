"""Explicit loading of trusted local Python mods; this is not a sandbox.

Each enabled mod owns a Session. This first runtime supports one enabled mod at
a time; its own subscribers may share that session. No sys.path changes occur.
"""
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import threading
import uuid

from .sdk import Session


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

    def enable(self, name):
        record = self._record(name)
        if record[2] is not None:
            return
        if any(value[2] is not None for value in self._loaded.values()):
            raise ModError('This runtime currently supports one enabled mod at a time')
        session = Session()
        record[2] = session
        try:
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
        session = record[2]
        if session is None:
            return
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
        if failure:
            raise failure from None

    def poll(self, name):
        record = self._record(name)
        if record[2] is None:
            raise ModError(f'Mod {name!r} is disabled')
        return record[2].poll()

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
