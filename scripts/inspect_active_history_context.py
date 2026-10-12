"""Read-only reflected engine/viewport/world links for history provenance."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching
from expedition33.values import read_object_reference

pid = int(sys.argv[1])
with ReadBatch(pid):
    catalog = capture_matching(pid, classes=('GameEngine',))
    engines = [o for o in catalog.select('GameEngine') if not o.object_flags & 0x10]
    if len(engines) != 1:
        raise RuntimeError('Ambiguous engine')
    current = engines[0]
    records = []
    for owner_name, field in [('Engine', 'GameViewport'), ('GameViewportClient', 'World'),
                              ('World', 'OwningGameInstance')]:
        owner = catalog.by_index[catalog.find_class(owner_name).index]
        previous = current
        current, catalog = read_object_reference(catalog, current, owner, field)
        records.append(dict(source=catalog.path_name(previous), field=field,
                            target=catalog.path_name(current) if current else None))
        if current is None:
            break
    print(json.dumps(records, indent=2))
