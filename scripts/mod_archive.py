"""Build or inspect a mod candidate; never installs or executes mod source."""
import argparse
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
api = runpy.run_path(str(ROOT / 'src/expedition33/mod_archive.py'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    build = sub.add_parser('build')
    build.add_argument('source', type=Path)
    build.add_argument('output', type=Path, help='New archive path; existing files are never overwritten')
    inspect = sub.add_parser('inspect')
    inspect.add_argument('archive', type=Path)
    inspect.add_argument('--expected-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'build':
            data, candidate = api['build_bytes'](args.source)
            if args.output.resolve().is_relative_to(args.source.resolve()):
                raise ValueError('Archive output must be outside the source folder')
            with args.output.open('xb') as stream:
                stream.write(data)
        else:
            candidate = api['read_candidate'](args.archive, args.expected_sha256)
        print(json.dumps(candidate.summary(), indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
