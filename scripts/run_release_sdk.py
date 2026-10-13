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
        from expedition33.release_startup import gameplay_ready
        deadline = time.monotonic() + 600
        logging.info('Waiting for loaded exploration gameplay before restoring saved mods: pid=%s', args.game_pid)
        while True:
            if kernel.WaitForSingleObject(handle, 0) != 258:
                return
            try:
                if gameplay_ready(args.game_pid):
                    break
                # A valid title/menu state is not an error. Keep waiting while
                # this process lives; only sustained read failures time out.
                deadline = time.monotonic() + 600
                time.sleep(1)
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
            transport = original_transport(_executable=ROOT / 'build/research-probe-picto-v4/research_probe.exe')
            required = ('original_game_action_protocol', 'blueprint_trace_protocol', 'picto_edit_protocol', 'picto_progression_protocol', 'picto_class_load_protocol', 'picto_cost_protocol')
            if any(getattr(transport, name, 0) != 1 for name in required):
                transport.close()
                raise RuntimeError('Combined release runtime is missing capabilities')
            return transport
        sdk.SessionTransport = release_transport
        settings = SettingsStore(ROOT / 'settings/management.json')
        with sdk.Session(multiple_pause_entries=True) as session, ModLoader(mod_root, settings=settings, session=session, poll_diagnostics=args.poll_diagnostics) as loader:
            from expedition33.lease_policy import configure
            configure(session, hard_limit=1024, owner_quota=256, cleanup_reserve=64)
            session.console.enable()
            # Only core/default UI mods start automatically on a fresh install.
            # Explicit saved false always wins for optional mods.
            for name in ('SDKManagement', 'IntrospectionHarness'):
                if name != 'SDKManagement' and name not in loader.discover():
                    continue
                selection = loader.registry.load(name)
                view = next(v for v in loader.registry.views() if v['folder'] == name)
                if view['protected'] or settings.get(view['id']).get('enabled') is not False:
                    loader.registry.set_enabled(selection, True)
            for mod_id, failure in loader.registry.restore_enabled().items():
                logging.error('Saved enable failed for %s: %s', mod_id, failure)
            server = None
            if args.commands:
                from expedition33.controller_commands import CommandServer, Command
                server = CommandServer({'mods.status': Command('inspect', loader.registry.views), 'sdk.shutdown': Command('lifecycle', loader.request_stop)}, capabilities={'inspect', 'lifecycle'})
                server.write_connection(ROOT / 'settings/controller')
            try:
                logging.info('SDK ready: pid=%s, mods=%s', session.pid, len(loader.discover()))
                while not loader.stop_requested and kernel.WaitForSingleObject(handle, 0) == 258:
                    if server:
                        server.poll()
                    loader.poll()
                    time.sleep(.005)
                if loader.stop_requested:
                    time.sleep(.3)  # Let the requesting client receive acknowledgement.
            finally:
                if server:
                    server.close()
    finally:
        lock.close()
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
