"""External research process: one fresh reader per selected sequence object."""
import json,sys,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from expedition33.catalog import capture,capture_selected
from expedition33.values import read_values
from expedition33.values import _decode_values
from expedition33 import _decode_query
from expedition33.reflection import describe

c=capture()
prefix='/Game/Cinematics/Titles/SequenceTitles/LS_Title_PrologueLumiere'
rows=[]
for o in c.objects:
    path=c.path_name(o)
    if not path.startswith(prefix) or o.class_name in ('Package','MovieSceneCompiledData','MovieSceneBuiltInEasingFunction'): continue
    row={'path':path,'class':o.class_name,'index':o.index,'serial':o.serial}
    try:
        fresh=capture_selected(c.pid,((o.index,o.serial,o.address),))
        fresh=c.with_observations(fresh)
        obj=fresh.resolve(o)
        if obj.class_name=='Function':
            r=subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),'--describe-script',str(c.pid),
                f'{o.index}:{o.serial}:{o.address:x}'],capture_output=True,text=True,timeout=30)
            row['script_rows']=[json.loads(line) for line in r.stdout.splitlines()]
            # Resolve embedded identities against this observed registry only;
            # byte matches are leads, not a bytecode interpretation.
            import struct
            script=next((bytes.fromhex(x['hex']) for x in row['script_rows'] if x['event']=='blueprint_script'),b'')
            by_address={x.address:x for x in c.objects}
            row['object_pointer_matches']=[{'offset':i,'path':c.path_name(by_address[struct.unpack_from('<Q',script,i)[0]])}
                for i in range(max(0,len(script)-7)) if struct.unpack_from('<Q',script,i)[0] in by_address]
            if r.returncode: row['error']=r.stderr
        elif obj.class_name!='BlueprintGeneratedClass':
            r=subprocess.run([str(ROOT/'build/sequence-inspector/research_probe.exe'),'--read-values',str(c.pid),
                f'{o.index}:{o.serial}:{o.address:x}'],capture_output=True,text=True,timeout=30)
            if r.returncode: raise RuntimeError(r.stderr)
            start,observations=_decode_query(r.stdout)
            row['raw_observations']=observations
            values=_decode_values(fresh,obj,start,observations)
            row['values']={str(k):repr(v) for k,v in values.values.items()}
            row['errors']={str(k):repr(v) for k,v in values.errors.items()}
    except Exception as e: row['error']=str(e)
    rows.append(row)
(ROOT/'evidence/sequence-track-inspection.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print(len(rows),'objects;',sum('error' in r for r in rows),'failed objects;',sum(len(r.get('errors',{})) for r in rows),'unreadable properties')
