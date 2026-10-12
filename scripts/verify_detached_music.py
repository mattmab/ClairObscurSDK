"""Create/release a detached music UObject; never replace the game's system."""
import json
from datetime import datetime, timezone
from pathlib import Path
from expedition33._scope import SessionScope
from expedition33.catalog import capture
from expedition33.values import read_values, read_object_reference

def run(mod):
    scope = SessionScope(mod.session)
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'playback_attempted': False,
              'game_music_replaced': False}
    one = lambda values: tuple(values)
    try:
        c = capture()
        if c.pid != scope.pid: raise ValueError('Music catalog session mismatch')
        def unique(values):
            values = one(values)
            if len(values) != 1: raise ValueError('Ambiguous music identity')
            return values[0]
        cls = unique(o for o in c.objects if o.name == 'BP_InteractiveMusicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
        gi = unique(o for o in c.objects if o.class_name == 'BP_jRPG_GI_Custom_C' and not o.name.startswith('Default__'))
        gi_cls = c.by_index[gi.class_index]
        original, c = read_object_reference(c, gi, gi_cls, 'InteractiveMusicSystem')
        report['original'] = repr(original)
        planner = scope.invocation_planner(catalog=c)
        default = unique(o for o in c.objects if o.name == 'Default__GameplayStatics')
        owner = unique(o for o in c.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
        fn = unique(o for o in c.objects if o.name == 'SpawnObject' and o.outer_index == owner.index)
        result = planner.prepare(default, fn, ObjectClass=cls, Outer=gi).invoke(refresh_from_result=True)
        obj = result.return_value
        report['detached'] = repr(obj)
        if obj is None or obj.class_index != cls.index or obj.outer_index != gi.index:
            raise RuntimeError('Detached music ownership mismatch')
        values = read_values(planner._catalog, obj)
        report['values'] = {str(k):repr(v) for k,v in values.values.items()}
        report['errors'] = {str(k):str(v) for k,v in values.errors.items()}
        current, _ = read_object_reference(planner._catalog, gi, gi_cls, 'InteractiveMusicSystem')
        report['original_unchanged'] = current == original
    except Exception as error:
        report['error'] = repr(error)
    finally:
        scope.close()
    root = Path(__file__).resolve().parents[1]
    (root/'evidence/sequence-detached-music.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    return {k:v for k,v in report.items() if k not in ('values','errors')}
