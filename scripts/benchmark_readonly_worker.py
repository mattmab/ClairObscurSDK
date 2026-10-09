"""Compare equal live read requests; never invoke an engine function."""
import json
from pathlib import Path
import subprocess
import time

from expedition33.catalog import capture, capture_selected
from expedition33.reflection import describe
from expedition33._reader import ReadBatch

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = capture()
    owner = catalog.find_class('KismetMathLibrary').index
    matches = [obj for obj in catalog.objects if obj.outer_index == owner and obj.name == 'Add_IntInt']
    assert len(matches) == 1
    function = matches[0]
    identity = ((function.index, function.serial, function.address),)
    started = time.perf_counter()
    ordinary = [(describe(catalog, [function]), capture_selected(catalog.pid, identity)) for _ in range(5)]
    ordinary_seconds = time.perf_counter() - started
    started = time.perf_counter()
    with ReadBatch(catalog.pid) as batch:
        worker_pid = batch._process.pid
        repeated = [(describe(catalog, [function]), capture_selected(catalog.pid, identity)) for _ in range(5)]
    worker_seconds = time.perf_counter() - started
    for (a, ac), (b, bc) in zip(ordinary, repeated):
        assert a == b and ac.objects == bc.objects and ac.classes == bc.classes
    assert batch._process.poll() == 0 and not batch._thread.is_alive()
    # Exercise the native allowlist directly, bypassing the Python guard. It
    # must reject the session opcode before the mutation-capable query runner.
    executable = ROOT / 'build/readonly-worker/research_probe.exe'
    worker = subprocess.Popen([str(executable), '--reader-session', str(catalog.pid)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    ready = json.loads(worker.stdout.readline())
    assert ready['event'] == 'reader_ready'
    output, error = worker.communicate('--session\n', timeout=10)
    assert worker.returncode == 1 and 'READER_OPERATION_NOT_ALLOWED' in output
    record = dict(pid=catalog.pid, worker_pid=worker_pid, queries=10,
        ordinary_seconds=ordinary_seconds, worker_seconds=worker_seconds,
        observations_equal=True, worker_exit_code=batch._process.returncode,
        reader_thread_stopped=True, native_mutation_opcode_rejected=True, engine_calls=0)
    (ROOT / 'evidence/readonly-worker-benchmark.json').write_text(json.dumps(record, indent=2))
    print(json.dumps(record))


if __name__ == '__main__':
    main()
