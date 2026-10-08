"""Read-only live catalog verification, including Blueprint subclass discovery."""
import json
from pathlib import Path
import time

from expedition33.catalog import capture


def main():
    started = time.monotonic()
    catalog = capture()
    assert len(catalog.select('Object')) == len(catalog.objects)
    result = {'pid': catalog.pid, 'objects': len(catalog.objects),
              'classes': len(catalog.classes), 'elapsed_seconds': time.monotonic() - started,
              'roots': {}}
    for name in ('World', 'GameInstance', 'LocalPlayer', 'PlayerController', 'Pawn'):
        rows = [obj for obj in catalog.select(name) if not obj.name.startswith('Default__')]
        result['roots'][name] = [
            {'index': obj.index, 'serial': obj.serial, 'name': obj.name, 'class': obj.class_name,
             'parents': [catalog.classes[index].name for index in catalog.ancestors(obj.class_index)],
             'outer_names': [owner.name for owner in catalog.outer_chain(obj)]}
            for obj in rows[:32]]
    assert result['roots']['World'], 'No live World observed'
    assert result['roots']['PlayerController'], 'No live PlayerController observed'
    # Require a real subclass specimen; exact-name filtering cannot pass this.
    assert any(row['class'] != 'PlayerController' for row in result['roots']['PlayerController'])
    destination = Path(__file__).resolve().parents[1] / 'evidence/introspection-catalog-live.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
