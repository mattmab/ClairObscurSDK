"""Portable installed SDK controller. Bootstrap and manual launcher share this host."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import logging
import os
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src')]


def verify_install(*, check_mods=False):
    document = json.loads((ROOT / 'release-manifest.json').read_text(encoding='utf8'))
    for name, expected in document['sdk_files'].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT) or path.is_symlink() or path.is_junction():
            raise RuntimeError('Redirected release file: ' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError('Release file missing or modified: ' + name)
    from expedition33.mod_archive import read_candidate
    if check_mods:
        for row in document['mods']:
            read_candidate(ROOT.parent / 'SDK_Mods' / row['archive'], row['sha256'])
    return document


def game_handle(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    handle = kernel.OpenProcess(0x100000 | 0x1000, False, pid)
    if not handle:
        raise RuntimeError('Expected game process is not running')
    name = ctypes.create_unicode_buffer(32768)
    size = ctypes.c_ulong(len(name))
    expected = ROOT.parent / 'Sandfall/Binaries/Win64/SandFall-Win64-Shipping.exe'
    if not kernel.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)) or Path(name.value).resolve() != expected.resolve():
        kernel.CloseHandle(handle)
        raise RuntimeError('Bootstrap process does not belong to this installation')
    return kernel, handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify package without attaching')
    parser.add_argument('--game-pid', type=int)
    parser.add_argument('--commands', action='store_true', help='Enable authenticated structured local commands')
    parser.add_argument('--poll-diagnostics', action='store_true', help='Log bounded shared poll latency measurements')
    parser.add_argument('--early-init', action=argparse.BooleanOptionalAction, default=True, help='Prepare compatible mods and process UI before a save; defer gameplay activation')
    parser.add_argument('--combat-model-test', action='store_true', help='Allow diagnostic startup with a verified active combat party target')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError('Use the bundled Python 3.13 runtime')
    document = verify_install(check_mods=args.check)
    if args.check:
        print(json.dumps(dict(release=document['version'], mods=len(document['mods']), verified=True)))
        return
    if args.game_pid is None:
        import subprocess
        probe = ROOT / 'build/research-probe/research_probe.exe'
        result = subprocess.run([str(probe), '--limit', '1'], capture_output=True, text=True, timeout=120, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        args.game_pid = next(json.loads(line)['pid'] for line in result.stdout.splitlines() if json.loads(line).get('event') == 'snapshot_start')
    kernel, handle = game_handle(args.game_pid)
    from expedition33.mod_lock import ModRootLock
    lock = ModRootLock(ROOT)
    try:
        (ROOT / 'logs').mkdir(exist_ok=True)
        (ROOT / 'settings').mkdir(exist_ok=True)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s', handlers=[logging.FileHandler(ROOT / 'logs/controller.log', encoding='utf8')])
        from expedition33.release_mods import materialize
        mod_root = materialize(ROOT.parent / 'SDK_Mods', ROOT)
        from expedition33.release_startup import gameplay_ready, attachment_ready, menu_availability
        from expedition33.core_startup import core_bootstrap_ready
        deadline = time.monotonic() + 600
        logging.info('Waiting for %s before attaching core SDK: pid=%s',
                     'engine bootstrap' if args.early_init else 'gameplay and native pause UI', args.game_pid)
        while True:
            if kernel.WaitForSingleObject(handle, 0) != 258:
                return
            try:
                ready=(core_bootstrap_ready(args.game_pid) if args.early_init else attachment_ready(args.game_pid))
                if not ready and args.combat_model_test:
                    from expedition33.procedural_mesh import combat_target
                    combat_target(args.game_pid)
                    ready=True
                if ready:
                    logging.info('Bootstrap prerequisites ready; attaching core SDK: pid=%s', args.game_pid)
                    break
                # A valid title/menu state is not an error. Keep waiting while
                # this process lives; only sustained read failures time out.
                deadline = time.monotonic() + 600
                time.sleep(.25)
            except Exception as error:
                if time.monotonic() >= deadline:
                    raise RuntimeError('Game was not ready within ten minutes') from error
                time.sleep(1)
        # The native controller checks this before it installs any hook.
        os.environ['E33_EXPECTED_GAME_PID'] = str(args.game_pid)
        import expedition33.sdk as sdk
        from expedition33.mods import ModLoader
        from expedition33.settings import SettingsStore
        original_transport = sdk.SessionTransport
        def release_transport(*, _executable=None):
            transport = original_transport(_executable=ROOT / 'build/research-probe-cinematic-v210-lease-batch/research_probe.exe')
            required = ('retired_world_cleanup_protocol', 'menu_open_focus_protocol', 'metadata_stabilization_protocol', 'stable_lease_protocol', 'console_color_status_protocol', 'lease_release_batch_protocol', 'original_game_action_protocol', 'blueprint_trace_protocol', 'picto_edit_protocol', 'picto_progression_protocol', 'picto_class_load_protocol', 'picto_cost_protocol')
            required = (*required,'builder_world_retirement_protocol')
            if transport.zone_travel_protocol != 2 or any(getattr(transport, name, 0) != 1 for name in required) or transport.mesh_protocol != 3:
                transport.close()
                raise RuntimeError('Combined release runtime is missing capabilities')
            return transport
        sdk.SessionTransport = release_transport
        settings = SettingsStore(ROOT / 'settings/management.json')
        with sdk.Session(multiple_pause_entries=True) as session, ModLoader(mod_root, settings=settings, session=session, poll_diagnostics=args.poll_diagnostics) as loader:
            from expedition33.lease_policy import configure
            configure(session, hard_limit=8192, owner_quota=7000, cleanup_reserve=512)
            world_lifecycle = loader.install_world_lifecycle() if args.early_init else None
            ui_ready = not args.early_init
            runtime_polling_started = not args.early_init
            process_ui = None
            if args.early_init:
                from expedition33.process_ui import ProcessUI
                process_ui = ProcessUI(session,loader.registry)
                session._process_ui = process_ui
                from expedition33.loading_preparation import LoadingPreparation
                loading_preparation=LoadingPreparation(session,loader)
            if args.early_init:
                # Core services register Python callbacks immediately. Neither
                # console attachment nor native widgets are needed for readiness.
                session._menu_readiness = lambda: ui_ready
                session._poll_readiness = lambda: runtime_polling_started
            else:
                session.console.enable()
            loader.registry._startup_progress = dict(completed=0,
                total=sum(settings.get(key).get('enabled') is True for key in loader.registry.startup_order()),
                failed=0, finished=False, phase='widgets')
            # Only core/default UI mods start automatically on a fresh install.
            # Explicit saved false always wins for optional mods.
            for name in (('SDKManagement',) if args.early_init else ('SDKManagement', 'IntrospectionHarness')):
                if name != 'SDKManagement' and name not in loader.discover():
                    continue
                if args.early_init and not loader.prepare_startup(name, sdk_version=document['version']):
                    raise RuntimeError('Core management requires explicit early-preparation compatibility')
                selection = loader.registry.load(name)
                view = next(v for v in loader.registry.views() if v['folder'] == name)
                if view['protected'] or settings.get(view['id']).get('enabled') is not False:
                    loader.registry.set_enabled(selection, True)
                if name == 'SDKManagement':
                    # Prepare the usable menu before optional gameplay work.
                    loader._loaded[name][1].prepare()
            if args.early_init:
                from expedition33.process_console import ProcessConsole, StartupConsoleInfo
                process_console = ProcessConsole(session,loader._loaded['SDKManagement'][1].menu)
                console_info = StartupConsoleInfo(session.console,loader,document['version'])
                session.console.register('startuptiming',console_info.command,owner=console_info)
                for name in loader.discover():
                    if name == 'SDKManagement':
                        continue
                    try:
                        prepared = loader.prepare_startup(name, sdk_version=document['version'])
                        if prepared:
                            logging.info('Mod prepared before world activation: %s', name)
                    except Exception:
                        # A failed optional preparation never replays its code
                        # or aborts unrelated core services.
                        logging.exception('Startup preparation failed for %s', name)
            from expedition33.startup_order import StartupGate
            startup_gate = StartupGate()
            loader.registry._startup_progress['phase'] = 'mods'
            startup_pending_result = None
            restoration = loader.registry.restore_enabled_steps()
            next_restore = time.monotonic() + .005
            gameplay_confirmed = False
            activation_candidate = False
            startup_counts_refreshed = not args.early_init
            late_core_pending = args.early_init
            restored_world_token = None
            startup_world_token = None
            last_lifecycle_sequence = None
            admission_observer = None
            admission_monitor = None
            console_readiness = None
            title_ui = None
            last_observation_sequence = None
            restoration_waiting_context = False
            last_admission_signature = None
            server = None
            if args.commands:
                from expedition33.controller_commands import CommandServer, Command
                def catalog_model():
                    loaded=loader._loaded.get('CatalogModels')
                    if not loaded or loaded[1].session is None:
                        raise RuntimeError('Enable Catalog Models first')
                    return loaded[1]
                def ui_status():
                    management = loader._loaded['SDKManagement'][1]
                    status = management.native.status()
                    if title_ui is not None and title_ui.service is not None:
                        status=title_ui.service.status()
                    return dict(state=status['state'], latency=status.get('latency'),
                        menu_latency=status.get('menu_latency'), widget_latency=status.get('widget_latency'),
                        readiness_sampling=admission_monitor.diagnostics() if admission_monitor is not None else None,
                        world_lifecycle=world_lifecycle.status() if world_lifecycle is not None else None,
                        console_enabled=bool(session.console._enabled),
                        console_colors=getattr(session.console,'native_color_status',None),
                        metadata_leases=len(getattr(getattr(session,'_metadata_preparation',None),'_journal',())),
                        pause_state=management.pause.state if management.pause is not None else None,
                        pause_timings=dict(management.pause.timings) if management.pause is not None else {},
                        title=title_ui.status() if title_ui is not None else None)
                def title_open():
                    if title_ui is None:
                        raise RuntimeError('Title frontend is unavailable')
                    return title_ui.open()
                def title_test_keys(offset=0):
                    if type(offset) not in (int,float) or not 0 <= offset <= 50000:
                        raise ValueError('Expected bounded scroll offset')
                    if title_ui is None or title_ui.service is None:
                        raise RuntimeError('Title frontend is unavailable')
                    menu=title_ui.service.menu
                    if menu is None or menu.panel.state!='open':
                        raise RuntimeError('Open the title menu first')
                    if menu.view.screen!='all_keys':
                        menu.view.screen='all_keys'
                        menu.view.reset_scroll()
                        menu.refresh()
                    menu.panel.direct(menu.panel.scroll,'ScrollBox','SetScrollOffset',NewScrollOffset=float(offset))
                    menu._scroll_poll=0
                    menu.poll_scroll()
                    return dict(screen=menu.view.screen,rows=menu.view.total_rows)
                server = CommandServer({'mods.status': Command('inspect', loader.registry.views), 'sdk.ui_status': Command('inspect', ui_status), 'sdk.title_open': Command('ui', title_open), 'sdk.title_test_keys': Command('ui', title_test_keys), 'sdk.shutdown': Command('lifecycle', loader.request_stop),
                    'catalog.replacement_preview':Command('models',lambda:catalog_model().replacement_preview()),
                    'catalog.replacement_material':Command('models',lambda profile:catalog_model().replacement_material(profile)),
                    'catalog.replacement_enable':Command('models',lambda:catalog_model().replacement_enable()),
                    'catalog.replacement_select':Command('models',lambda model:catalog_model().select_replacement(model)),
                    'catalog.bones':Command('inspect',lambda component_index,page=0:__import__('expedition33.procedural_mesh',fromlist=['capture_bones']).capture_bones(catalog_model().session,component_index,page)),
                    'catalog.list':Command('inspect',lambda:catalog_model().entries),
                    'catalog.status':Command('inspect',lambda:catalog_model().status()),
                    'catalog.render_probe':Command('models',lambda freeze=None:catalog_model().model.render_probe(freeze)),
                    'catalog.shaders':Command('models',lambda batch=1:catalog_model().shader_samples(batch)),
                      'catalog.shader_nearest':Command('inspect',lambda:catalog_model().shader_nearest()),
                    'catalog.open':Command('models',lambda:catalog_model().open()),
                    'catalog.spawn':Command('models',lambda model_id:catalog_model().spawn(model_id)),
                    'catalog.destroy':Command('models',lambda:catalog_model().destroy())}, capabilities={'inspect', 'lifecycle','models','ui'})
                server.write_connection(ROOT / 'settings/controller')
            if args.early_init:
                from expedition33.world_admission import WarmAdmissionObserver
                from expedition33.admission_monitor import ReadOnlyAdmissionMonitor
                from expedition33.ui_admission import UiAdmissionObserver
                from expedition33.console_startup import ConsoleReadiness
                admission_observer = WarmAdmissionObserver(session.pid)
                admission_monitor = ReadOnlyAdmissionMonitor(lambda pid=session.pid:UiAdmissionObserver(pid))
                title_ui = process_ui
                console_readiness = ConsoleReadiness(session.pid)
            def fresh_world_admission():
                # Read-only gate before EVERY cycle/core/optional enable. A
                # different fresh token schedules retirement but never enables
                # during the same operation that discovered the mismatch.
                expected = world_lifecycle.current_token
                from expedition33 import RuntimeQueryError
                try:
                    current = admission_observer.observe_activation()
                except RuntimeQueryError:
                    world_lifecycle.observe(None)
                    return None
                world_lifecycle.observe(current)
                if (not current.activation_ready or current.token != expected or
                        not world_lifecycle.ready or not world_lifecycle.cleanup_ready):
                    return None
                return current
            try:
                logging.info('SDK ready: pid=%s, mods=%s', session.pid, len(loader.discover()))
                while not loader.stop_requested and kernel.WaitForSingleObject(handle, 0) == 258:
                    if args.early_init:
                        observation = admission_monitor.snapshot()
                        if observation is None:
                            world_lifecycle.observe(None)
                        elif observation.sequence != last_lifecycle_sequence:
                            last_lifecycle_sequence = observation.sequence
                            packet = observation.admission
                            # Confirm a new gameplay token before revoking old
                            # owners. Repeated old mailbox slots cannot overwrite
                            # a newer token already observed at an enable gate.
                            sampled = packet.admission
                            if (sampled.state == 'world_ready' and world_lifecycle.current_token is not None
                                    and sampled.token != world_lifecycle.current_token):
                                fresh_world_admission()
                            else:
                                world_lifecycle.observe(sampled,title=packet.title_ready is True)
                    if server:
                        server.poll()
                    if args.early_init:
                        activation_candidate = (observation is not None and
                            observation.admission.admission.activation_ready and
                            observation.admission.admission.token == world_lifecycle.current_token and
                            world_lifecycle.ready and world_lifecycle.cleanup_ready)
                        title_readiness = (getattr(observation.admission,'title_ready',False)
                            if observation is not None else None)
                        # Viewport-owned console is independent of a loaded save
                        # and becomes usable before optional title UI warmup.
                        if not runtime_polling_started:
                            process_console.enable_for_title(console_readiness.ready() if console_readiness is not None else None)
                            process_console.poll()
                            if session.console._enabled and console_readiness is not None:
                                console_readiness.close()
                                console_readiness = None
                        # A title menu owns a distinct scope. Its acknowledged
                        # detach/release precedes ALL gameplay UI/mod work.
                        if not runtime_polling_started:
                            session.poll() # No generic mod/key polling before first admission.
                        process_ui.observe(observation.admission if observation is not None else None)
                        loading_ui_ready=loading_preparation.observe(observation.admission if observation is not None else None)
                        if not loading_ui_ready:activation_candidate=False
                        if title_readiness is True:
                            process_console.title_active()
                        title_cleanup_ready = process_ui.title_cleanup_ready
                        if not title_cleanup_ready:
                            activation_candidate = False
                        admission = None
                        if observation is None:
                            ui_ready = None
                        elif observation.sequence != last_observation_sequence:
                            last_observation_sequence = observation.sequence
                            admission = observation.admission.admission
                            ui_ready = observation.admission.menu_ready
                        if admission is not None:
                            signature = (admission.state, admission.reason, admission.token)
                            if signature != last_admission_signature:
                                logging.info('World admission: state=%s reason=%s', admission.state, admission.reason)
                                last_admission_signature = signature
                            if admission.activation_ready and title_cleanup_ready:
                                runtime_polling_started = True
                                process_console.world_active()
                        # No passive engine query occurs on this owner loop.
                        # Stale/uncertain status suspends NEW UI work only;
                        # existing input polling needs its separate native gates.
                        # Uncertainty suspends new UI work without claiming the
                        # old world retired. Combat possession is not teardown.
                        if not title_cleanup_ready:
                            ui_ready = False
                        if ui_ready and title_cleanup_ready and not session.console._enabled:
                            session.console.enable()
                        if activation_candidate and title_cleanup_ready and startup_world_token != world_lifecycle.current_token:
                            cycle_admission = fresh_world_admission()
                            if cycle_admission is not None:
                                startup_world_token = cycle_admission.token
                                restored_world_token = None
                                startup_pending_result = None
                                startup_gate = StartupGate()
                                restoration = loader.registry.restore_enabled_steps()
                                late_core_pending = True
                                startup_counts_refreshed = True
                                loader.registry._startup_progress.update(completed=0,failed=0,finished=False,phase='mods',
                                    total=sum(settings.get(key).get('enabled') is True for key in loader.registry.startup_order()))
                                loader.registry._startup_activation_started = {}
                                loader.registry._startup_enable_timings = {}
                                console_info.begin_world_cycle()
                            else:
                                activation_candidate = False
                        if (ui_ready and activation_candidate and late_core_pending and
                                startup_world_token == world_lifecycle.current_token):
                            core_admission = fresh_world_admission()
                            if core_admission is not None and 'IntrospectionHarness' in loader.discover():
                                selection = loader.registry.load('IntrospectionHarness')
                                view = next(v for v in loader.registry.views() if v['folder'] == 'IntrospectionHarness')
                                if view['protected'] or settings.get(view['id']).get('enabled') is not False:
                                    loader.registry.set_enabled(selection, True)
                            if core_admission is not None:
                                late_core_pending = False
                            else:
                                activation_candidate = False
                    if not args.early_init or runtime_polling_started:
                        loader.poll()
                    if restoration is not None and not loader.stop_requested and time.monotonic() >= next_restore and (not args.early_init or activation_candidate) and not startup_gate.pending(time.monotonic()):
                        management = loader._loaded['SDKManagement'][1]
                        # Restore saved mods even while Pause/Mods is open.
                        # Keep polling between enables, but never initialize a
                        # gameplay mod during SDK-owned travel/recovery.
                        busy = management.native.travel_recovery_pending
                        if busy:
                            gameplay_confirmed = False
                        if not busy:
                            if args.early_init:
                                # Revalidate after UI/polling work and before
                                # EVERY optional enable; readiness is not sticky.
                                current_admission = fresh_world_admission()
                                gameplay_confirmed = (current_admission is not None and
                                    current_admission.token == startup_world_token and
                                    current_admission.token == world_lifecycle.current_token)
                                if not gameplay_confirmed:
                                    activation_candidate = False
                                    if not restoration_waiting_context:
                                        logging.warning('Saved mod restoration waits for world admission or cleanup')
                                        restoration_waiting_context = True
                                else:
                                    restoration_waiting_context = False
                            elif not gameplay_confirmed:
                                try:
                                    gameplay_confirmed = gameplay_ready(args.game_pid)
                                    if not gameplay_confirmed and args.combat_model_test:
                                        from expedition33.procedural_mesh import combat_target
                                        combat_target(args.game_pid)
                                        gameplay_confirmed = True
                                except Exception:
                                    gameplay_confirmed = False
                            if gameplay_confirmed:
                                if startup_pending_result is not None:
                                    loader.registry._startup_progress['completed'] += 1
                                    loader.registry._startup_progress['failed'] += bool(startup_pending_result[1])
                                    if args.early_init:
                                        folder=settings.get(startup_pending_result[0]).get('folder')
                                        actual=next((row for row in loader.status() if row.name==folder),None)
                                        view=next((row for row in loader.registry.views() if row['folder']==folder),{})
                                        console_info.activation(view.get('name') or folder or startup_pending_result[0],
                                            not startup_pending_result[1] and actual is not None and actual.enabled,
                                            getattr(loader.registry,'_startup_enable_timings',{}).get(startup_pending_result[0]),
                                            getattr(loader,'_startup_preparation_timings',{}).get(folder))
                                    startup_pending_result = None
                                if not startup_counts_refreshed:
                                    # Title staging may change the desired set
                                    # after the generator was created. Count its
                                    # latest choices only once before first work.
                                    loader.registry._startup_progress.update(completed=0,failed=0,
                                        total=sum(settings.get(key).get('enabled') is True
                                            for key in loader.registry.startup_order()))
                                    startup_counts_refreshed = True
                                result = next(restoration, None)
                                if args.early_init and result is not None and not result[1]:
                                    restored_world_token = current_admission.token
                                startup_pending_result = result
                                if result is None:
                                    loader.registry._startup_progress['finished'] = True
                                    restoration = None
                                    logging.info('Saved mod restoration complete')
                                elif result[1]:
                                    logging.error('Saved enable failed for %s: %s', *result)
                                else:
                                    folder=settings.get(result[0]).get('folder')
                                    loaded=loader._loaded.get(folder)
                                    if loaded:startup_gate.arm(loaded[1],time.monotonic())
                                    logging.info('Saved mod initialized: %s', result[0])
                        # Yield through the owner loop between mods; their
                        # readiness contracts and fresh admission gate the next
                        # enable. An extra fixed 250 ms adds latency per mod.
                        next_restore = time.monotonic() + .005
                    if args.early_init:
                        title_service=getattr(title_ui,'service',None)
                        frontend_failed=bool(getattr(title_ui,'frontend_failed',None) or
                            getattr(title_service,'_failure',None) or
                            getattr(getattr(title_service,'menu',None),'failure',None))
                        console_info.poll(world_active=(runtime_polling_started and world_lifecycle.ready and world_lifecycle.cleanup_ready and title_readiness is not True),title_ready=title_readiness,
                            frontend_failed=frontend_failed)
                    time.sleep(.005)
                if loader.stop_requested:
                    time.sleep(.3)  # Let the requesting client receive acknowledgement.
            finally:
                try:
                    from expedition33.mods import ModDisablePending
                    shutdown_deadline=time.monotonic()+10.
                    while True:
                        # Restore fresh ordinary-disable admission after a
                        # cleanup-only wait. Uncertainty is never retirement.
                        if (args.early_init and world_lifecycle.current_token is not None
                                and world_lifecycle.ever_admitted):
                            fresh_world_admission()
                        try:
                            loader.close()
                            break
                        except ModDisablePending:
                            # False was an explicit read-only barrier, so no
                            # domain disable was dispatched and polling it is safe.
                            if args.early_init:world_lifecycle.observe(None)
                            session.poll()
                            if time.monotonic()>=shutdown_deadline:raise
                            time.sleep(.01)
                    if title_ui is not None:
                        if not title_ui.close():
                            raise RuntimeError('Process UI cleanup pending; retain owner before Session close')
                    if args.early_init:loading_preparation.close()
                finally:
                    try:
                        if admission_monitor is not None:
                            if not admission_monitor.close():
                                logging.info('Read-only readiness worker finishing its bounded request during shutdown')
                    finally:
                        try:
                            if admission_observer is not None:
                                admission_observer.close()
                        finally:
                            try:
                                if console_readiness is not None:
                                    console_readiness.close()
                            finally:
                                if server:
                                    server.close()
    finally:
        try:
            lock.close()
        finally:
            kernel.CloseHandle(handle)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (ROOT / 'logs').mkdir(exist_ok=True)
        import traceback
        with (ROOT / 'logs/startup-error.log').open('a', encoding='utf8') as stream:
            traceback.print_exc(file=stream)
        raise
