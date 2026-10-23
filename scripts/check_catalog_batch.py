from check_installed_catalog import client,request,ROOT
import json,time
c=client();rows=request(c,'catalog.list');results=[]
for row in rows:
    request(c,'catalog.spawn',{'model_id':row['id']});deadline=time.monotonic()+90
    while True:
        status=request(c,'catalog.status')
        if status.get('state') in ('spawned','failed','retired-on-travel'):break
        if time.monotonic()>deadline:raise RuntimeError('Timed out '+row['id'])
        time.sleep(.5)
    destroyed=request(c,'catalog.destroy');after=request(c,'catalog.status')
    result=dict(id=row['id'],status=status,cleanup=after)
    results.append(result);(ROOT/'dist/catalog-integrated/runtime-catalog-check.json').write_text(json.dumps(results,indent=2))
    print(row['id'],status.get('state'),status.get('uploaded'),after.get('native'),flush=True)
    if status.get('state')!='spawned':break
