"""Port of Mattmab's BL4 named-action CLI (MIT, src/expedition33/introspection/LICENSE).

Uses the original local JSON protocol through e33_introspect.py. Staged reload
and BL4 game-specific aliases are not yet supported by the Expedition 33 backend.
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
    logs = sub.add_parser('logs', help='Read a bounded SDK log tail')
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
