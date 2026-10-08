"""Incremental original-core live test: roots/search/schema and bounded mod lifecycle."""
import json
from pathlib import Path

from expedition33.introspection import Harness
from expedition33.mods import ModLoader


def main():
    root = Path(__file__).resolve().parents[1]
    with Harness() as harness:
        status = harness.request({'op': 'status'})
        roots = harness.request({'op': 'roots'})
        search = harness.request({'op': 'search', 'class': 'PlayerController', 'limit': 32})
        assert roots['PlayerController'] and search['objects']
        assert any(row in roots['PlayerController'] for row in search['objects'])
        controller = roots['PlayerController'][0]
        schema = harness.request({'op': 'schema', 'class': controller['class'], 'limit': 20})
        assert len(schema['properties']) == 20 and len(schema['functions']) == 20
        assert 'PlayerController' in schema['parents'] and 'Actor' in schema['parents']
        assert any(fn['parameters'] for fn in schema['functions'])
        struct = next(prop['Struct']['path'] for prop in schema['properties']
                      if prop.get('Struct', {}).get('name') == 'Rotator')
        struct_schema = harness.request({'op': 'schema', 'struct': struct})
        assert {p['name'] for p in struct_schema['properties']} == {'Pitch', 'Yaw', 'Roll'}
        assert all(p['type'] == 'DoubleProperty' for p in struct_schema['properties'])
    with ModLoader(root / 'mods') as loader:
        for _ in range(2):
            loader.load('IntrospectionHarness')
            loader.enable('IntrospectionHarness', console=True, console_key='F10')
            loader.poll('IntrospectionHarness')
            loader.disable('IntrospectionHarness')
            loader.unload('IntrospectionHarness')
            assert not loader.status()
    result = {'status': status, 'roots': roots, 'search': search,
              'schema': schema, 'struct_schema': struct_schema,
              'mod_attach_unload_cycles': 2,
              'native_ui_command_entry_tested': False}
    (root / 'evidence/introspection-original-core-live.json').write_text(
        json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
