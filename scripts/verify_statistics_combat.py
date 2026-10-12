"""Compare preserved combat observations; resolve identities read-only if still live."""
import json
import math
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33.catalog import capture

folder = ROOT / 'evidence/statistics-reference'
rows = [json.loads(line) for line in (folder / 'v29-combat-events.jsonl').read_text().splitlines()]
start = max(i for i, row in enumerate(rows) if row['kind'] == 'enabled')
events = [row['value'] for row in rows[start:] if row['kind'] == 'damage']
def summary(name):
    candidates = [r['summary'] for r in json.loads((folder / name).read_text()) if r.get('summary')]
    if len(candidates) != 1:
        raise ValueError('Expected one live battle summary')
    return candidates[0]
before = summary('v29-precombat-summary.json')
after = summary('v29-postcombat-summary.json')
if before['path'] != after['path']:
    raise ValueError('Battle summary changed between observations')
delta = after['values']['TotalReceivedDamagesByEnemies'] - before['values']['TotalReceivedDamagesByEnemies']
total = math.fsum(e['arguments']['ReceivedDamages'] for e in events)
catalog = capture()
identities = []
for event in events:
    fields = {}
    for field in ('SourceCharacter', 'TargetCharacter', 'BattleDamages'):
        observed = event['arguments'][field]
        obj = catalog.by_index.get(observed['index'])
        matched = bool(obj and observed['pid'] == catalog.pid and
                       obj.serial == observed['serial'] and obj.address == observed['address'])
        fields[field] = {'observed': observed, 'current_identity_matches': matched,
                         'path': catalog.path_name(obj) if matched else None,
                         'class_name': obj.class_name if matched else None,
                         'lifetime_guarantee': False}
    identities.append({'sequence': event['sequence'], 'fields': fields})
report = dict(recorded_at=datetime.now(timezone.utc).isoformat(), candidate='v29',
              events=len(events), event_sum=total, enemy_damage_delta=delta,
              numerical_difference=delta-total,
              matches_delta=math.isclose(total,delta,rel_tol=1e-12,abs_tol=1e-8),
              consecutive_sequences=[e['sequence'] for e in events]==list(range(1,len(events)+1)),
              sessions=sorted(set(e['session'] for e in events)),
              threads=sorted(set(e['thread'] for e in events)),
              before=before, after=after, identities=identities,
              limitations=['Entry notifications, not universal proof of completed hits',
                           'Serial zero is an observation, not a retained handle',
                           'No defensive attempts or full DLL parity validated'])
(folder / 'v29-combat-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
