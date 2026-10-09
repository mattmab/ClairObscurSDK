"""Read-only target descriptors for a future owned UMG text-value API."""
from dataclasses import asdict
import json
from pathlib import Path
from expedition33.catalog import capture
from expedition33.reflection import describe

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = capture()
    selected, missing = [], []
    for owner, names in {
        'KismetTextLibrary': ('Conv_StringToText', 'Conv_TextToString'),
        'TextBlock': ('SetText', 'GetText'),
    }.items():
        cls = catalog.find_class(owner)
        for name in names:
            rows = [o for o in catalog.objects if o.outer_index == cls.index and o.name == name]
            if len(rows) == 1:
                selected.append(rows[0])
            else:
                missing.append({'owner':owner, 'name':name, 'matches':len(rows)})
    descriptors = describe(catalog, selected)
    result = {'pid':catalog.pid, 'executed':False, 'missing':missing,
              'functions':[{'object':asdict(d.object), 'path':catalog.path_name(d.object),
                            'owners':[dict(row) for row in d.owners],
                            'function':dict(d.function),
                            'properties':[dict(row) for row in d.properties]}
                           for d in descriptors.values()]}
    (ROOT/'evidence/widget-text-schema.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    for row in result['functions']:
        print(row['path'], row['function']['entry_rva'],
              [(p['name'],p['type'],p['offset'],p['element_size']) for p in row['properties']])
    print('Missing:', missing)


if __name__ == '__main__':
    main()
