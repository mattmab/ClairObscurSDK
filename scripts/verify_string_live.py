"""Bounded source-only probe; never opens media or invokes story playback."""
import json
from datetime import datetime, timezone
from pathlib import Path
from expedition33.catalog import capture_matching
from expedition33._scope import SessionScope
from expedition33.values import read_values


def run(session):
    root = Path(__file__).resolve().parents[1]
    report = {'utc': datetime.now(timezone.utc).isoformat(), 'pid': session.pid,
              'playback_attempted': False, 'calls': []}
    scope = SessionScope(session)
    def one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one observed identity')
        return rows[0]
    try:
        if not session.supports_string_values:
            raise RuntimeError('String candidate capability required')
        catalog = capture_matching(session.pid, names=('FileMediaSource', 'GameplayStatics',
            'Default__GameplayStatics', 'SpawnObject', 'SetFilePath', '/Engine/Transient'))
        cls = one(o for o in catalog.objects if o.name == 'FileMediaSource' and o.class_name == 'Class')
        default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
        outer = one(o for o in catalog.objects if o.name == '/Engine/Transient' and o.class_name == 'Package')
        spawn = one(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == default.class_index)
        setter = one(o for o in catalog.objects if o.name == 'SetFilePath' and o.outer_index == cls.index)
        with scope.invocation_planner(selected_results=True, catalog=catalog) as planner:
            result = planner.prepare(default, spawn, ObjectClass=cls, Outer=outer).invoke(refresh_from_result=True)
            source = result.return_value
            report['source'] = {'index': source.index, 'serial': source.serial}
            for path in ('./Movies/SDK_String_Probe.mp4', '', './Movies/SDK_\U0001f3ac_Probe.mp4') * 3:
                with planner.prepare(source, setter, Path=path).invoke():
                    values = read_values(planner._catalog, source)
                    stored = values.values.get((cls.index, 'FilePath'))
                    report['calls'].append({'input': path, 'stored': stored,
                        'errors': {str(k): str(v) for k, v in values.errors.items()}})
                    if stored != path:
                        raise RuntimeError('Stored path did not match copied input')
            report['configured'] = True
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        try:
            scope.close()
            report['scope_closed'] = True
        finally:
            (root / 'evidence/string-live-validation.json').write_text(
                json.dumps(report, indent=2), encoding='utf-8')
    return report


if 'live_session' in globals():
    print(run(live_session))
