"""Reproducible same-command cold CLI versus warm reusable client benchmark."""
import argparse
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
import uuid
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.controller_commands import CommandClient

def call(client, name):
    rid=uuid.uuid4().hex
    reply=client.request(name,request_id=rid); trips=1
    deadline=time.monotonic()+15
    while reply.get('state') in ('queued','running') and time.monotonic()<deadline:
        time.sleep(.005)
        reply=client.request('request.status',request_id=rid); trips+=1
    if reply.get('state')!='completed': raise RuntimeError(str(reply))
    return reply, trips

def summarize(rows):
    values=sorted(r['ms'] for r in rows)
    return dict(count=len(rows),median_ms=statistics.median(values),
                p95_ms=values[math.ceil(len(values)*.95)-1],total_ms=sum(values),
                failures=sum(not r['success'] for r in rows),retries=0,
                process_launches=sum(r['process_launches'] for r in rows),
                ipc_round_trips=sum(r.get('ipc_round_trips',0) for r in rows))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--connection',type=Path,required=True)
    parser.add_argument('--count',type=int,default=10)
    parser.add_argument('--output',type=Path,default=ROOT/'evidence/workflow-benchmark.json')
    args=parser.parse_args()
    client=CommandClient(json.loads(args.connection.read_text()))
    records={}
    for command in ('sdk.status','cinematics.status','cinematics.catalog','sdk.object.lookup','sdk.properties','sdk.function.schema'):
        for mode in ('cold_cli','warm_client'):
            rows=[]
            for _ in range(args.count):
                start=time.perf_counter();trips=0;success=False
                if mode=='cold_cli':
                    proc=subprocess.run([sys.executable,str(ROOT/'scripts/sdk_command.py'),
                        '--connection',str(args.connection),command],capture_output=True,text=True,timeout=20)
                    success=proc.returncode==0
                else:
                    _,trips=call(client,command);success=True
                rows.append(dict(ms=(time.perf_counter()-start)*1000,success=success,
                                 process_launches=int(mode=='cold_cli'),ipc_round_trips=trips))
            records[command+'.'+mode]={'summary':summarize(rows),'samples':rows}
    args.output.write_text(json.dumps({'recorded_at':time.time(),'measurements':records,
        'notes':['Cold CLI IPC counts unavailable, reported as null below.',
                 'Cold includes Python startup and CLI 100ms polling; warm polls at 5ms.',
                 'No native gameplay mutation. No desktop input. No model usage telemetry.']},indent=2))
    # Correct unavailable counts rather than claiming zero round trips.
    data=json.loads(args.output.read_text())
    for name,result in data['measurements'].items():
        if name.endswith('cold_cli'):
            result['summary']['ipc_round_trips']=None
            for row in result['samples']: row['ipc_round_trips']=None
    args.output.write_text(json.dumps(data,indent=2))
    print(json.dumps({name:value['summary'] for name,value in data['measurements'].items()},indent=2))

if __name__=='__main__':main()
