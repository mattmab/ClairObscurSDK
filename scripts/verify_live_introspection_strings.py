"""Live string and DoubleProperty specimens; never modifies game state."""
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33.values import read_values
from expedition33.introspection import Harness


def main():
    with Harness() as harness:
        found = harness.request({'op': 'search', 'class': 'GeneralProjectSettings',
            'query': 'Default__GeneralProjectSettings', 'limit': 2})
        assert len(found['objects']) == 1
        inspected = harness.request({'op': 'inspect', 'target': found['objects'][0],
            'members': ['ProjectName', 'ProjectVersion', 'CompanyName', 'Description']})
        assert inspected['values']['ProjectName'] == 'Expedition 33'
        assert type(inspected['values']['Description']) is str
    catalog = capture()
    defaults = [obj for obj in catalog.objects if obj.name.startswith('Default__')
                and obj.metaclass_name == 'BlueprintGeneratedClass'][:48]
    descriptors = describe(catalog, tuple({obj.class_index: catalog.by_index[obj.class_index]
                                          for obj in defaults}.values()))
    doubles = []
    for obj in defaults:
        properties = [p for p in descriptors[obj.class_index].properties if p['type'] == 'DoubleProperty']
        if not properties:
            continue
        values = read_values(catalog, obj)
        for prop in properties:
            key = (prop['owner_index'], prop['name'])
            if key in values.values:
                assert type(values.values[key]) is float
                doubles.append({'object': obj.name, 'property': prop['name'], 'value': values.values[key]})
        if doubles:
            break
    assert doubles, 'No loaded double specimen found in the bounded class sample'
    output = {'pid': catalog.pid, 'strings': inspected, 'doubles': doubles}
    path = Path(__file__).resolve().parents[1] / 'evidence/introspection-strings-double-live.json'
    path.write_text(json.dumps(output, indent=2), encoding='utf-8')
    print('Live original-core string inspection and Blueprint double reads passed.')


if __name__ == '__main__': main()
