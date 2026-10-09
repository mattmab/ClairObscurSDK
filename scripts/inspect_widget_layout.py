"""Read-only live UMG layout/value-codec inventory; executes no engine function."""
from dataclasses import asdict
import json
from pathlib import Path
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33._pod_values import PROFILES, validate_profile

ROOT = Path(__file__).resolve().parents[1]
FUNCTIONS = {
    'CanvasPanelSlot': ('SetPosition', 'SetSize', 'SetOffsets', 'SetAnchors',
                        'SetAlignment', 'SetAutoSize', 'GetPosition', 'GetSize'),
    'UserWidget': ('SetDesiredSizeInViewport', 'SetPositionInViewport'),
    'TextBlock': ('SetText', 'SetColorAndOpacity', 'SetFont'),
    'Button': ('SetBackgroundColor', 'SetColorAndOpacity'),
    'Slider': ('SetValue', 'SetMinValue', 'SetMaxValue', 'SetStepSize'),
    'WidgetBlueprintLibrary': ('SetInputMode_UIOnlyEx', 'SetInputMode_GameAndUIEx',
                               'SetInputMode_GameOnly', 'SetFocusToGameViewport'),
    'Widget': ('SetKeyboardFocus', 'SetUserFocus', 'HasKeyboardFocus', 'SetIsEnabled'),
}


def main():
    catalog = capture()
    selected, missing = [], []
    for owner, names in FUNCTIONS.items():
        cls = catalog.find_class(owner)
        for name in names:
            rows = [o for o in catalog.objects if o.outer_index == cls.index and o.name == name]
            if len(rows) != 1:
                missing.append({'owner': owner, 'name': name, 'matches': len(rows)})
            else:
                selected.append(rows[0])
    descriptors = describe(catalog, selected)
    structs = {p['struct_index'] for d in descriptors.values() for p in d.properties
               if p['type'] == 'StructProperty'}
    # Include nested reflected structures, bounded to three levels for this audit.
    struct_descriptors = {}
    for _ in range(3):
        pending = structs - struct_descriptors.keys()
        if not pending:
            break
        current = describe(catalog, [catalog.by_index[index] for index in sorted(pending)])
        struct_descriptors.update(current)
        structs.update(p['struct_index'] for d in current.values() for p in d.properties
                       if p['type'] == 'StructProperty')

    def encode(descriptor):
        return {'object': asdict(descriptor.object),
                'path': catalog.path_name(descriptor.object),
                'owners': [dict(row) for row in descriptor.owners],
                'function': dict(descriptor.function) if descriptor.function else None,
                'properties': [dict(row) for row in descriptor.properties]}
    validated = [validate_profile(catalog, d, struct_descriptors).path
                 for d in struct_descriptors.values() if catalog.path_name(d.object) in PROFILES]
    result = {'pid': catalog.pid, 'executed': False, 'validated_pod_profiles': validated,
              'functions': [encode(d) for d in descriptors.values()],
              'structs': [encode(d) for d in struct_descriptors.values()], 'missing': missing,
              'unexpanded_structs': sorted(structs - struct_descriptors.keys())}
    output = ROOT / 'evidence/widget-layout-schema.json'
    output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    for row in result['functions']:
        print(row['path'], [(p['name'], p['type'], p.get('struct_name'), p['offset'], p['element_size'])
                            for p in row['properties']])
    for row in result['structs']:
        print('STRUCT', row['path'], row['owners'][0]['size'],
              [(p['name'], p['type'], p['offset'], p['element_size']) for p in row['properties']])
    print('Missing:', missing)


if __name__ == '__main__':
    main()
