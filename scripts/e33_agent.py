"""Port of Mattmab's BL4 named-action CLI (MIT, src/expedition33/introspection/LICENSE).

Uses the original local JSON protocol through e33_introspect.py. BL4 game-specific
aliases and core reload are not supported by the Expedition 33 backend.
"""
import argparse
import json
from pathlib import Path
import runpy

_client = runpy.run_path(str(Path(__file__).with_name('e33_introspect.py')))
send = _client['send']
DEFAULT_DATA = _client['DEFAULT_DATA']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-mutation', action='store_true')
    parser.add_argument('--data', type=Path, default=DEFAULT_DATA)
    parser.add_argument('--timeout', type=float, default=15.)
    sub = parser.add_subparsers(dest='op', required=True)
    sub.add_parser('status', help='Read bridge capabilities, registered actions and last diagnostics')
    sub.add_parser('mods', help='List loaded mods and their enabled state')
    action = sub.add_parser('action', help='Call one registered named action')
    action.add_argument('name')
    action.add_argument('--args', default='{}', help='JSON object of named arguments')
    for verb in ('enable', 'disable'):
        lifecycle = sub.add_parser(verb, help=f'{verb.title()} an already-loaded mod')
        lifecycle.add_argument('mod', help='Loader folder name from mods')
    for verb in ('reload', 'reload-changed'):
        lifecycle = sub.add_parser(verb, help='Reload captured local Python; staged archives excluded')
        lifecycle.add_argument('mod', help='Already-loaded non-core mod folder')
        lifecycle.add_argument('--expected-sha256', required=True, help='SHA256 of installed mod.py bytes')
        lifecycle.add_argument('--expected-package-sha256', help='Required when package-local Python helpers exist or were removed')
    logs = sub.add_parser('logs', help='Read a bounded SDK log tail')
    staged = sub.add_parser('install-staged', help='Install fixed staging/<mod>.zip; retain backup and journal')
    staged.add_argument('mod')
    staged.add_argument('--expected-sha256', required=True, help='SHA256 of the complete staged archive')
    logs.add_argument('--contains', default='')
    logs.add_argument('--limit', type=int, default=30)
    args = parser.parse_args(argv)
    try:
        if args.op == 'status':
            request = {'op': 'dev_status'}
        elif args.op == 'mods':
            request = {'op': 'mod_list'}
        elif args.op == 'action':
            values = json.loads(args.args)
            if type(values) is not dict:
                raise ValueError('--args must be a JSON object')
            request = {'op': 'action', 'name': args.name, 'args': values}
        elif args.op in ('enable', 'disable'):
            request = {'op': 'mod_' + args.op, 'mod': args.mod}
        elif args.op in ('reload', 'reload-changed', 'install-staged'):
            if len(args.expected_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.expected_sha256):
                raise ValueError('--expected-sha256 must be 64 lowercase hex characters')
            request = {'op': {'reload':'mod_reload', 'reload-changed':'reload_changed_mod',
                              'install-staged':'mod_install_staged'}[args.op],
                       'mod': args.mod, 'expected_sha256': args.expected_sha256}
            if getattr(args, 'expected_package_sha256', None) is not None:
                if len(args.expected_package_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.expected_package_sha256):
                    raise ValueError('--expected-package-sha256 must be 64 lowercase hex characters')
                request['expected_package_sha256'] = args.expected_package_sha256
        else:
            request = {'op': 'logs', 'contains': args.contains, 'limit': args.limit}
        request['allow_mutation'] = args.allow_mutation
        # One send only. A claimed timed-out mutation has an unknown outcome.
        result = send(request, args.data, args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result.get('ok') is True and result.get('result', {}).get('success') is True else 1
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
