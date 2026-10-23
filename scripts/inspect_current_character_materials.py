import sys,json,dataclasses
from pathlib import Path
sys.path[:0]=['src','scripts']
from check_installed_catalog import client,request
from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching,capture_selected,CatalogObject
from expedition33.values import read_values_with_references,StoredArray,StoredStruct
r=request(client(),'catalog.status')['native'];pid=r['driver']['pid']
with ReadBatch(pid,_executable=Path('build/release/research-probe-mesh-v21/research_probe.exe')):
 c=capture_matching(pid,names=('ScalarParameterValue','VectorParameterValue','TextureParameterValue','MaterialParameterInfo','Guid','LinearColor','SkeletalMaterial','MaterialInstanceBasePropertyOverrides'))
 c=c.with_observations(capture_selected(pid,[(r[k]['index'],r[k]['serial'],int(r[k]['address'],16)) for k in ('driver','driver_asset','component')]))
 def conv(v):
  if isinstance(v,CatalogObject):return dict(index=v.index,serial=v.serial,name=v.name,kind=v.class_name,path=c.path_name(v))
  if isinstance(v,StoredArray):return dict(length=v.length,items=[conv(x) for x in v.items])
  if isinstance(v,StoredStruct):return dict(type=v.type_object.name,fields={k:conv(x) for k,x in v.fields.items()},errors=dict(v.errors),truncated=v.truncated)
  return v
 output=[];queue=[c.by_index[r[k]['index']] for k in ('driver','driver_asset','component')];seen=set()
 while queue and len(seen)<100:
  o=queue.pop(0)
  if o.index in seen:continue
  seen.add(o.index)
  fields=('OverrideMaterials','SkinnedAsset') if o.class_name.endswith('Component') else ('Materials',) if o.class_name=='SkeletalMesh' else ('Parent','ScalarParameterValues','VectorParameterValues','TextureParameterValues','BasePropertyOverrides') if o.class_name.startswith('MaterialInstance') else ('MaterialDomain','BlendMode','ShadingModel','ShadingModels','TwoSided','bHasPixelAnimation','bOutputTranslucentVelocity')
  v,c=read_values_with_references(c,o,fields=fields)
  def refs(x):
   if isinstance(x,CatalogObject):
    if x.class_name.startswith(('Material','SkeletalMesh')):queue.append(x)
   elif isinstance(x,StoredArray):
    for y in x.items:refs(y)
   elif isinstance(x,StoredStruct):
    for y in x.fields.values():refs(y)
  for x in v.values.values():refs(x)
  output.append(dict(object=conv(o),values={k[1]:conv(x) for k,x in v.values.items()},errors={k[1]:x for k,x in v.errors.items()}))
 Path('dist/verso-2b/current-character-material-inspection.json').write_text(json.dumps(output,indent=2))
 print(json.dumps(output,indent=2)[:22000])
