"""Bounded telemetry cost without a game/controller restart or desktop input."""
import json
from pathlib import Path
import statistics
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.workflow_telemetry import Telemetry

def main():
    samples=[]
    for _ in range(5):
        with tempfile.TemporaryDirectory(dir=ROOT/'.test-tmp') as directory:
            telemetry=Telemetry(Path(directory)/'timings.jsonl')
            start=time.perf_counter()
            for number in range(10000):
                telemetry.record('native.poll','native_transport',time.time(),.01,True,ipc_round_trips=1)
            elapsed=time.perf_counter()-start
            totals=telemetry.snapshot()['operations']
            assert totals[0]['count']==10000 and totals[0]['ipc_round_trips']==10000
            telemetry.close()
            samples.append(elapsed*1000/10000)
    report=dict(count_per_sample=10000, samples_ms_per_record=samples,
                median_ms_per_record=statistics.median(samples), max_ms_per_record=max(samples),
                note='Total instrumentation cost including rotating disk log and aggregates; no baseline speedup claimed.')
    (ROOT/'evidence/workflow-telemetry-cost.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))

if __name__=='__main__':main()
