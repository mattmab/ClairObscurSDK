import sys,json
sys.path.insert(0,'src')
from expedition33.catalog import capture, capture_matching
from expedition33.reflection import describe
from expedition33.values import read_values
from expedition33._reader import ReadBatch
from pathlib import Path
with ReadBatch(9616):
 selected=capture_matching(9616,names=('CommonVideoPlayer','MediaPlayer','SetVideo','PlayFromStart','Pause','Play','Close','SetRate','IsReady','IsPlaying','IsPaused','IsClosed','GetDuration','GetTime','SetLooping','TestvIDEO'),classes=('FileMediaSource',))
 c=capture(); rows=[]
 for o in selected.objects:
  if o.class_name=='Function' and c.by_index[o.outer_index].name not in ('MediaPlayer','CommonVideoPlayer'):continue
  if o.class_name not in ('Class','Function','FileMediaSource'):continue
  d=describe(c,(o,))[o.index] if o.class_name != 'FileMediaSource' else None
  row=dict(path=c.path_name(o),cls=o.class_name,properties=[dict(p) for p in d.properties] if d else [],function=dict(d.function) if d and d.function else None)
  if o.class_name=='FileMediaSource':
   v=read_values(c,o);row['values']={str(k):str(x) for k,x in v.values.items()}
  rows.append(row)
 Path('evidence/media-live-schema.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 for r in rows:
  if r['cls']=='Function': print(r['path'],r['function'])
  elif r['cls']=='FileMediaSource':print(r['path'],r.get('values'))


