"""Read-only schema reference proof, optionally using a separate candidate reader.

--probe redirects only the reader executable in subprocess.run; all production
catalog/descriptor validation and original-core schema logic remain unchanged.
No synthetic native responses or persistent session operations are used.
"""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from expedition33.introspection import Harness

ROOT = Path(__file__).resolve().parents[1]


def verify():
    results = {}
    expected = {
        'Actor': {'RootComponent': ('PropertyClass', 'SceneComponent'),
                  'ParentComponent': ('PropertyClass', 'ChildActorComponent'),
                  'OnEndPlay': ('SignatureFunction', 'ActorEndPlaySignature__DelegateSignature')},
        'PlayerController': {'OverridePlayerInputClass': ('MetaClass', 'PlayerInput')},
        'InputSettings': {'DefaultInputComponentClass': ('MetaClass', 'InputComponent')},
        'Controller': {'OnPossessedPawnChanged': ('SignatureFunction', 'OnPossessedPawnChanged__DelegateSignature')},
    }
    with Harness() as harness:
        for cls, specimens in expected.items():
            found, pages, offset = {}, [], 0
            while True:
                page = harness.request({'op': 'schema', 'class': cls, 'offset': offset, 'limit': 100})
                pages.append(page)
                found.update({p['name']: p for p in page['properties']})
                if all(name in found for name in specimens):
                    break
                assert page['properties'], f'Missing expected properties on {cls}'
                offset += 100
                assert offset <= 1000, 'Specimens exceed bounded schema scan'
            for name, (attribute, target) in specimens.items():
                reference = found[name][attribute]
                assert reference['name'] == target, (cls, name, reference)
                assert reference['path'].startswith('/Script/'), reference
            results[cls] = {name: found[name] for name in specimens}
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', type=Path)
    args = parser.parse_args()
    original_run = subprocess.run
    default = (ROOT / 'build/research-probe/research_probe.exe').resolve()
    candidate = args.probe.resolve() if args.probe else default
    if not candidate.is_file():
        raise SystemExit(f'Missing reader: {candidate}')

    def launch(command, *positional, **kwargs):
        assert Path(command[0]).resolve() == default, 'Unexpected subprocess in read-only verifier'
        assert '--session' not in command, 'Persistent sessions are excluded'
        return original_run([str(candidate), *command[1:]], *positional, **kwargs)

    with patch('expedition33.subprocess.run', side_effect=launch) if args.probe else nullcontext():
        results = verify()
    output = {'reader': str(candidate), 'schemas': results, 'persistent_controller_replaced': False}
    (ROOT / 'evidence/introspection-reference-schema-live.json').write_text(
        json.dumps(output, indent=2), encoding='utf-8')
    print('Live original-core class and delegate reference schemas passed.')


if __name__ == '__main__':
    main()
