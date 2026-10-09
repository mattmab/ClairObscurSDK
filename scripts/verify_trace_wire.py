"""Cross-check Python requests with the compiled native protocol fixture."""
from pathlib import Path
from types import SimpleNamespace
import subprocess
from expedition33 import _trace_wire as wire

root = Path(__file__).resolve().parents[1]
fixture = root / 'build/trace-protocol-fixture/trace_protocol_fixture.exe'
output = root / 'evidence/trace-wire-cross-language'
output.mkdir(parents=True, exist_ok=True)
function = SimpleNamespace(pid=99, index=2, serial=0, address=0x20000)
exemplar = SimpleNamespace(pid=99, index=1, serial=0, address=0x10000)
plan = SimpleNamespace(function=function, parameters=(), parameter_size=0,
    allocation_extent=0, return_offset=65535, function_flags=0x400, entry_rva=0x1234)
requests = {
    'start': wire.encode_request('start', 7, plan=plan, exemplar=exemplar),
    'filtered-start': wire.encode_request('start', 7, plan=plan, exemplar=exemplar, target=exemplar),
    **{op: wire.encode_request(op, 7, 9) for op in ('stop', 'drain', 'status', 'forget')},
}
for name, request in requests.items():
    path = output / (name + '.bin')
    path.write_bytes(request)
    subprocess.run([str(fixture), str(path)], check=True)
print('All six Python trace request variants accepted by native validation.')
