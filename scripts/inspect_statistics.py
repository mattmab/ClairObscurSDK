"""Read-only Statistics capability survey; installs no hooks or third-party DLLs."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture
from expedition33.reflection import describe
from expedition33.tracing import prepare_trace
from expedition33.values import read_values
from expedition33._reader import ReadBatch

LEADS = ('BattleSummary', 'BattleManager', 'BattleDamages', 'CharacterStats',
         'OnCharacterReceivedDamage', 'OnDamageReceived', 'FreeAimShooterBattle')

def main():
    catalog = capture()
    selected = [o for o in catalog.objects if any(s in o.name for s in LEADS)]
    rows = []
    with ReadBatch(catalog.pid):
        for obj in selected:
            row = dict(path=catalog.path_name(obj), cls=obj.class_name,
                       index=obj.index, serial=obj.serial)
            try:
                if obj.class_name in ('Function', 'Class', 'BlueprintGeneratedClass'):
                    descriptor = describe(catalog, (obj,))[obj.index]
                    row['properties'] = [dict(p) for p in descriptor.properties]
                    row['function'] = dict(descriptor.function) if descriptor.function else None
                    if obj.class_name == 'Function':
                        try:
                            plan = prepare_trace(catalog, obj)
                            row['trace'] = dict(supported=True, capture_size=plan.capture_size)
                        except (ValueError, RuntimeError) as exc:
                            row['trace'] = dict(supported=False, reason=str(exc))
                elif not obj.object_flags & 0x10:
                    values = read_values(catalog, obj)
                    row['values'] = {f'{k[0]}:{k[1]}': repr(v) for k,v in values.values.items()}
                    row['errors'] = {str(k): str(v) for k,v in values.errors.items()}
            except Exception as exc:
                row['error'] = str(exc)
            rows.append(row)
    out = ROOT / 'evidence/statistics-reference/live-capabilities.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(pid=catalog.pid, rows=rows), indent=2), encoding='utf-8')
    print(out)
    for row in rows:
        if 'trace' in row or row.get('error'):
            print(row['path'], row.get('trace', row.get('error')))
    print('Objects examined:', len(rows))

if __name__ == '__main__': main()
