"""Read-only candidate proof for array element identities and harness schemas."""
import argparse
import json
from pathlib import Path
import subprocess
from unittest.mock import patch

from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33.introspection import Harness

ROOT = Path(__file__).resolve().parents[1]


def verify():
    catalog = capture()
    targets = [catalog.by_index[catalog.find_class(name).index]
               for name in ('InputSettings', 'GameInstance')]
    descriptions = describe(catalog, targets)
    expectations = {'ConsoleKeys': ('inner_struct', 'Key'),
                    'ActionMappings': ('inner_struct', 'InputActionKeyMapping'),
                    'AxisMappings': ('inner_struct', 'InputAxisKeyMapping'),
                    'LocalPlayers': ('inner_property_class', 'LocalPlayer')}
    result = {}
    for descriptor in descriptions.values():
        for row in descriptor.properties:
            if row['name'] not in expectations:
                continue
            prefix, expected = expectations[row['name']]
            reference = catalog.by_index[row[prefix + '_index']]
            assert reference.name == expected
            assert reference.serial == row[prefix + '_serial']
            result[row['name']] = dict(row, referenced_path=catalog.path_name(reference))
    assert set(result) == set(expectations)
    with Harness() as harness:
        schemas = [harness.request({'op': 'schema', 'class': name, 'limit': 100})
                   for name in ('InputSettings', 'GameInstance')]
    seen = set()
    for schema in schemas:
        for row in schema['properties']:
            if row['name'] not in expectations:
                continue
            prefix, _ = expectations[row['name']]
            attr = 'Struct' if prefix == 'inner_struct' else 'PropertyClass'
            assert row['Inner'][attr]['$object'] == result[row['name']]['referenced_path']
            assert row['Inner']['element_size'] == result[row['name']]['inner_element_size']
            seen.add(row['name'])
    assert seen == set(expectations)
    return {'pid': catalog.pid, 'properties': result, 'schemas': schemas,
            'functions_invoked': False, 'controller_replaced': False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'evidence/inner-schema-live.json')
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
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'pid': result['pid'], 'verified': list(result['properties']),
                      'output': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
