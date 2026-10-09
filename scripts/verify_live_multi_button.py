"""Bounded v17 real-input test: blue, green, removed blue, surviving green."""
import dataclasses
import json
from pathlib import Path
import runpy
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import sdk


def run(session, *, remove_focused_control=False):
    prefix = 'multi-button-removed-focus' if remove_focused_control else 'multi-button'
    path = ROOT / f'evidence/{prefix}-progress.json'
    evidence = {'passed': False, 'phase': 'preparing', 'pid': session.pid, 'events': []}
    def save(): path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    save()
    observe = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before = observe()
    evidence['focus_before'] = before
    save()
    assert before['users'][0]['matches_game_viewport']

    class Lifecycle:
        menu = None
        def open_controls(self, scope, widget, buttons, player):
            self.menu = scope.prepare_menu(widget, buttons[0], player)
            assert self.menu.attach() and self.menu.focus()
            def record(name, event):
                evidence['events'].append({'control': name, **dataclasses.asdict(event)})
                save()
            self.blue = self.menu.bind_control(buttons[0], lambda event: record('blue', event))
            self.green = self.menu.bind_control(buttons[1], lambda event: record('green', event))
            assert self.blue._registration != self.green._registration
        def close(self):
            if self.menu is not None:
                assert self.menu.close()
                restored = observe()
                evidence['focus_after'] = restored
                evidence['focus_restored'] = (
                    restored['users'][0]['matches_game_viewport']
                    and restored['game_viewport'] == before['game_viewport'])
                save()
    lifecycle = Lifecycle()
    def wait(phase, count):
        evidence['phase'] = phase; save()
        deadline = time.monotonic() + 180
        while len(evidence['events']) < count and time.monotonic() < deadline:
            session.poll(); time.sleep(.05)
        assert len(evidence['events']) == count, 'Missing or duplicate click: ' + phase
    def interact(*_):
        wait('click_blue', 1)
        assert [e['control'] for e in evidence['events']] == ['blue']
        wait('click_green', 2)
        assert [e['control'] for e in evidence['events']] == ['blue', 'green']
        assert lifecycle.blue.remove()
        evidence['phase'] = 'click_removed_blue_then_green'; save()
        wait('click_removed_blue_then_green', 3)
        assert [e['control'] for e in evidence['events']] == ['blue', 'green', 'green']
        assert not lifecycle.blue.failures and not lifecycle.green.failures
        if remove_focused_control:
            assert lifecycle.green.remove()
            evidence['focused_callback_removed_before_close'] = True
        evidence['independent_routing'] = evidence['removed_control_no_delivery'] = True
        evidence['phase'] = 'cleaning'; save()
        return {'two_controls': True, 'selective_removal': True}
    result = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_visible.py'))['run'](
        session, activatable=True, button_enabled=True, two_buttons=True,
        native_lifecycle=lifecycle, on_display=interact, hold_seconds=0,
        evidence_name=f'{prefix}-widget-live.json')
    assert result['passed'] and result['holder_baseline_restored'] and result['second_child_removed']
    evidence['holder_baseline_restored'] = True
    save()
    assert evidence.get('focus_restored'), 'Menu closed without restoring owned control focus'
    evidence.update(passed=True, phase='complete', holder_baseline_restored=True)
    save()
    return evidence


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remove-focused-control', action='store_true')
    args = parser.parse_args()
    with sdk.Session(multi_controls=True) as session:
        run(session, remove_focused_control=args.remove_focused_control)
    print('Two native controls, independent routing, selective removal and exact cleanup passed.')
