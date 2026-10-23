import sys,json
from pathlib import Path
sys.path[:0]=['src','scripts']
from check_installed_catalog import client,request
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching,CatalogObject
from expedition33.values import read_values_with_references,StoredArray,StoredStruct
pid=request(client(),'catalog.status')['native']['actor']['pid']
roots={x['path']:x for x in json.load(open('dist/verso-2b/lit-material-survey.json'))}
with ReadBatch(pid,_executable=Path('build/release/research-probe-mesh-v24/research_probe.exe')):
 c=capture_matching(pid,classes=('MaterialInstanceConstant',),names=('TextureParameterValue','MaterialParameterInfo','Guid'))
 objects=[o for o in c.objects if o.class_name=='MaterialInstanceConstant' and not o.object_flags&0x10 and c.path_name(o).startswith('/Game/')]
 cache={}
 def info(o):
  global c
  if o.index in cache:return cache[o.index]
  v,c=read_values_with_references(c,o,fields=('Parent','TextureParameterValues'))
  d={k[1]:x for k,x in v.values.items()};params=[]
  for item in getattr(d.get('TextureParameterValues'),'items',()):
   f=item.fields;pi=f.get('ParameterInfo');name=pi.fields.get('Name') if pi else None
   if name:params.append(name)
  result=(d.get('Parent'),params);cache[o.index]=result;return result
 rows=[]
 for o in objects[:3000]:
  current=o;params=[];seen=set()
  while current and current.class_name=='MaterialInstanceConstant' and current.index not in seen and len(seen)<12:
   seen.add(current.index);current,p=info(current);params.extend(p)
  root=c.path_name(current) if current else ''
  rv=roots.get(root,{}).get('values',{})
  if rv.get('MaterialDomain')!=0 or rv.get('ShadingModel')!=1 or rv.get('BlendMode') not in (0,1):continue
  if any(s in root.lower() for s in ('/fx/','water','tree','invisible','grapple','blockout','debug','magic')):continue
  params=list(dict.fromkeys(params))
  picks=[p for p in params if any(s in p.lower() for s in ('base color','basecolor','albedo','diffuse')) and not any(s in p.lower() for s in ('normal','mask','detail','variation'))]
  if picks:rows.append(dict(path=c.path_name(o),root=root,parameter=picks[0],parameters=params,root_values=rv))
 Path('dist/verso-2b/lit-instance-survey.json').write_text(json.dumps(rows,indent=2))
 print(json.dumps(dict(inspected=len(objects[:3000]),candidates=len(rows),roots=sorted(set(x['root'] for x in rows)))))
