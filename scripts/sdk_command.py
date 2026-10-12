"""One structured command client for humans, scripts and notebook users."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from expedition33.controller_commands import CommandClient

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection',required=True,type=Path)
    parser.add_argument('--id',help='Existing request ID for request.status; optional ID for a new request')
    parser.add_argument('--wait',type=float,default=30)
    parser.add_argument('command')
    parser.add_argument('arguments',nargs='?',default='{}',help='JSON object of named arguments')
    args=parser.parse_args()
    if args.command in ('request.status','request.cancel') and not args.id: parser.error('request.status/request.cancel requires --id')
    client=CommandClient(json.loads(args.connection.read_text(encoding='utf8')))
    rid=args.id or uuid.uuid4().hex
    reply=client.request(args.command,json.loads(args.arguments),request_id=rid)
    deadline=time.monotonic()+max(0,args.wait)
    while reply.get('state') in ('queued','running') and time.monotonic()<deadline:
        time.sleep(.1)
        reply=client.request('request.status',request_id=rid)
    print(json.dumps(reply,indent=2))
    return 0 if reply.get('state')=='completed' else 2

if __name__=='__main__': raise SystemExit(main())
