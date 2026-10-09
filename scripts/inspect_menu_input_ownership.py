"""Read-only live CommonUI/focus inventory; no setters or input events."""
from dataclasses import asdict
import json
from pathlib import Path

from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33.values import read_values

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = capture()
    names = ('CommonUIActionRouterBase', 'CommonActivatableWidget',
             'CommonActivatableWidgetContainerBase', 'CommonInputSubsystem',
             'Widget', 'UserWidget', 'PlayerController', 'LocalPlayer')
    result = dict(pid=catalog.pid, read_only=True, classes={}, instances={}, functions=[], observations=[])
    selected = []
    for name in names:
        try:
            cls = catalog.by_index[catalog.find_class(name).index]
        except Exception as error:
            result['classes'][name] = {'error': str(error)}
            continue
        result['classes'][name] = {'object': asdict(cls), 'path': catalog.path_name(cls)}
        selected.append(cls)
        instances = [obj for obj in catalog.select(name) if not obj.object_flags & 0x10
                     and catalog.path_name(obj).startswith(('/Engine/Transient.', '/Game/Levels/'))]
        result['instances'][name] = [dict(object=asdict(o), path=catalog.path_name(o)) for o in instances[:64]]
        for fn in catalog.objects:
            if fn.outer_index == cls.index and fn.class_name == 'Function' and any(
                    term in fn.name.lower() for term in ('focus', 'activat', 'input', 'enabled')):
                selected.append(fn)
        if name in ('CommonUIActionRouterBase', 'CommonActivatableWidget', 'PlayerController'):
            for obj in instances[:64]:
                observed = read_values(catalog, obj)
                # Keep scalar state only; no recursive native pointer serialization.
                fields = {f'{owner}:{field}': value for (owner, field), value in observed.values.items()
                          if type(value) in (bool, int, float, str) or value is None}
                errors = {f'{owner}:{field}': str(value) for (owner, field), value in observed.errors.items()}
                result['observations'].append(dict(path=catalog.path_name(obj), fields=fields, errors=errors))
    descriptors = describe(catalog, selected)
    for descriptor in descriptors.values():
        result['functions'].append(dict(path=catalog.path_name(descriptor.object),
            object=asdict(descriptor.object), function=dict(descriptor.function) if descriptor.function else None,
            owners=[dict(row) for row in descriptor.owners],
            properties=[dict(row) for row in descriptor.properties]))
    (ROOT / 'evidence/menu-input-ownership.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({name: len(rows) for name, rows in result['instances'].items()}, indent=2))
    for row in result['observations']:
        active = {key: value for key, value in row['fields'].items() if key.endswith(':bIsActive')}
        if any(active.values()):
            print('Active:', row['path'])
    print('Read-only descriptors:', len(descriptors))


if __name__ == '__main__':
    main()
