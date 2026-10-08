"""Record the permanent-prefix specimen; this does not prove generic GC pinning."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import pefile

root = Path(__file__).resolve().parents[1]
probe = root / 'build/research-probe/research_probe.exe'
def query(*args):
    result = subprocess.run([str(probe), *args], capture_output=True, encoding='utf-8',
                            timeout=120, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[0]['event'] == 'snapshot_start' and rows[-1]['event'] == 'snapshot_end'
    targets = [r for r in rows if r['event'] == 'object']
    assert len(targets) == 1 and rows[-1]['emitted'] == 1
    return rows[0], targets[0]

fn_start, function = query('--reflect-function', 'Actor.IsActorBeingDestroyed')
obj_start, obj = query('--read-bools', 'Default__Actor')
assert fn_start['pid'] == obj_start['pid']
prefix = tuple(fn_start[f'registry_prefix_{field}'] for field in ('0', '4', '8', 'c'))
assert prefix == tuple(obj_start[f'registry_prefix_{field}'] for field in ('0', '4', '8', 'c'))
first, last, capacity, open_flag = prefix
assert 0 < first <= capacity <= fn_start['num_elements'] and last + 1 == first and open_flag == 0
assert 0 <= function['index'] <= last and 0 <= obj['index'] <= last
assert function['class_name'] == 'Function' and obj['class_name'] == 'Actor'

binary = Path(r'D:\HobbyDevelopment\Analysis\ClairObscurSDK\23765773-218a2478\inputs\SandFall-Win64-Shipping.exe')
pe = pefile.PE(str(binary), fast_load=True)
strings = {}
for address in (0x146e04bf8, 0x146e04b38, 0x146e04b78, 0x146e1b568, 0x146e1b5a8):
    data = pe.get_data(address - pe.OPTIONAL_HEADER.ImageBase, 180)
    strings[hex(address)] = data.decode('utf-16le').split('\0')[0]
pe.close()
assert strings['0x146e04bf8'] == 'GC.GatherUnreachable'
assert strings['0x146e1b568'] == 'gc.MaxObjectsNotConsideredByGC'
output = {'timestamp': datetime.now(timezone.utc).isoformat(), 'pid': fn_start['pid'],
          'sha256': fn_start['sha256'], 'registry_prefix': prefix,
          'function': function, 'object': obj, 'binary_diagnostic_strings': strings,
          'scope': 'Observed permanent-prefix membership; shutdown explicitly invalidates ordinary-GC exclusion'}
(root / 'evidence/python-live-lifetime.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output))
