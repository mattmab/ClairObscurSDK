"""Inspect fresh base CommonVideoPlayer ownership without opening media."""
import json
from pathlib import Path
from expedition33.catalog import capture_matching, capture_selected
from expedition33._scope import SessionScope
from expedition33.values import read_object_reference


def run(session):
    report = {'pid': session.pid, 'playback_attempted': False}
    scope = SessionScope(session)
    def one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise ValueError('Expected one observed identity')
        return rows[0]
    try:
        catalog = capture_matching(session.pid, names=('CommonVideoPlayer', 'GameplayStatics',
            'Default__GameplayStatics', 'SpawnObject'))
        cls = one(o for o in catalog.objects if o.name == 'CommonVideoPlayer' and o.class_name == 'Class')
        default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
        spawn = one(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == default.class_index)
        panel = session._native_menu_service.menu.panel
        catalog = catalog.with_observations(capture_selected(session.pid,
            ((panel.tree.index, panel.tree.serial, panel.tree.address),)))
        with scope.invocation_planner(selected_results=True, catalog=catalog) as planner:
            result = planner.prepare(default, spawn, ObjectClass=cls, Outer=panel.tree).invoke(refresh_from_result=True)
            widget = result.return_value
            report['widget'] = {'index': widget.index, 'serial': widget.serial}
            catalog = planner._catalog
            for name in ('MediaPlayer', 'MediaTexture', 'SoundComponent', 'VideoMaterial', 'Video'):
                ref, catalog = read_object_reference(catalog, widget, cls, name)
                report[name] = None if ref is None else {'index': ref.index, 'serial': ref.serial,
                    'path': catalog.path_name(ref), 'outer_index': ref.outer_index}
    except BaseException as error:
        report['error'] = repr(error)
        raise
    finally:
        try:
            scope.close()
            report['scope_closed'] = True
        finally:
            Path('evidence/media-construction-live.json').write_text(json.dumps(report, indent=2), encoding='utf8')
    print(report)


if 'live_session' in globals():
    run(live_session)
