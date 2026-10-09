"""Isolated development-bundle launcher; standard-library dependencies only."""
import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[1]
if sys.version_info[:3] != (3, 13, 15):
    raise SystemExit(f'CPython 3.13.15 is required; got {sys.version.split()[0]}')
if ROOT.drive.upper() != 'D:':
    raise SystemExit('Extract this development bundle under D:\\HobbyDevelopment')
if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
    raise SystemExit('Use launch.cmd (isolated interpreter, no site startup or bytecode writes)')
manifest = ROOT / 'MANIFEST.json'
if manifest.exists():
    for relative, expected in json.loads(manifest.read_text(encoding='utf-8'))['files'].items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():
            raise SystemExit(f'Bundle file missing or outside root: {relative}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit(f'Bundle checksum mismatch: {relative}')
sys.path.insert(0, str(ROOT / 'src'))
import expedition33
from expedition33.mods import ModLoader
from expedition33.settings import SettingsStore
from expedition33.sdk import Session

if not Path(expedition33.__file__).resolve().is_relative_to(ROOT):
    raise SystemExit('SDK import resolved outside this bundle')

def main():
    parser = argparse.ArgumentParser(description='Expedition 33 development SDK')
    parser.add_argument('command', choices=['objects', 'example', 'smoke', 'console', 'introspection', 'management'])
    parser.add_argument('--seconds', type=float, default=0, help='Console duration; 0 runs until Ctrl+C')
    parser.add_argument('--console-key', choices=[f'F{i}' for i in range(1, 13)], help='Optional additional console toggle')
    parser.add_argument('--reflected', action='store_true', help='Use experimental v6 reflected invocation backend')
    parser.add_argument('--leases', action='store_true', help='Use experimental v7 object leases and reflected invocation')
    parser.add_argument('--retained', action='store_true', help='Use experimental v8 retained invocation and Harness values')
    parser.add_argument('--stable-returns', action='store_true', help='Use experimental v9 stable retained object returns')
    parser.add_argument('--object-assignment', action='store_true', help='Use experimental v10 owned ObjectProperty assignment')
    parser.add_argument('--pod-values', action='store_true', help='Use experimental v11 verified numeric struct invocation')
    parser.add_argument('--text-values', action='store_true', help='Use experimental v12 owned text invocation and v11 capabilities')
    args = parser.parse_args()
    if (args.reflected or args.leases or args.retained or args.stable_returns or args.object_assignment or args.pod_values or args.text_values) and args.command not in ('console', 'introspection', 'management'):
        parser.error('Experimental session flags require console, introspection or management')
    log_dir = ROOT / 'logs'
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[logging.StreamHandler(), RotatingFileHandler(log_dir / 'sdk.log', maxBytes=2_000_000, backupCount=3, encoding='utf-8')])
    log = logging.getLogger('expedition33.launcher')
    try:
        if args.command in ('console', 'introspection', 'management'):
            mod_name = 'IntrospectionHarness' if args.command in ('introspection', 'management') else 'ConsoleExample'
            store = SettingsStore(ROOT / 'settings/management.json') if args.command == 'management' else None
            if store is not None and store.recovery:
                log.warning('Management settings recovery: %s', store.recovery)
            with (Session(reflected=args.reflected, leases=args.leases, retained=args.retained, stable_returns=args.stable_returns, object_assignment=args.object_assignment, pod_values=args.pod_values, text_values=args.text_values)
                  if args.reflected or args.leases or args.retained or args.stable_returns or args.object_assignment or args.pod_values or args.text_values else nullcontext(None)) as runtime, \
                    ModLoader(ROOT / 'mods', settings=store, session=runtime) as loader:
                if args.command == 'management':
                    loader.load('SDKManagement')
                    loader.enable('SDKManagement', console=True, console_key=args.console_key)
                    log.info('Console management ready: mods. Native UMG and general key dispatch remain pending.')
                loader.load(mod_name)
                loader.enable(mod_name, console=True, console_key=args.console_key)
                if args.command in ('introspection', 'management'):
                    log.info('Introspection stage 1 ready: e33i.status, e33i.roots, e33i.request JSON, or py introspection.request(...). Ctrl+C stops the controller.')
                else:
                    log.info('Native console ready. Press Tilde; use py help(), py my_mod.some_function(), or sdk.hello. Ctrl+C stops the controller.')
                deadline = time.monotonic() + args.seconds if args.seconds > 0 else float('inf')
                try:
                    while not loader.stop_requested and time.monotonic() < deadline:
                        loader.poll()
                        time.sleep(.05)
                except KeyboardInterrupt:
                    log.info('Closing console session')
                except expedition33.TargetExitedError as error:
                    if error.exit_code != 0:
                        raise
                    log.info('Game exited normally; revoking Python resources and ending this controller')
            log.info('%s unloaded; SDK controller closed', mod_name)
        if args.command in ('objects', 'smoke'):
            observed = expedition33.objects()
            if not observed:
                raise RuntimeError('Live enumeration returned no objects')
            log.info('Enumerated %d live objects in PID %d using %s', len(observed), observed[0].pid, expedition33.__file__)
            for obj in observed[:20]:
                print(f'{obj.name}  {obj.class_name}')
        if args.command == 'smoke':
            metadata = expedition33.reflect_class('Actor')
            values = expedition33.stored_bools('Default__Actor')
            log.info('Actor hierarchy=%s; %d reflected fields; %d stored bool observations',
                     metadata.hierarchy, len(metadata.properties), len(values.values))
        if args.command in ('example', 'smoke'):
            with ModLoader(ROOT / 'mods') as loader:
                loader.load('ExampleMod')
                loader.enable('ExampleMod')
                loader.disable('ExampleMod')
                loader.unload('ExampleMod')
            log.info('ExampleMod completed and unloaded')
        return 0
    except Exception:
        log.exception('SDK operation failed; native diagnostics are included below')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
