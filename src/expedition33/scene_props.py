"""Scene-owned static props using the existing World Builder map owner."""
from .map_spawn_plan import SpawnPlan
from .map_runtime import MapRuntime,context

def plan(document):
 rows=document.get('props',[])
 if type(rows) is not list or len(rows)>16:raise ValueError('Up to sixteen scene props')
 return SpawnPlan(dict(format='e33.world-builder.scene',version=1,name=document['name'],world=document['target_map'],objects=rows,assets=sorted({r['asset'] for r in rows})))

class SceneProps:
 def __init__(self,runtime,document):self.map=MapRuntime(runtime.scope);self.document=document
 def prepare(self):
  if getattr(self.map.scope._session._transport,'map_runtime_owner_slots',1)<2:raise RuntimeError('Independent cinematic prop ownership hook required')
  ctx=context(self.map.scope)
  if not ctx or not ctx['ready']:raise RuntimeError('Scene props require an admitted world')
  self.map.load(plan(self.document),ctx)
 def close(self):return self.map.close()
 def retire_world(self):return self.map.retire_world()
