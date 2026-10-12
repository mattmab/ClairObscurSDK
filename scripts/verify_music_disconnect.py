"""Read-only verification after terminating the test controller externally."""
import json
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
report = json.loads((ROOT/'evidence/music-reference-owner-live.json').read_text(encoding='utf8'))
index, serial, address = report['gi']
proc = subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'), '--read-values',
                       str(report['pid']), f'{index}:{serial}:{address:x}'], capture_output=True, text=True, timeout=30)
rows = [json.loads(line) for line in proc.stdout.splitlines()]
matches = [r for r in rows if r.get('event') == 'stored_value' and r.get('name') == 'InteractiveMusicSystem']
report['disconnect_observation_utc'] = datetime.now(timezone.utc).isoformat()
report['disconnect_reader_exit'] = proc.returncode
report['disconnect_reference_rows'] = matches
report['disconnect_reader_stderr'] = proc.stderr
original_index, original_serial, original_address = report['original']
expected = {'index': original_index, 'serial': original_serial, 'address': hex(original_address)}
# Preserve raw values even if a protocol change requires manual interpretation.
report['disconnect_expected_reference'] = expected
observed = matches[0].get('value', {}).get('$reference', {}) if len(matches) == 1 else {}
report['disconnect_original_restored'] = proc.returncode == 0 and all(observed.get(k) == v for k,v in expected.items())
saves = Path('C:/Users/Matt/AppData/Local/Sandfall/Saved/SaveGames')
current = {str(p.relative_to(saves)): hashlib.sha256(p.read_bytes()).hexdigest() for p in saves.rglob('*.sav')}
report['save_hashes_unchanged'] = current == report['before_hashes']
(ROOT/'evidence/music-reference-disconnect.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k.startswith('disconnect_') or k=='save_hashes_unchanged'},indent=2))
