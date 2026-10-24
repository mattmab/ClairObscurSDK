"""Execute the actual release host with process/native boundaries replaced."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import tempfile
import sys
import threading
import unittest
from contextlib import ExitStack,nullcontext
from unittest.mock import patch

import expedition33.sdk as sdk
from expedition33 import mods, settings, mod_lock, release_mods, release_startup
from expedition33 import lease_policy, startup_order
from expedition33 import world_admission
from expedition33 import core_startup
from expedition33 import controller_commands
def candidate_module(name):
    path=Path(__file__).resolve().parents[1]/('src/expedition33/'+name+'.py')
    if not path.exists():path=Path(sdk.__file__).resolve().parent/(name+'.py')
    spec=importlib.util.spec_from_file_location('expedition33.'+name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    return module
admission_monitor=candidate_module('admission_monitor')
candidate_module('ui_shell_proof')
world_admission=candidate_module('world_admission')
ui_admission=candidate_module('ui_admission')
process_ui=candidate_module('process_ui')
process_title_ui=candidate_module('process_title_ui')
process_console=candidate_module('process_console')
console_startup=candidate_module('console_startup')

ROOT = Path(sdk.__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('early_host_monitor_target', Path(__file__).resolve().parents[1]/'scripts/run_release_sdk.py')
host = importlib.util.module_from_spec(spec)
spec.loader.exec_module(host)


class HostTests(unittest.TestCase):
    def test_world_loader_cleanup_ack_precedes_process_shell_close(self):
        events=self.run_host(lambda call:True)
        self.assertLess(events.index('loader.close'),events.index('title.close'))
    def test_known_read_worker_barrier_keeps_transport_poll_alive_before_cleanup(self):
        events=self.run_host(lambda call:True,shutdown_pending=2)
        self.assertEqual(events.count('loader.pending'),2)
        self.assertLess(events.index('loader.pending'),events.index('session.transport.poll',events.index('loader.pending')))
        self.assertLess(events.index('loader.close'),events.index('title.close'))
    def test_unknown_loader_cleanup_does_not_close_process_shell_but_closes_readers(self):
        events=[]
        with self.assertRaisesRegex(mods.ModError,'World cleanup unknown'):
            self.run_host(lambda call:True,close_failure='loader',commands=True,recorded_events=events)
        self.assertNotIn('title.close',events)
        for event in ('monitor.close','observer.close','server.close','session.close'):
            self.assertIn(event,events)
    def test_bootstrap_default_arguments_enter_early_path_without_explicit_flag(self):
        events=self.run_host(lambda call:False,title=True,console_ready=True,early_flag=False)
        self.assertIn('console.register.startuptiming',events)
        self.assertIn('prepared',events);self.assertIn('console.enable',events)
        self.assertIn('title.tick.True',events)
        self.assertNotIn('gameplay.enable.0',events);self.assertNotIn('poll',events)

    def test_ui_can_route_back_to_title_after_gameplay_polling_latch(self):
        events=self.run_host(lambda call:call<5,title=True)
        self.assertIn('console.world_route',events)
        self.assertIn('console.title_route',events)
        self.assertIn('title.tick.True',events)
        # This test asserts UI/console routing only. Existing legacy gameplay
        # retirement is intentionally not inferred from an inactive packet.
        self.assertIn('poll',events)

    def run_host(self, readiness, *, restore_count=1, title=False, staged_count=1,
                 commands=False, close_failure=None, recorded_events=None,console_ready=None,early_flag=True, cleanup_ready=True, foreground=None, release_after=None, shutdown_pending=0):
        events = [] if recorded_events is None else recorded_events
        desired_records=['gameplay']
        clock = [0.]
        def sleep(seconds): clock[0] += max(seconds, .3)
        class Session:
            @property
            def pid(self):
                if threading.get_ident()!=self.owner:
                    raise RuntimeError('Session pid belongs to its owner thread')
                return 7
            def __init__(self, **kwargs):
                self.owner=threading.get_ident()
                self.console = N(_enabled=False,write=lambda text:events.append('console.info'),
                    poll=lambda:events.append('console.poll'),
                    register=lambda name,callback,owner:events.append('console.register.'+name))
                def enable():
                    self.console._enabled = True
                    events.append('console.enable')
                self.console.enable = enable
            def poll(self):events.append('session.transport.poll')
            def __enter__(self): events.append('session.open'); return self
            def __exit__(self, *args): events.append('session.close')
        class Store:
            def __init__(self, path): pass
            def get(self, key):
                return dict(enabled=True, folder='Gameplay' if key=='gameplay' else key)
        class Registry:
            def __init__(self, loader): self.loader = loader
            def startup_order(self): return tuple(desired_records)
            def load(self, name):
                events.append('load.'+name)
                self.loader._loaded[name] = [None, N(native=N(travel_recovery_pending=False), menu=object(), prepare=lambda: events.append('management.prepare')), None]
                return name
            def views(self):
                return [dict(folder=name, id=name, protected=name=='SDKManagement') for name in self.loader._loaded]
            def set_enabled(self, name, enabled): events.append('enable.'+name)
            def restore_enabled_steps(self):
                events.append('progress.total.'+str(self._startup_progress['total']))
                for index in range(restore_count):
                    events.append('gameplay.enable.'+str(index))
                    yield ('gameplay', None)
        class Coordinator:
            current_token=None;ready=False;ever_admitted=False
            def __init__(self):self.cleanup_ready=True
            def observe(self,value=None,*,title=False):
                self.ready=False
                if title:self.current_token=None;return
                if value is None or value.state!='world_ready':return
                if value.activation_ready:
                    if self.current_token is not None and self.current_token!=value.token:self.cleanup_ready=cleanup_ready
                    self.current_token=value.token;self.ever_admitted=True
                self.ready=self.current_token==value.token
        class Loader:
            last = None
            def __init__(self, *args, **kwargs):
                Loader.last = self
                self._loaded = {}
                self.registry = Registry(self)
                self.stop_requested = False
                self.polls = 0
                self.session = kwargs['session']
            def install_world_lifecycle(self):self.world_lifecycle=Coordinator();return self.world_lifecycle
            def __enter__(self): return self
            def close(self):
                if getattr(self,'closed',False):return
                if close_failure=='loader':raise mods.ModError('World cleanup unknown; owner retained')
                attempts=getattr(self,'close_attempts',0);self.close_attempts=attempts+1
                if attempts<shutdown_pending:
                    events.append('loader.pending')
                    raise mods.ModDisablePending('read worker finishing')
                events.append('loader.close');self.closed=True
            def __exit__(self,*args):self.close()
            def request_stop(self):self.stop_requested=True
            def discover(self): return ('SDKManagement', 'Prepared', 'Legacy', 'IntrospectionHarness')
            def status(self):return ()
            def prepare_startup(self, name, **kwargs):
                events.append('prepare.attempt.'+name)
                if name=='Prepared': events.append('prepared'); return True
                if name=='SDKManagement': return True
                return False
            def poll(self):
                self.polls += 1
                if release_after is not None and self.polls>=release_after:self.world_lifecycle.cleanup_ready=True
                events.append('poll')
                events.append('ui.'+str(self.session._menu_readiness()))
        class Kernel:
            turns=0
            def WaitForSingleObject(self, *args):
                self.turns+=1
                return 0 if self.turns>10 else 258
            def CloseHandle(self, handle): events.append('handle.close')
        class Lock:
            def __init__(self, *args): pass
            def close(self): events.append('lock.close')
        class Gate:
            def pending(self, now): return False
            def arm(self, *args): pass
        calls = [0]
        def ui_ready(pid):
            events.append('menu.ready')
            return True
        def gameplay_ready(pid):
            return readiness(calls[0])
        class Observer:
            def __init__(self,pid):events.append('observer.open')
            def prepare(self):events.append('observer.worker.prepare')
            def observe(self):
                events.append('foreground.observe')
                calls[0]+=1
                value=(foreground or readiness)(calls[0])
                if type(value) is bool:
                    value=world_admission.Admission('world_ready' if value else 'inactive',
                        'test',('epoch',) if value else None,value)
                events.append('admission.'+value.state)
                return value
            def observe_activation(self):return self.observe()
            def close(self):
                events.append('observer.close')
                if close_failure=='observer':raise RuntimeError('observer cleanup failed')
        class Monitor:
            def __init__(self,factory):
                events.append('monitor.open');self.sequence=0
                failures=[]
                def create_on_worker():
                    try:factory().close()
                    except BaseException as error:failures.append(error)
                worker=threading.Thread(target=create_on_worker)
                worker.start();worker.join()
                if failures:raise failures[0]
            def snapshot(self):
                self.sequence+=1
                calls[0]+=1
                value=readiness(calls[0])
                if type(value) is bool:
                    value=world_admission.Admission('world_ready' if value else 'inactive',
                        'test',('epoch',) if value else None,value)
                events.append('admission.'+value.state)
                return N(sequence=self.sequence,admission=N(admission=value,
                    menu_ready=True if value.state=='world_ready' else False if value.state in ('inactive','loading') else None,
                    title_ready=title if value.state=='inactive' else None if value.state=='observation_pending' else False))
            def close(self):
                events.append('monitor.close')
                if close_failure=='monitor':raise RuntimeError('monitor cleanup failed')
                return True
        class TitleDriver:
            def __init__(self,*args):self.active=False;self.gameplay_ui_ready=False;self.service=None;self.context=None
            def prepare_queries(self):events.append('ui.reads.prepared')
            def close_queries(self):events.append('ui.reads.close')
            def _read_operation(self):return nullcontext()
            @property
            def title_cleanup_ready(self):return not self.active
            def observe(self,packet):
                ready=None if packet is None else packet.title_ready
                if packet is not None and packet.admission.activation_ready:
                    ready=False;self.gameplay_ui_ready=True;self.context=N(kind='world')
                elif ready is True:
                    self.context=N(kind='title');self.gameplay_ui_ready=False
                self.poll(ready)
            def poll(self,ready):
                events.append('title.tick.'+str(ready))
                if ready is True:self.active=True
                if ready is True:desired_records[:]=['gameplay'+str(i) for i in range(staged_count)]
                elif ready is False and self.active:
                    events.append('title.cleanup');self.active=False
            def close(self):
                events.append('title.close')
                if close_failure=='title':raise RuntimeError('title native attachment acknowledgement unknown')
                self.active=False
                return True
        class Server:
            def __init__(self,*args,**kwargs):events.append('server.open')
            def write_connection(self,*args):pass
            def poll(self):pass
            def close(self):events.append('server.close')
        class ConsoleDriver:
            def __init__(self,session,menu):self.session=session
            def world_active(self):events.append('console.world_route')
            def title_active(self):events.append('console.title_route')
            def enable_for_title(self,ready):
                if ready is True and not self.session.console._enabled:self.session.console.enable()
            def poll(self):
                if self.session.console._enabled:events.append('title.console.poll')
        class ConsoleReadiness:
            def __init__(self,pid):pass
            def ready(self):return title if console_ready is None else console_ready
            def close(self):events.append('console.worker.close');return True
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            boundaries=(patch.object(process_console.StartupConsoleInfo,'begin_world_cycle',lambda self:events.append('cycle.begin'),create=True),patch.object(host, 'ROOT', Path(temporary)),
             patch.object(host, 'verify_install', return_value=dict(version='0.1.0-rc17')), \
             patch.object(host, 'game_handle', return_value=(Kernel(), 7)), \
             patch.object(host.logging, 'basicConfig'), \
             patch.object(host.logging, 'FileHandler'), \
             patch.object(host.time, 'sleep', side_effect=sleep), \
             patch.object(host.time, 'monotonic', side_effect=lambda: clock[0]), \
             patch.object(host.sys, 'argv', ['host', '--game-pid', '7']+(['--early-init'] if early_flag else [])+(['--commands'] if commands else [])), \
             patch.object(sdk, 'Session', Session), \
             patch.object(sdk, 'SessionTransport'), \
             patch.object(mods, 'ModLoader', Loader), \
             patch.object(settings, 'SettingsStore', Store), \
             patch.object(mod_lock, 'ModRootLock', Lock), \
             patch.object(release_mods, 'materialize', return_value=Path(temporary)), \
             patch.object(release_startup, 'bootstrap_ready', return_value=True), \
             patch.object(core_startup, 'core_bootstrap_ready', return_value=True), \
             patch.object(release_startup, 'attachment_ready', side_effect=ui_ready), \
             patch.object(release_startup, 'menu_ready', side_effect=ui_ready), \
             patch.object(release_startup, 'gameplay_ready', side_effect=gameplay_ready), \
             patch.object(world_admission, 'WarmAdmissionObserver', Observer), \
             patch.object(admission_monitor, 'ReadOnlyAdmissionMonitor', Monitor), \
             patch.object(process_ui,'ProcessUI',TitleDriver), \
             patch.object(controller_commands,'CommandServer',Server), \
             patch.object(process_console,'ProcessConsole',ConsoleDriver), \
             patch.object(console_startup,'ConsoleReadiness',ConsoleReadiness), \
             patch.object(lease_policy, 'configure'), \
             patch.object(startup_order, 'StartupGate', Gate))
            for boundary in boundaries:stack.enter_context(boundary)
            host.main()
        return events

    def test_console_prerequisites_can_attach_before_title_without_gameplay(self):
        events=self.run_host(lambda call:False,console_ready=True)
        self.assertIn('console.enable',events)
        self.assertIn('title.console.poll',events)
        self.assertEqual(events.count('console.worker.close'),1)
        self.assertNotIn('title.tick.True',events)
        self.assertNotIn('gameplay.enable.0',events)
        self.assertNotIn('poll',events)

    def test_title_only_prepares_without_gameplay_callbacks_or_console(self):
        events = self.run_host(lambda call: False)
        self.assertIn('session.open', events)
        self.assertIn('prepared', events)
        self.assertNotIn('gameplay.enable.0', events)
        self.assertNotIn('console.enable', events)
        self.assertNotIn('foreground.observe',events)
        self.assertNotIn('load.Legacy', events)
        self.assertNotIn('load.IntrospectionHarness', events)
        self.assertIn('session.close', events)
        self.assertIn('handle.close', events)
        self.assertIn('observer.close', events)
        self.assertNotIn('poll',events)

    def test_explicit_title_ui_ticks_without_generic_mod_poll_or_keys(self):
        events=self.run_host(lambda call:False,title=True)
        self.assertIn('title.tick.True',events)
        self.assertNotIn('poll',events)
        self.assertNotIn('foreground.observe',events)
        self.assertEqual(events.count('console.enable'),1)
        self.assertIn('title.console.poll',events)
        self.assertLess(events.index('console.enable'),events.index('title.tick.True'))

    def test_title_cleanup_precedes_first_world_poll_and_restore(self):
        events=self.run_host(lambda call:call>=3,title=True)
        self.assertIn('title.cleanup',events)
        self.assertLess(events.index('title.cleanup'),events.index('poll'))
        self.assertLess(events.index('title.cleanup'),events.index('gameplay.enable.0'))

    def test_first_restoration_recounts_latest_title_choices(self):
        events=self.run_host(lambda call:call>=3,title=True,staged_count=3)
        self.assertIn('progress.total.3',events)

    def test_title_then_gameplay_restores_only_after_readiness(self):
        events = self.run_host(lambda call: call>=3)
        self.assertIn('admission.inactive', events)
        self.assertEqual(events.count('session.open'), 1)
        self.assertEqual(events.count('prepared'), 1)
        self.assertEqual(events.count('gameplay.enable.0'), 1)
        self.assertLess(events.index('admission.world_ready'), events.index('gameplay.enable.0'))
        self.assertEqual(events.count('console.enable'), 1)

    def test_loading_between_steps_inhibits_second_enable_but_keeps_polling(self):
        events=self.run_host(lambda call: world_admission.Admission(
            'world_ready' if call<=5 else 'loading','test',('epoch',) if call<=5 else None,
            call<=5),restore_count=2)
        self.assertEqual(events.count('gameplay.enable.0'),1)
        self.assertNotIn('gameplay.enable.1',events)
        self.assertGreater(events.count('poll'),3)
        self.assertIn('ui.False',events)

    def test_combat_preserves_core_ui_without_first_gameplay_activation(self):
        events=self.run_host(lambda call: world_admission.Admission('world_ready','possession_pending',('epoch',),False))
        self.assertNotIn('poll',events)
        self.assertEqual(events.count('enable.SDKManagement'),1)
        self.assertEqual(events.count('console.enable'),1)
        self.assertNotIn('gameplay.enable.0',events)
        self.assertNotIn('foreground.observe',events)
        self.assertNotIn('load.IntrospectionHarness',events)

    def test_observation_uncertainty_uses_none_ui_without_activation(self):
        events=self.run_host(lambda call: world_admission.Admission('observation_pending','read_unavailable'))
        self.assertIn('title.tick.None',events)
        self.assertNotIn('poll',events)
        self.assertNotIn('menu.ready',events)
        self.assertNotIn('gameplay.enable.0',events)
        self.assertEqual(events.count('enable.SDKManagement'),1)

    def test_new_world_after_partial_restore_blocks_remaining_legacy_enable(self):
        events=self.run_host(lambda call: world_admission.Admission('world_ready','test',
            ('first' if call<=5 else 'second',),True),restore_count=2,cleanup_ready=False)
        self.assertEqual(events.count('gameplay.enable.0'),1)
        self.assertNotIn('gameplay.enable.1',events)

    def test_new_epoch_after_complete_restore_starts_fresh_cycle_once(self):
        events=self.run_host(lambda call: world_admission.Admission('world_ready','test',
            ('first' if call<=7 else 'second',),True))
        self.assertEqual(events.count('cycle.begin'),2)
        self.assertEqual(events.count('gameplay.enable.0'),2)
        self.assertEqual(events.count('enable.IntrospectionHarness'),2)
        self.assertEqual(events.count('prepared'),1)

    def test_uncertainty_keeps_current_cycle_and_does_not_restart_restoration(self):
        events=self.run_host(lambda call:world_admission.Admission(
            'observation_pending' if 6<=call<=8 else 'world_ready','test',
            None if 6<=call<=8 else ('epoch',),not 6<=call<=8))
        self.assertEqual(events.count('cycle.begin'),1)
        self.assertEqual(events.count('gameplay.enable.0'),1)

    def test_confirmed_boundary_waits_for_pending_cleanup_then_restarts(self):
        events=self.run_host(lambda call:world_admission.Admission('world_ready','test',
            ('first' if call<=7 else 'second',),True),cleanup_ready=False,release_after=5)
        self.assertEqual(events.count('cycle.begin'),2)
        self.assertEqual(events.count('gameplay.enable.0'),2)
        self.assertGreaterEqual(events.count('poll'),5)

    def test_foreground_new_token_cannot_enable_on_the_mismatch_operation(self):
        def sample(call):return world_admission.Admission('world_ready','test',
            ('first' if call<=4 else 'second',),True)
        events=self.run_host(sample,foreground=lambda call:world_admission.Admission(
            'world_ready','test',('second',) if call>=4 else ('first',),True))
        # First cycle loses its gate before any optional activation. The next
        # matching sampled epoch starts a new cycle; imports/preparation persist.
        self.assertEqual(events.count('cycle.begin'),2)
        self.assertEqual(events.count('gameplay.enable.0'),1)
        self.assertEqual(events.count('prepared'),1)

    def test_failed_title_ack_still_closes_readers_and_command_endpoint(self):
        events=[]
        with self.assertRaisesRegex(RuntimeError,'title native attachment acknowledgement unknown'):
            self.run_host(lambda call:False,title=True,commands=True,
                close_failure='title',recorded_events=events)
        for event in ('title.close','monitor.close','observer.close','server.close','session.close','lock.close','handle.close'):
            self.assertIn(event,events)
        self.assertLess(events.index('title.close'),events.index('monitor.close'))

    def test_failed_monitor_cleanup_still_closes_foreground_reader_and_endpoint(self):
        events=[]
        with self.assertRaisesRegex(RuntimeError,'monitor cleanup failed'):
            self.run_host(lambda call:False,commands=True,close_failure='monitor',recorded_events=events)
        self.assertIn('observer.close',events);self.assertIn('server.close',events)
        self.assertIn('handle.close',events)


if __name__ == '__main__': unittest.main()
