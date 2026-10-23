import sys,json
from pathlib import Path
sys.path[:0]=['src','scripts']
from check_installed_catalog import client,request
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching
from expedition33.values import read_values_with_references
pid=request(client(),'catalog.status')['native']['actor']['pid']
with ReadBatch(pid,_executable=Path('build/release/research-probe-mesh-v24/research_probe.exe')):
 c=capture_matching(pid,classes=('Material',))
 rows=[]
 for o in c.objects:
  if o.class_name!='Material' or o.object_flags&0x10:continue
  path=c.path_name(o)
  if not path.startswith('/Game/'):continue
  v,c=read_values_with_references(c,o,fields=('MaterialDomain','BlendMode','ShadingModel','TwoSided'))
  row=dict(path=path,index=o.index,values={k[1]:x for k,x in v.values.items()},errors={k[1]:x for k,x in v.errors.items()})
  rows.append(row)
 Path('dist/verso-2b/lit-material-survey.json').write_text(json.dumps(rows,indent=2,default=str))
 print(json.dumps(rows,default=str))
