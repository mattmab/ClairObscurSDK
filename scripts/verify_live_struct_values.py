"""Bounded reflected struct observations through the candidate reader; no writes."""
import argparse
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from expedition33.catalog import capture
from expedition33.values import read_values, StoredStruct, StoredArray
from expedition33.introspection import Harness

ROOT = Path(__file__).resolve().parents[1]


def verify():
    catalog = capture()
    specimens = {'Default__InputSettings': ('ConsoleKeys', 'ActionMappings', 'AxisMappings'),
                 'Default__SceneComponent': ('RelativeLocation', 'RelativeRotation', 'RelativeScale3D')}
    results = []
    copied_arrays = {}
    with Harness() as harness:
        for name, members in specimens.items():
            matches = [obj for obj in catalog.objects if obj.name == name]
            assert len(matches) == 1, name
            obj = matches[0]
            values = read_values(catalog, obj)
            for member in members:
                key = next(key for key in values.types if key[1] == member)
                assert key not in values.errors, (member, values.errors.get(key))
                value = values.values[key]
                assert isinstance(value, (StoredStruct, StoredArray)), member
                if member == 'ConsoleKeys':
                    assert value.items and all(isinstance(item, StoredStruct) for item in value)
                    assert all(item.type_object.name == 'Key' and type(item.fields['KeyName']) is str for item in value)
                elif member in ('ActionMappings', 'AxisMappings'):
                    assert value.items and all(isinstance(item, StoredStruct) for item in value)
                    assert all(isinstance(item.fields['Key'], StoredStruct) and
                               type(item.fields['Key'].fields['KeyName']) is str for item in value)
                    assert len(value.items) == min(len(value), 64)
                elif member == 'RelativeScale3D':
                    assert value.fields == {'X':1.0, 'Y':1.0, 'Z':1.0}, value
                elif member == 'RelativeLocation':
                    assert value.fields == {'X':0.0, 'Y':0.0, 'Z':0.0}, value
                if isinstance(value, StoredArray):
                    copied_arrays[member] = {'length':len(value), 'copied':len(value.items)}
            target = {'$object': catalog.path_name(obj), 'class': catalog.path_name(catalog.by_index[obj.class_index])}
            request = {'op':'inspect', 'target':target, 'members':list(members), 'depth':4}
            observed = harness.request(request)
            assert all('$error' not in observed['values'][member] for member in members)
            if name == 'Default__InputSettings':
                for member in members:
                    source = next(value for key, value in values.values.items() if key[1] == member)
                    rendered = observed['values'][member]
                    assert rendered['length'] == len(source) and rendered['truncated'] == (len(source) > 64)
                    first = rendered['items'][0]['fields']
                    expected_key = source.items[0].fields['KeyName'] if member == 'ConsoleKeys' else source.items[0].fields['Key'].fields['KeyName']
                    actual_key = first['KeyName'] if member == 'ConsoleKeys' else first['Key']['fields']['KeyName']
                    assert actual_key == expected_key
            before = harness.request(dict(request, op='snapshot', name='struct-before'))
            after = harness.request(dict(request, op='snapshot', name='struct-after'))
            assert before['values'] == after['values']
            assert harness.request({'op':'diff','before':'struct-before','after':'struct-after'}) == {}
            results.append(observed)
    return {'pid':catalog.pid, 'results':results, 'copied_arrays':copied_arrays,
            'native_state_owned':False, 'controller_replaced':False}


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
    with patch('expedition33.subprocess.run', side_effect=launch): result = verify()
    result['reader'] = str(candidate)
    (ROOT / 'evidence/struct-values-live.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'pid':result['pid'], 'targets':[row['target'] for row in result['results']],
                      'evidence':'evidence/struct-values-live.json'}, indent=2))


if __name__ == '__main__': main()
