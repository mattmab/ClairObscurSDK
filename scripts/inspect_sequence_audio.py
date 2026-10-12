"""Bounded, read-only snapshot of the live music system for replay isolation."""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33 import _decode_query
from expedition33.values import _decode_values

c = capture()
rows = []
for o in c.objects:
    if o.class_name != 'BP_InteractiveMusicSystem_C' or o.name.startswith('Default__'):
        continue
    proc = subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),
        '--read-values', str(c.pid), f'{o.index}:{o.serial}:{o.address:x}'],
        capture_output=True, text=True, timeout=30)
    record = {'path': c.path_name(o), 'identity': [o.index,o.serial,o.address],
        'rows': [json.loads(line) for line in proc.stdout.splitlines()],
        'returncode': proc.returncode, 'stderr': proc.stderr}
    if not proc.returncode:
        start, observations = _decode_query(proc.stdout)
        try:
            decoded = _decode_values(c, o, start, observations)
            record['decoded'] = {str(k): repr(v) for k,v in decoded.values.items()}
            record['decode_errors'] = {str(k): str(v) for k,v in decoded.errors.items()}
        except Exception as error:
            record['decode_failure'] = repr(error)
    rows.append(record)
encoded = json.dumps(rows, indent=2)
(ROOT/'evidence/sequence-audio-state.json').write_text(encoded, encoding='utf8')
(ROOT/('evidence/sequence-audio-state-'+datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.json')).write_text(encoded, encoding='utf8')
print(len(rows), 'live music systems;', sum(r['returncode'] != 0 for r in rows), 'failed')
