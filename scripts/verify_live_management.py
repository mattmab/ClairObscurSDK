"""Install a temporary management loader on the existing native console Session.

Run install(sdk) from the game Python console, then interact using real `mods`
commands. Call the returned object's finish() to verify observed effects and
remove its resources without detaching the host. This is not a relaunch test.
"""
import importlib.util
import json
from pathlib import Path
import sys
import uuid

from expedition33.settings import SettingsStore

ROOT = Path(__file__).resolve().parents[1]


class Verification:
    def __init__(self, session):
        self.session = session
        self.commands_before = set(session.console.dispatcher.command_names)
        self.hooks_before = tuple(session._hooks)
        self.output_dir = ROOT / 'evidence/management-live' / uuid.uuid4().hex
        self.output_dir.mkdir(parents=True)
        self.store = SettingsStore(self.output_dir / 'preferences.json')
        # Import a distinct candidate module; don't reload the active host's
        # loader module/classes or replace its running instances.
        name = 'expedition33._management_candidate_' + uuid.uuid4().hex
        spec = importlib.util.spec_from_file_location(name, ROOT / 'src/expedition33/mods.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        finally:
            sys.modules.pop(name, None)
        self.loader = module.ModLoader(ROOT / 'mods', settings=self.store, session=session)
        try:
            self.loader.load('SDKManagement')
            self.loader.enable('SDKManagement')
            self.loader.load('ManagementExample')
            self.original = self.loader._loaded['ManagementExample'][1]
            self.stale_selection = self.loader.registry.select('example.management')
        except BaseException:
            self.loader.close()
            raise
        self.closed = False

    def finish(self):
        try:
            statuses = {status.name: status.enabled for status in self.loader.status()}
            assert statuses == {'SDKManagement': True, 'ManagementExample': True}, statuses
            registry = self.loader.registry
            selection = registry.select('example.management')
            current = self.loader._loaded['ManagementExample'][1]
            assert current is not self.original, 'Use mods unload, then load/enable the example again'
            assert self.original.events == 1, self.original.events
            assert current.events == 1, current.events
            assert current.label == 'Live menu persistence', current.label
            assert self.store.get('example.management')['options']['label'] == current.label
            try:
                registry.invoke(self.stale_selection, 'observe')
            except RuntimeError:
                pass
            else:
                raise AssertionError('Stale selection remained callable')
            assert self.session.console.dispatcher.namespace['management_python_probe'] == 42
            result = {'pid': self.session.pid, 'original_hook_events': self.original.events,
                      'reloaded_hook_events': current.events, 'saved_label': current.label,
                      'stale_selection_rejected': True, 'console_menu_live': True,
                      'borrowed_session': True, 'umg_tested': False,
                      'native_key_dispatch_tested': False, 'relaunch_tested': False}
        finally:
            self.close()
        assert set(self.session.console.dispatcher.command_names) == self.commands_before
        assert tuple(self.session._hooks) == self.hooks_before
        actor = self.session.find_object('Default__Actor')
        assert self.session.call(actor, 'Actor.IsActorBeingDestroyed') is False
        result['commands_and_hooks_restored'] = True
        result['host_session_usable'] = True
        path = self.output_dir / 'result.json'
        path.write_text(json.dumps(result, indent=2), encoding='utf-8')
        result['evidence'] = str(path)
        return result

    def close(self):
        if not self.closed:
            self.closed = True
            self.loader.close()


def install(session):
    return Verification(session)
