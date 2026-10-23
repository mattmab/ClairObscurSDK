"""Generate only the cinematic adapter's fixed VFX spawn contract."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
report=json.loads((ROOT/'evidence/runtime-cinematic-effects-20261017.json').read_text())
assert report['read_only']
rows=[next(r for r in report['functions'] if r['path']==path) for path in (
    '/Script/Niagara.NiagaraFunctionLibrary:SpawnSystemAtLocation',)]
out=['#pragma once','// Fixed native adapter contracts from the live effects report.','namespace e33_runtime_cinematic {']
for i,row in enumerate(rows):
    fields=[]
    for p in row['parameters']:
        constraint=p.get('property_class_name','')
        # Niagara constraints are separately verified by the isolated owner;
        # the shared mesh validator intentionally remains Engine-only.
        if constraint in ('NiagaraSystem','NiagaraComponent'):constraint=''
        fields.append('{'+','.join((json.dumps(p['name']),json.dumps(p['type']),str(p['offset']),str(p['element_size']),str(p['flags'])+'ULL',p['vtable_rva']+'ULL',json.dumps(p.get('struct_name','')),json.dumps(p.get('inner_type','')),str(p.get('inner_element_size',0)),json.dumps(p.get('inner_struct_name','')),p.get('bool_encoding','0')+'U',json.dumps(constraint)))+'}')
    out.append(f'inline const MeshField fx_fields_{i}[]={{'+',\n'.join(fields)+'};')
out.append('inline const MeshFunction fx_functions[]={')
for i,row in enumerate(rows):
    owner,name=row['path'].split('.')[-1].split(':');f=row['function']
    out.append('{'+','.join((json.dumps(owner),json.dumps(name),str(f['flags']),str(f['params_size']),str(row['allocation_extent']),str(f['return_offset']),f['entry_rva'],f'fx_fields_{i}',str(len(row['parameters']))))+'},')
out+=['};','}']
(ROOT/'native/runtime_cinematic_effects_profile.h').write_text('\n'.join(out)+'\n')
