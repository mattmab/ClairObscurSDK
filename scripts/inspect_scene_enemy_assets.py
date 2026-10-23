"""Read exact selected enemy asset metadata after a failed native preflight."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture_matching
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredArray
d=json.loads((ROOT/'evidence/scene-editor/palette-acceptance.json').read_text())
scene=next(e['value'] for e in d['events'] if e['event']=='enemy_roundtrip')
palette=json.loads((ROOT/'mods/SceneEditor/palette.json').read_text());chars={r['id']:r for r in palette['characters']};clips={r['id']:r for r in palette['clips']}
paths=set(json.loads((ROOT/'mods/SceneEditor/sample.scene.json').read_text())['assets'].values())
for actor in scene['actors']:
    paths.update(p['path'] for p in chars[actor['assembly']]['parts'] if p['path'])
    event=next(e for e in scene['events'] if e['target']==actor['id']);paths.add(clips[event['params']['asset']]['path'])
rows=[]
with ReadBatch(38688,_executable=ROOT/'build/release/research-probe-cinematic-v15/research_probe.exe'):
    c=capture_matching(38688,names=sorted({p.rsplit('.',1)[1] for p in paths}))
    for o in c.objects:
        path=c.path_name(o)
        if path not in paths:continue
        fields=('Skeleton','Notifies','bEnableRootMotion','AdditiveAnimType') if o.class_name=='AnimSequence' else ('Skeleton',) if o.class_name=='SkeletalMesh' else ()
        if not fields:continue
        v,observed=read_values_with_references(c,o,fields=fields)
        values={k[1]:observed.path_name(x) if hasattr(x,'class_index') else dict(length=x.length) if isinstance(x,StoredArray) else x for k,x in v.values.items()}
        rows.append(dict(path=path,type=o.class_name,values=values,errors={k[1]:str(x) for k,x in v.errors.items()}))
(ROOT/'evidence/scene-editor/enemy-preflight-inspection.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=1))
