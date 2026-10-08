"""Exercise the same fingerprint gate used before live runtime discovery."""
import json
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
source = Path(r'D:\HobbyDevelopment\Analysis\ClairObscurSDK\23765773-218a2478\inputs\SandFall-Win64-Shipping.exe')
fixture = root / 'build/compatibility/changed-image.bin'
fixture.parent.mkdir(parents=True, exist_ok=True)
probe = root / 'build/research-probe/research_probe.exe'
def check(path):
    result = subprocess.run([str(probe), '--check-image', str(path)], capture_output=True, text=True, timeout=30)
    return result.returncode, json.loads(result.stdout or result.stderr)

accepted = check(source)
assert accepted == (0, {'event': 'build_supported'})
shutil.copyfile(source, fixture)
with fixture.open('r+b') as file:
    file.seek(-1, 2)
    byte = file.read(1)
    file.seek(-1, 2)
    file.write(bytes([byte[0] ^ 1]))
changed = check(fixture)
assert changed[0] != 0 and 'UNSUPPORTED_BUILD_SHA256=' in changed[1]['message']
fixture.write_bytes(b'Unrecognized game build')
short = check(fixture)
assert short[0] != 0 and short[1]['message'] == 'UNSUPPORTED_BUILD_SIZE'
missing = check(fixture.parent / 'absent.exe')
assert missing[0] != 0 and missing[1]['message'] == 'MODULE_FILE_OPEN_FAILED'
result = {'supported_accepted': True, 'same_size_single_byte_change': changed,
          'different_size': short, 'missing_file': missing, 'no_process_attachment': True}
(root / 'evidence/compatibility.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
