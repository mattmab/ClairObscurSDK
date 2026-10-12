"""Generate exact build schema rows from the preserved live reflection capture."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'evidence/sequence-support-schema.json').read_text())
names=('MovieSceneSequenceLoopCount','MovieSceneSequenceTickInterval','MovieSceneSequencePlaybackSettings')
lines=['#pragma once','// Derived from evidence/sequence-support-schema.json; no stock layouts.',
       'struct SequenceSettingField { const char* name; const char* type; uint32_t offset,width; uint64_t flags,table; uint32_t boolean; const char* nested; };']
for name in names:
    row=next(r for r in rows if r['path']=='/Script/MovieScene.'+name)
    lines.append('inline constexpr SequenceSettingField fields_'+name+'[]={')
    for p in row['properties']:
        assert p['dimension']==1
        lines.append('    {"%s","%s",%d,%d,%dULL,%s,%s,"%s"},'%(p['name'],p['type'],p['offset'],p['element_size'],
            p['flags'],p['vtable_rva'],p.get('bool_encoding','0'),p.get('struct_name',p.get('enum_name',''))))
    lines.append('};')
(ROOT/'native/sequence_settings_profile.h').write_text('\n'.join(lines)+'\n',encoding='utf8')
