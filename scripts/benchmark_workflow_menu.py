"""Explicit opt-in live menu lifecycle benchmark; never starts playback."""
import argparse
import json
from pathlib import Path
import time
from benchmark_workflow import CommandClient, call, summarize
parser=argparse.ArgumentParser()
parser.add_argument('--connection',type=Path,required=True)
args=parser.parse_args()
client=CommandClient(json.loads(args.connection.read_text()))
records={}
try:
    for _ in range(3):
        for command,expected in (('cinematics.menu.open','open'),('cinematics.menu.close','built')):
            clock=time.perf_counter()
            reply,trips=call(client,command)
            result=reply['result']
            success=result['menu']['state']==expected and result['menu']['error'] is None
            records.setdefault(command,[]).append(dict(ms=(time.perf_counter()-clock)*1000,
                success=success,ipc_round_trips=trips,process_launches=0,state=result['menu']['state']))
            if not success: raise RuntimeError('Menu lifecycle state mismatch')
            time.sleep(.1) # Let the existing pause owner restore between cycles.
finally:
    call(client,'cinematics.menu.close')
report={key:{'samples':rows,'summary':summarize(rows)} for key,rows in records.items()}
(Path(__file__).resolve().parents[1]/'evidence/workflow-menu-benchmark.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
