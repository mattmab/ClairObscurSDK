"""Explicit loading of trusted local Python mods; this is not a sandbox.

Enabled mods own resource scopes on one loader-owned Session. Disabling one mod
does not detach another mod's transport or console. No sys.path changes occur.
"""
from dataclasses import dataclass
import importlib.util
import hashlib
import logging
import time
from pathlib import Path
import sys
import threading
import uuid

from .sdk import Session
from ._scope import SessionScope
from .management import ModDefinition, Registry
from .mod_imports import PackageSources, OwnedImports


class ModError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModStatus:
    name: str
    enabled: bool
    cleanup_error: str | None = None
    source_sha256: str | None = None
    package_sha256: str | None = None


def _error(phase, error):
    try:
        detail = str(error)[:4096]
    except BaseException:
        detail = '<exception formatting failed>'
    return ModError(f'Mod {phase} failed: {type(error).__name__}: {detail}')


class ModLoader:
    def __init__(self, root, *, settings=None, session=None, poll_diagnostics=False):
        self.root = Path(root).resolve(strict=True)
        self._loaded = {}
        self._owner = threading.get_ident()
        # An explicitly borrowed Session remains owned by its original host.
        self._session = session
        self._borrowed = session is not None
        self._polling = False
        self._poll_diagnostics = bool(poll_diagnostics)
        self._poll_timings = {}
        self._poll_sample_count = 0
        self._keys = None
        self._disabling = set()
        self._enabling = set()
        # A failed cleanup may have external effects beyond SDK-owned resources.
        # Keep the failure across unload/load; only a fresh controller can reset it.
        self._cleanup_failures = {}
        self._source_digests = {}
        self._imports = {}
        self._reloading = False
        self._installing = None
        self.stop_requested = False
        self.registry = Registry(self, settings)
        from .introspection.agent import AgentBridge
        self.actions = AgentBridge(self.registry, self.root.parent / 'logs' / 'sdk.log')
        from .mod_lock import ModRootLock
        self._root_lock = ModRootLock(self.root)
        self._closed = False

    def request_stop(self):
        """Ask the owning host loop to exit after its current dispatch completes."""
        self._check_thread()
        self.stop_requested = True

    def _check_thread(self):
        if threading.get_ident() != self._owner:
            raise ModError('Mods must be managed on their owning Python thread')
        if self._closed:
            raise ModError('Mod loader is closed')

    def discover(self):
        self._check_thread()
        return tuple(sorted(path.parent.name for path in self.root.glob('*/mod.py')
                            if path.resolve().is_relative_to(self.root)))

    def load(self, name):
        self._check_thread()
        self._check_cleanup(name)
        self._check_install(name)
        if name in self._loaded:
            return
        self._load_source(name, self._read_source(name))

    def _read_source(self, name):
        if name not in self.discover():
            raise ModError(f'No local mod named {name!r}')
        path = (self.root / name / 'mod.py').resolve(strict=True)
        if not path.is_relative_to(self.root):
            raise ModError('Mod entry point is outside the configured directory')
        with path.open('rb') as stream:
            source = stream.read(4 * 1024 * 1024 + 1)
        if len(source) > 4 * 1024 * 1024:
            raise ModError('Mod entry point exceeds 4 MiB')
        try:
            code = compile(source, str(path), 'exec', dont_inherit=True)
        except BaseException as error:
            raise _error('compile', error) from None
        digest = hashlib.sha256(source).hexdigest()
        try:
            package = PackageSources(path, code, digest)
        except BaseException as error:
            raise _error('package preflight', error) from None
        return path, code, digest, package

    def _load_source(self, name, snapshot):
        path, code, digest, package = snapshot
        key = '_expedition33_mod_' + uuid.uuid4().hex
        imports = OwnedImports(key, package)
        imports.install()
        spec = imports.find_spec(key)
        module = importlib.util.module_from_spec(spec)
        sys.modules[key] = module
        try:
            # Execute exactly the captured bytes; timestamp/size-matched .pyc
            # files and edits during cleanup must not substitute another source.
            imports.exec_module(module)
            instance = module.Mod()
            if not callable(getattr(instance, 'enable', None)) or not callable(getattr(instance, 'disable', None)):
                raise TypeError('Mod must define enable(session) and disable()')
            describe = getattr(instance, 'management', None)
            definition = describe() if describe is not None else ModDefinition(name.lower(), name)
            self.registry.register(name, definition)
        except BaseException as error:
            imports.close()
            raise _error('load', error) from None
        self._loaded[name] = [key, instance, None]
        self._source_digests[name] = digest
        self._imports[name] = imports

    def reload(self, name, *, expected_sha256, changed_only=False, expected_package_sha256=None):
        """Replace trusted installed Python sources; global dependencies/core stay loaded.

        Compilation and digest validation precede cleanup. After cleanup starts,
        failures are reported without replay or automatic rollback/re-enable.
        """
        record = self._record(name)
        self._check_cleanup(name)
        self._check_install(name)
        if type(changed_only) is not bool:
            raise ModError('changed_only must be bool')
        if (self._reloading or name in self._enabling or name in self._disabling or
                name in ('SDKManagement', 'IntrospectionHarness')):
            raise ModError('Cannot reload a servicing core mod or active lifecycle transition')
        row = next(v for v in self.registry.views() if v['folder'] == name)
        if row['protected'] or row['id'] in self.registry._dispatching:
            raise ModError('Cannot reload a protected mod or its executing management action')
        if (type(expected_sha256) is not str or len(expected_sha256) != 64 or
                any(c not in '0123456789abcdef' for c in expected_sha256)):
            raise ModError('Supply a lowercase SHA256 of the installed mod.py')
        snapshot = self._read_source(name)
        if snapshot[2] != expected_sha256:
            raise ModError('expected_sha256 does not match installed mod.py')
        package = snapshot[3]
        old_package = self._imports[name].sources
        if package.has_dependencies or old_package.has_dependencies or expected_package_sha256 is not None:
            if expected_package_sha256 != package.sha256:
                raise ModError('expected_package_sha256 must match the captured Python source tree: ' + package.sha256)
        if changed_only and old_package.sha256 == package.sha256:
            return dict(changed=False, mod=name, version=row['version'],
                        enabled=record[2] is not None, sha256=snapshot[2], package_sha256=package.sha256)
        enabled = record[2] is not None
        # Do not use unload's finally path: failure must stop replacement.
        self._reloading = True
        try:
            self.disable(name)
            self.unload(name)
            self._load_source(name, snapshot)
            if enabled:
                self.enable(name)
        finally:
            self._reloading = False
            # Preserve persistent Python/transport while replacing the sole mod.
            # A failed replacement with no remaining users still closes normally.
            if (not self._borrowed and self._session is not None and
                    not any(value[2] is not None for value in self._loaded.values())):
                shared, self._session = self._session, None
                shared.close()
        view = next(v for v in self.registry.views() if v['folder'] == name)
        return dict(changed=True, mod=name, version=view['version'],
                    enabled=view['enabled'], sha256=snapshot[2], package_sha256=package.sha256)

    def _check_install(self, name):
        if self._installing == name:
            return
        from .mod_install import inspect_transaction
        transactions = self.root / '.transactions'
        if not transactions.exists():
            return
        if transactions.is_symlink() or transactions.is_junction():
            raise ModError('Transaction directory is redirected')
        for index, directory in enumerate(transactions.iterdir()):
            if index >= 1024:
                raise ModError('Transaction history exceeds inspection limit')
            state = inspect_transaction(self.root, directory.name)
            if state['mod'] == name and (state['phase'] not in ('preparing', 'prepared', 'committed', 'rolled_back') or
                                         state['phase'] == 'committed' and state.get('error')):
                raise ModError('Unresolved installation requires inspection: ' + state['journal'])

    def install_staged(self, name, *, expected_sha256):
        """Activate fixed staging/<folder>.zip after cleanup; retain backup/journal."""
        record = self._record(name)
        self._check_cleanup(name)
        self._check_install(name)
        row = next(v for v in self.registry.views() if v['folder'] == name)
        if (self._reloading or name in self._enabling or name in self._disabling or
                name in ('SDKManagement', 'IntrospectionHarness') or row['protected'] or
                row['id'] in self.registry._dispatching):
            raise ModError('Cannot install over a protected/core mod or active lifecycle transition')
        from .mod_install import PreparedInstall
        transaction = PreparedInstall(self.root, name, self.root.parent / 'staging' / (name + '.zip'),
                                      expected_sha256)
        enabled = record[2] is not None
        self._reloading, self._installing = True, name
        def cleanup():
            self.disable(name)
            self.unload(name)
            return True
        try:
            transaction.activate(cleanup)
            snapshot = self._read_source(name)
            expected = transaction.candidate.summary()
            entry_digest = next(f['sha256'] for f in expected['files'] if f['path'] == 'mod.py')
            if snapshot[2] != entry_digest or snapshot[3].sha256 != expected['python_package_sha256']:
                raise ModError('Installed source changed before activation')
            transaction._record('activating')
            self._load_source(name, snapshot)
            if enabled:
                self.enable(name)
            transaction._record('committed')
            return transaction.inspect()
        except BaseException as error:
            transaction._failed(error)
            raise
        finally:
            self._reloading, self._installing = False, None
            if (not self._borrowed and self._session is not None and
                    not any(value[2] is not None for value in self._loaded.values())):
                shared, self._session = self._session, None
                shared.close()

    def enable(self, name, *, console=False, console_key=None):
        record = self._record(name)
        self._check_cleanup(name)
        self._check_install(name)
        if name in self._enabling or name in self._disabling:
            raise ModError('Recursive mod lifecycle transition is not supported')
        if record[2] is not None:
            return
        if self._session is None:
            self._session = Session()
        session = SessionScope(self._session,lease_owner=name)
        session.mods = self.registry
        from .introspection.agent import ScopedActions
        session.actions = ScopedActions(self.actions, session, name)
        record[2] = session
        self.registry.changed(name)
        self._enabling.add(name)
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
            self.registry.apply_options(name)
        except BaseException as error:
            failure = _error('enable', error)
            self._enabling.discard(name)
            try:
                self.disable(name)
            except ModError as cleanup:
                failure = ModError(f'{failure}; cleanup: {cleanup}')
            raise failure from None
        finally:
            self._enabling.discard(name)

    def disable(self, name):
        record = self._record(name)
        if name in self._disabling or name in self._enabling:
            raise ModError('Recursive mod disable is not supported')
        session = record[2]
        if session is None:
            return
        self._disabling.add(name)
        self.registry.changed(name)
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
            if not self._borrowed and not self._reloading and not any(value[2] is not None for value in self._loaded.values()):
                shared, self._session = self._session, None
                try:
                    shared.close()
                except BaseException as error:
                    close_error = _error('shared session cleanup', error)
                    failure = ModError(f'{failure}; {close_error}') if failure else close_error
            self._disabling.discard(name)
        if failure:
            self._cleanup_failures[name] = str(failure)
            raise failure from None

    def _check_cleanup(self, name):
        if name in self._cleanup_failures:
            raise ModError('Previous cleanup failed for ' + repr(name) +
                           '; restart the controller before loading/enabling it: ' +
                           self._cleanup_failures[name])

    def _record_poll_timing(self, phase, elapsed):
        sample = self._poll_timings.setdefault(phase, {'count': 0, 'total_ms': 0., 'max_ms': 0.})
        milliseconds = elapsed * 1000.
        sample['count'] += 1
        sample['total_ms'] += milliseconds
        sample['max_ms'] = max(sample['max_ms'], milliseconds)

    def _timed_poll(self, phase, callback):
        started = time.perf_counter()
        try:
            return callback()
        finally:
            self._record_poll_timing(phase, time.perf_counter() - started)

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
        started = time.perf_counter() if self._poll_diagnostics else None
        try:
            if self._poll_diagnostics:
                self._timed_poll('shared.console.poll', shared.console.poll)
            else:
                shared.console.poll()
            # Console actions may disable the last mod and close this session.
            if self._session is not shared:
                return 0
            delivered = self._timed_poll('shared.poll', shared.poll) if self._poll_diagnostics else shared.poll()
            if self._session is not shared or getattr(shared, '_closed', False):
                return delivered
            from ._session import supports_keys
            if supports_keys(getattr(shared, '_transport', None)):
                from .keybind_service import KeybindService
                if self._keys is None or self._keys.session is not shared:
                    if self._keys is not None:
                        self._keys.close()
                    self._keys = KeybindService(shared, self.registry)
                delivered += self._timed_poll('keys.poll', self._keys.poll) if self._poll_diagnostics else self._keys.poll()
                if self._session is not shared:
                    return delivered
            failures = []
            records = [(key, self._loaded.get(key)) for key in selected]
            for key, record in records:
                if record is None or self._loaded.get(key) is not record or record[2] is None:
                    continue
                callback = getattr(record[1], 'poll', None)
                if callback is not None:
                    try:
                        if self._poll_diagnostics:
                            self._timed_poll('mod.' + key, callback)
                        else:
                            callback()
                    except BaseException as error:
                        failures.append(str(_error('poll', error)))
            if failures:
                raise ModError('; '.join(failures))
            return delivered
        finally:
            self._polling = False
            if self._poll_diagnostics:
                self._record_poll_timing('total', time.perf_counter() - started)
                self._poll_sample_count += 1
                if self._poll_sample_count == 30:
                    logging.getLogger(__name__).info('Mod poll latency (30 polls): %s', self._poll_timings)
                    self._poll_timings = {}
                    self._poll_sample_count = 0

    def unload(self, name):
        self._check_thread()
        if name in self._disabling or name in self._enabling:
            raise ModError('Recursive mod lifecycle transition is not supported')
        if name not in self._loaded:
            return
        try:
            self.disable(name)
        finally:
            key, _, _ = self._loaded.pop(name)
            self.registry.unregister(name)
            sys.modules.pop(key, None)
            self._imports.pop(name).close()
            self._source_digests.pop(name, None)

    def _record(self, name):
        self._check_thread()
        try:
            return self._loaded[name]
        except KeyError:
            raise ModError(f'Mod {name!r} is not loaded') from None

    def status(self):
        self._check_thread()
        return tuple(ModStatus(name, record[2] is not None and name not in self._enabling
                               and name not in self._disabling,
                               self._cleanup_failures.get(name), self._source_digests.get(name),
                               self._imports[name].sources.sha256)
                     for name, record in self._loaded.items())

    def close(self):
        if self._closed:
            return
        self._check_thread()
        failures = []
        if self._keys is not None:
            try:
                self._keys.close()
            except BaseException as error:
                failures.append(str(_error('keybind cleanup', error)))
        for name in tuple(self._loaded):
            try:
                self.unload(name)
            except ModError as error:
                failures.append(str(error))
        self.actions.close()
        self._closed = True
        self._root_lock.close()
        if failures:
            raise ModError('; '.join(failures))

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        self.close()
