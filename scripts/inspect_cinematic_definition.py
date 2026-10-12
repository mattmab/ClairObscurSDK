"""Read current cinematic definition schemas; never execute story actions."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from expedition33.catalog import capture_matching, capture
from expedition33.reflection import describe
from expedition33._reader import ReadBatch
with ReadBatch(9616):
    c = capture_matching(9616, names=('BP_GameAction_CinematicWithLightingScenario_C',
        'BP_GameAction_Cinematic_C', 'FileMediaSource', 'S_TriggerCinematicVariables'))
    selected = c.objects
    c = capture()
    result = []
    for o in selected:
        if o.class_name not in ('Class','BlueprintGeneratedClass','UserDefinedStruct'): continue
        d = describe(c, (o,))[o.index]
        result.append(dict(path=c.path_name(o),properties=[dict(p) for p in d.properties]))
    Path('evidence/cinematic-definition-schema.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result,indent=2))
