"""Read-only live inspect/snapshot/diff with independent native-API comparisons."""
import json
import argparse
from contextlib import nullcontext
from pathlib import Path
import subprocess
from unittest.mock import patch

import expedition33
from expedition33.catalog import capture
from expedition33.values import read_values
from expedition33.introspection import Harness


def main(output=None):
    catalog = capture()
    actor = next(obj for obj in catalog.objects if obj.name == 'Default__Actor')
    stored = read_values(catalog, actor)
    assert type(stored.values[actor.class_index, 'NetCullDistanceSquared']) is float
    previous = expedition33.stored_bools('Default__Actor')
    for boolean in previous.values:
        owner = catalog.find_class(boolean.owner).index
        assert stored.values[owner, boolean.name] == boolean.value
    with Harness() as harness:
        roots = harness.request({'op': 'roots'})
        target = roots['PlayerController'][0]
        request = {'op': 'inspect', 'target': target, 'members': [
            'Player', 'bShowMouseCursor', 'SmoothTargetViewRotationSpeed', 'NetTag',
            'NetUpdateFrequency', 'RemoteRole', 'NetDriverName', 'LastCompletedSeamlessTravelCount', 'Tags']}
        inspected = harness.request(request)
        values = inspected['values']
        assert values['Player'] == roots['LocalPlayer'][0]
        assert type(values['bShowMouseCursor']) is bool
        assert type(values['NetUpdateFrequency']) is float
        assert type(values['NetTag']) is int
        assert type(values['NetDriverName']) is str
        assert type(values['LastCompletedSeamlessTravelCount']) is int
        assert 0 <= values['LastCompletedSeamlessTravelCount'] <= 65535
        assert set(values['Tags']) == {'items', 'length', 'truncated'}
        assert all(type(tag) is str for tag in values['Tags']['items'])
        before = harness.request(dict(request, op='snapshot', name='before'))
        after = harness.request(dict(request, op='snapshot', name='after'))
        difference = harness.request({'op': 'diff', 'before': 'before', 'after': 'after'})
        expected = {key: {'before': before['values'].get(key), 'after': after['values'].get(key),
            'before_present': key in before['values'], 'after_present': key in after['values']}
            for key in before['values'].keys() | after['values'].keys()
            if before['values'].get(key) != after['values'].get(key)}
        assert difference == expected
        result = {'pid': catalog.pid, 'bool_comparisons': len(previous.values),
                  'inspect': inspected, 'before': before, 'after': after, 'diff': difference,
                  'limitations': 'Stored observations, not getters, owning handles or GC-atomic snapshots'}
    destination = output or Path(__file__).resolve().parents[1] / 'evidence/introspection-values-live.json'
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'Live value inspection passed; {len(previous.values)} existing bool observations agree; references and diff verified.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    default = (Path(__file__).resolve().parents[1] / 'build/research-probe/research_probe.exe').resolve()
    original_run = subprocess.run
    def launch(command, *positional, **kwargs):
        assert Path(command[0]).resolve() == default and '--session' not in command
        return original_run([str(args.probe.resolve(strict=True)), *command[1:]], *positional, **kwargs)
    with patch('expedition33.subprocess.run', side_effect=launch) if args.probe else nullcontext():
        main(args.output)
