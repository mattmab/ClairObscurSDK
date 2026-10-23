"""Read-only loaded sound candidates and selected cue settings."""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture
from expedition33._reader import ReadBatch
from expedition33.values import read_values_with_references,StoredStruct
c=capture();rows=[]
with ReadBatch(c.pid):
    for o in c.objects:
        if o.class_name!='SoundWave':continue
        path=c.path_name(o)
        if not any(s in path.lower() for s in ('leather_soft_short_main_02','whoosh','swoosh','swing','slash','sfx_ui_global_paint_enter_01')):continue
        v,observed=read_values_with_references(c,o,fields=('Volume','Pitch','Duration','SoundClassObject','bVirtualizeWhenSilent'))
        rows.append(dict(path=path,values={k[1]:observed.path_name(x) if hasattr(x,'class_index') else x for k,x in v.values.items()},errors={k[1]:str(x) for k,x in v.errors.items()}))
    classes=[]
    for o in c.select('SoundClass'):
        if o.name not in ('SoundClass_PlaceHolder_Guillaume','Soundclass_CS_SFX','Soundclass_UI','Master'):continue
        v,observed=read_values_with_references(c,o,fields=('Properties','ParentClass'))
        def copied(x):
            if isinstance(x,StoredStruct):return {k:copied(a) for k,a in x.fields.items()}
            if hasattr(x,'class_index'):return observed.path_name(x)
            return x
        classes.append(dict(path=c.path_name(o),values={k[1]:copied(x) for k,x in v.values.items()},errors={k[1]:str(x) for k,x in v.errors.items()}))
target=ROOT/'evidence/runtime-cinematic-audio-20261017.json'
target.write_text(json.dumps(dict(pid=c.pid,read_only=True,sounds=rows,classes=classes),indent=2)+'\n')
print(json.dumps(dict(output=str(target),sounds=len(rows))))
