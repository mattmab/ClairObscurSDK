"""Read-only live array proof using a separate reader; preserve the user host."""
import argparse
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from expedition33.catalog import capture
from expedition33.values import read_values, StoredArray
from expedition33.introspection import Harness

ROOT = Path(__file__).resolve().parents[1]


def verify():
    catalog = capture()
    results = []
    specimens = []
    for obj in catalog.select('GameInstance'):
        if not obj.name.startswith('Default__'):
            specimens.append((obj, 'LocalPlayers'))
    for name, member in (('Default__Actor', 'Tags'),
                         ('Default__RadialForceComponent', 'ObjectTypesToAffect')):
        matches = [obj for obj in catalog.objects if obj.name == name]
        if len(matches) == 1:
            specimens.append((matches[0], member))
    assert len(specimens) <= 16, 'Unexpected specimen count; inspect before widening'
    with Harness() as harness:
        roots = harness.request({'op': 'roots'})
        for obj, member in specimens:
            stored = read_values(catalog, obj)
            key = next(key for key in stored.types if key[1] == member)
            assert key not in stored.errors, (obj.name, member, stored.errors.get(key))
            value = stored.values[key]
            assert isinstance(value, StoredArray)
            target = {'$object': catalog.path_name(obj), 'class': catalog.path_name(catalog.by_index[obj.class_index])}
            request = {'op': 'inspect', 'target': target, 'members': [member]}
            observed = harness.request(request)['values'][member]
            assert observed['length'] == len(value)
            assert len(observed['items']) == len(value.items)
            assert observed['truncated'] == (len(value) > 64)
            if member == 'LocalPlayers':
                assert value.items, 'Expected actual live local player array'
                assert observed['items'] == roots['LocalPlayer'], (observed, roots['LocalPlayer'])
            elif member == 'ObjectTypesToAffect':
                assert value.items and all(type(item) is int and 0 <= item <= 255 for item in value)
                assert observed['items'] == list(value.items)
            else:
                assert all(type(item) is str for item in value)
            before = harness.request(dict(request, op='snapshot', name='array-before'))
            after = harness.request(dict(request, op='snapshot', name='array-after'))
            diff = harness.request({'op': 'diff', 'before': 'array-before', 'after': 'array-after'})
            assert before['values'] == after['values'] and diff == {}, 'Stable specimen changed; inspect observation'
            results.append({'target': target, 'member': member, 'value': observed})
    assert any(row['member'] == 'LocalPlayers' for row in results)
    assert any(row['member'] == 'ObjectTypesToAffect' for row in results)
    return {'pid': catalog.pid, 'specimens': results, 'persistent_controller_replaced': False,
            'native_allocation_ownership': False, 'large_array_live_tested': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', type=Path, required=True)
    args = parser.parse_args()
    candidate = args.probe.resolve(strict=True)
    default = (ROOT / 'build/research-probe/research_probe.exe').resolve()
    original_run = subprocess.run
    def launch(command, *positional, **kwargs):
        assert Path(command[0]).resolve() == default and '--session' not in command
        return original_run([str(candidate), *command[1:]], *positional, **kwargs)
    with patch('expedition33.subprocess.run', side_effect=launch):
        result = verify()
    result['reader'] = str(candidate)
    (ROOT / 'evidence/introspection-arrays-live.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
