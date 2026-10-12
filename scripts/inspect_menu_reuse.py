"""Read-only engine getter proof for detached menu ownership; existing session only."""
import json
from pathlib import Path
import time

from expedition33._reader import ReadBatch
from expedition33.catalog import capture_matching


def inspect(management):
    panel = management.native.menu.panel
    if panel.state != 'built' or panel.uncertain or panel.menu is not None:
        raise ValueError('Expected a known detached menu')
    report = {'widgets': [], 'completed': False}
    with ReadBatch(panel.scope.pid):
        observed = capture_matching(panel.scope.pid, names=('GetOwningPlayerPawn',))
        catalog = panel._planner._catalog.with_observations(observed)
        owner = catalog.find_class('UserWidget').index
        functions = [o for o in catalog.objects if o.outer_index == owner and o.name == 'GetOwningPlayerPawn']
        if len(functions) != 1:
            raise ValueError('Expected one reflected UserWidget.GetOwningPlayerPawn')
        with panel.scope.invocation_planner(catalog=catalog, selected_results=True) as planner:
            started = time.perf_counter()
            for widget in (panel.widget, *panel.button_art):
                with planner.prepare(widget, functions[0]).invoke() as result:
                    pawn = result.return_value
                    report['widgets'].append({
                        'index': widget.index,
                        'outer_chain': [(o.index, o.serial, o.name, o.class_name)
                                        for o in catalog.outer_chain(widget)],
                        'owning_pawn': None if pawn is None else (pawn.index, pawn.serial, pawn.address),
                        'controller': (panel.player.index, panel.player.serial, panel.player.address),
                    })
            report['getter_seconds'] = time.perf_counter() - started
    report['completed'] = True
    path = Path(__file__).resolve().parents[1] / 'evidence/menu-reuse-ownership.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('Detached ownership proof:', report['getter_seconds'], 'seconds;', len(report['widgets']), 'widgets')
