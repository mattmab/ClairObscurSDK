"""Send one idempotently tracked command to the local Scene Editor host."""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from expedition33.controller_commands import CommandClient

def request(command,arguments=None,timeout=90):
    location=Path((ROOT/'evidence/scene-editor/connection-path.txt').read_text(encoding='utf8').strip())
    client=CommandClient(json.loads(location.read_text(encoding='utf8')))
    result=client.request(command,arguments or {});deadline=time.monotonic()+timeout
    while result.get('state') in ('queued','running') and time.monotonic()<deadline:
        time.sleep(.1);result=client.request('request.status',request_id=result['id'])
    if result.get('state')!='completed':raise RuntimeError(str(result))
    return result['result']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command');p.add_argument('arguments',nargs='?',default='{}');args=p.parse_args()
    print(json.dumps(request(args.command,json.loads(args.arguments)),indent=2))
