"""Execute trusted local Python in the running SDK; never sends UI input."""
import argparse,hashlib,json,sys,time,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.controller_commands import CommandClient

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--wait',type=float,default=20.)
    sub=ap.add_subparsers(dest='operation',required=True)
    sub.add_parser('inspect')
    p=sub.add_parser('exec');p.add_argument('source')
    p=sub.add_parser('file');p.add_argument('path',type=Path)
    p=sub.add_parser('status');p.add_argument('request_id')
    args=ap.parse_args()
    if not 0<=args.wait<=60:ap.error('--wait must be between 0 and 60 seconds')
    files=list((ROOT/'settings/python-control').glob('controller-*.json'))
    if not files:raise SystemExit('No active local Python endpoint; enable Python control in the SDK controller')
    file=max(files,key=lambda p:p.stat().st_mtime_ns)
    client=CommandClient(json.loads(file.read_text(encoding='utf8')))
    rid=args.request_id if args.operation=='status' else uuid.uuid4().hex
    if args.operation=='exec':command='python.execute';arguments={'source':args.source}
    elif args.operation=='file':
        script=args.path.resolve(strict=True);command='python.file';arguments={'path':str(script),'sha256':hashlib.sha256(script.read_bytes()).hexdigest()}
    elif args.operation=='inspect':command='python.inspect';arguments={}
    else:command='request.status';arguments={}
    reply=client.request(command,arguments,request_id=rid);deadline=time.monotonic()+args.wait
    while reply.get('state') in ('queued','running') and time.monotonic()<deadline:
        time.sleep(.15);reply=client.request('request.status',request_id=rid)
    print(json.dumps(reply,indent=2,ensure_ascii=False))
    if reply.get('state') in ('queued','running'):return 0
    return 0 if reply.get('state')=='completed' and not reply.get('result',{}).get('failed',False) else 1

if __name__=='__main__':raise SystemExit(main())
