"""Representative menu timing/ownership check in an existing Python session.

Call run(my_mod.native). No new controller and no gameplay/mod-setting actions.
Timings are controller operation latency, not GPU presentation timestamps.
"""
import json
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]

def run(service, *, rounds=5, label='candidate'):
    if service.menu is None or service.menu.panel.state != 'built':
        raise ValueError('Prepare a detached menu before measuring')
    if rounds not in range(1, 11) or label not in ('candidate', 'final', 'reconnect'):
        raise ValueError('Invalid measurement bounds')
    session = service.scope._session
    panel = service.menu.panel
    baseline = len(session._leases) - len(panel.scope._leases)
    samples = []
    report = dict(pid=service.scope.pid, baseline_leases=baseline, samples=samples,
                  completed=False, boundary='paused gameplay; controller operations, not presentation timestamps')
    def measured(name, operation):
        begin = time.perf_counter()
        operation()
        samples.append(dict(operation=name, ms=(time.perf_counter() - begin) * 1000))
    try:
        for _ in range(rounds):
            measured('open', service.open)
            assert service.menu.panel is panel and panel.state == 'open'
            measured('refresh_unchanged', service.refresh)
            menu = service.menu
            first = menu.frame.controls[0]
            measured('navigate_details', lambda: menu.submit(menu.frame.revision, first.token))
            back = next(c for c in menu.frame.controls if c.label == 'Back')
            measured('navigate_back', lambda: menu.submit(menu.frame.revision, back.token))
            close = next(c for c in menu.frame.controls if c.label == 'Close')
            measured('close_button', lambda: menu.submit(menu.frame.revision, close.token))
            assert panel.state == 'built' and not menu.actions and not menu._accept_input
            assert not any(owner.active for owner in session._menus)
            assert len(service.scope._children) == 1
        measured('dispose_all_widgets', service.dispose_menu)
        assert service.menu is None and not service.scope._children
        assert len(session._leases) == baseline
        report.update(completed=True, final_leases=len(session._leases), final_child_scopes=0)
    finally:
        (ROOT / f'evidence/menu-latency-{label}.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return report
