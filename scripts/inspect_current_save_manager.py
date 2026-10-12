"""Read-only, identity-checked save-manager diagnostics; never selects unlocks."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching
from expedition33.values import read_values

with ReadBatch(int(sys.argv[1])):
    catalog = capture_matching(int(sys.argv[1]), classes=('BP_SaveManager_C', 'BP_jRPG_GI_Custom_C'))
    results = []
    for obj in catalog.objects:
        if obj.class_name not in ('BP_SaveManager_C', 'BP_jRPG_GI_Custom_C'):
            continue
        if obj.object_flags & 0x10:
            continue
        observed = read_values(catalog, obj)
        results.append(dict(path=catalog.path_name(obj), index=obj.index, serial=obj.serial,
            fields=[dict(name=key[1], type=kind, value=repr(observed.values.get(key))[:500],
                         error=observed.errors.get(key), truncated=key in observed.truncated)
                    for key, kind in observed.types.items() if any(part in key[1].lower()
                        for part in ('save', 'load', 'slot', 'interactedcinematics', 'gameinstancereference'))]))
    print(json.dumps(results, indent=2))
