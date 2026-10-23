"""Use the installed authenticated command client; never print its credentials."""
from pathlib import Path
import json,sys,time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.controller_commands import CommandClient

def client():
    files=list(Path('S:/SteamLibrary/steamapps/common/Expedition 33/SDK/settings/controller').glob('controller-*.json'))
    if len(files)!=1:raise RuntimeError('Expected exactly one installed controller connection')
    return CommandClient(json.loads(files[0].read_text()))
def request(c,command,arguments=None):
    result=c.request(command,arguments);deadline=time.monotonic()+50
    while result.get('state') in ('queued','running') and time.monotonic()<deadline:
        time.sleep(.1);result=c.request('request.status',request_id=result['id'])
    with (ROOT/'dist/catalog-integrated/live-events.jsonl').open('a') as f:
        f.write(json.dumps(dict(time=time.time(),command=command,arguments=arguments,result=result))+'\n')
    if result.get('state')!='completed':raise RuntimeError(str(result))
    return result['result']
if __name__=='__main__':
    print(json.dumps(request(client(),sys.argv[1],json.loads(sys.argv[2]) if len(sys.argv)>2 else None)))
