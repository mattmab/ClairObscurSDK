"""Inspect or explicitly restore an interrupted install with controllers stopped."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from expedition33.mod_install import inspect_transaction, recover_transaction


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inspect', 'restore'))
    parser.add_argument('mod_root', type=Path)
    parser.add_argument('transaction_id')
    parser.add_argument('--expected-journal-sha256')
    args = parser.parse_args(argv)
    try:
        if args.operation == 'inspect':
            result = inspect_transaction(args.mod_root, args.transaction_id)
        else:
            if not args.expected_journal_sha256:
                raise ValueError('restore requires --expected-journal-sha256 from a fresh inspection')
            result = recover_transaction(args.mod_root, args.transaction_id,
                                         expected_journal_sha256=args.expected_journal_sha256)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as error:
        print(json.dumps({'error': type(error).__name__ + ': ' + str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
