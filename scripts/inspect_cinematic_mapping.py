import sys,json
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,'src')
from expedition33.catalog import capture,capture_matching
from expedition33.values import read_values
from expedition33._reader import ReadBatch
from expedition33 import RuntimeQueryError
names=('DA_SEQ_MyFlower_P1','CS_MyFlower_P1','CS_MyFlower_P1_PreRenderIntro','DA_GA_CIN_MyFlower_P1','MCS_MyFlower_P1')
with ReadBatch(9616):
 try:
  matched=capture_matching(9616,names=names)
 except RuntimeQueryError as error:
  Path('evidence/cinematics-mapping-current.json').write_text(json.dumps(dict(
   utc=datetime.now(timezone.utc).isoformat(),pid=9616,names=names,error=str(error),
   authoritative_mapping=False,scope='Current loaded objects only; not an installed-content inventory'),indent=2),encoding='utf8')
  raise
 c=capture()
 rows=[]
 for o in matched.objects:
  if o.name not in names:continue
  v=read_values(c,c.resolve(o))
  rows.append(dict(path=c.path_name(o),cls=o.class_name,values={str(k):str(x) for k,x in v.values.items()},errors={str(k):str(x) for k,x in v.errors.items()}))
 Path('evidence/cinematics-mapping-current.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
 print(json.dumps(rows,indent=2))
