"""Kill only this test's controller with an action bound; verify native recovery."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from expedition33 import sdk, _menu_wire, _button_action_wire as wire

STEM = 'button-action-disconnect'


def save(name, value):
    (ROOT / 'evidence' / f'{STEM}-{name}.json').write_text(
        json.dumps(value, indent=2), encoding='utf-8')


def specimen(session, *, disconnect):
    name = 'worker' if disconnect else 'recovery'
    observe = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']
    before = observe()
    assert before['pid'] == session.pid and before['users'][0]['matches_game_viewport']
    evidence = dict(passed=False, before=before, session=session._transport.button_action_session)

    class Lifecycle:
        menu = None

        def open(self, scope, widget, button, player):
            self.menu = scope.prepare_menu(widget, button, player)
            assert self.menu.attach() and self.menu.focus()
            self.action = self.menu.bind_action(lambda event: None)
            assert self.action._poll() == 0
            evidence.update(owner=self.menu._owner, child_lease=self.menu._leases[1]._token,
                            registration=self.action._registration, during=observe(), bound=True)
            assert not evidence['during']['users'][0]['matches_game_viewport']
            save(name, evidence)

        def close(self):
            if self.menu is not None:
                assert self.menu.close()
                assert self.action._state == 'closed'
                assert self.menu._button_reference_state == 0
                evidence.update(menu_closed=True, reference_empty=True)
                save(name, evidence)

    lifecycle = Lifecycle()

    def displayed(*_):
        if disconnect:
            controller = session._transport._process
            evidence.update(controller_pid=controller.pid, disconnect_requested=True)
            save(name, evidence)
            # Bypass all Python finally blocks. The game's owner watcher must
            # revoke the action, restore its delegate, and tear down the menu.
            controller.kill()
            evidence['controller_exit_code'] = controller.wait(timeout=10)
            save(name, evidence)
            os._exit(23)
        assert lifecycle.action.remove()
        lifecycle.action = lifecycle.menu.bind_action(lambda event: None)
        assert lifecycle.action._registration > evidence['registration']
        assert lifecycle.action._poll() == 0
        evidence['rebound_registration'] = lifecycle.action._registration
        save(name, evidence)
        return dict(empty_drain=True, rebind=True)

    result = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_visible.py'))['run'](
        session, activatable=True, button_enabled=True, native_lifecycle=lifecycle,
        on_display=displayed, hold_seconds=0, evidence_name=f'{STEM}-{name}-live.json')
    assert result['passed'] and result['holder_baseline_restored']
    after = observe()
    assert after['game_viewport'] == before['game_viewport']
    assert after['users'][0]['matches_game_viewport']
    evidence.update(passed=True, after=after, holder_baseline_restored=True)
    save(name, evidence)
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        with sdk.Session(button_actions=True) as session:
            specimen(session, disconnect=True)
        raise AssertionError('Worker unexpectedly reached normal cleanup')

    result = dict(passed=False, phase='worker', python_cleanup_ran=False)
    save('result', result)
    try:
        worker = subprocess.run([sys.executable, '-B', __file__, '--worker'])
        assert worker.returncode == 23, worker.returncode
        previous = json.loads((ROOT / 'evidence' / f'{STEM}-worker.json').read_text())
        live = json.loads((ROOT / 'evidence' / f'{STEM}-worker-live.json').read_text())
        assert previous['bound'] and previous['disconnect_requested']
        assert 'menu_closed' not in previous and 'native_closed' not in live
        observe = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']
        holders = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_lifecycle.py'))['holders']
        baseline = {key: tuple(value) for key, value in live['baseline_holders'].items()}
        result.update(phase='observe_cleanup', controller_pid=previous['controller_pid'])
        save('result', result)
        for attempt in range(10):
            state, owned = observe(), holders()
            result.update(attempt=attempt + 1, after=state, holders=owned)
            save('result', result)
            if state['users'][0]['matches_game_viewport'] and owned == baseline:
                break
            time.sleep(.25)
        assert state['game_viewport'] == previous['before']['game_viewport']
        assert state['users'][0]['matches_game_viewport'] and owned == baseline
        result['native_cleanup_restored_baseline'] = True
        with sdk.Session(button_actions=True) as session:
            nonce = session._transport.button_action_session
            assert nonce != previous['session']
            sent = _menu_wire.request('status', previous['owner'])
            response = session._transport.command('menu', sent)
            menu = _menu_wire.decode(sent, response['menu_packet'])
            assert not menu.error and not menu.active and response['button_reference_state'] == 0
            sent = wire.request('status', previous['owner'], previous['child_lease'])
            response = session._transport.command('button-action', sent)
            stale = wire.decode(sent, response['button_action_packet'], session=nonce)
            assert stale.error == 911 and stale.state == 0 and not stale.events
            result.update(phase='recovery_specimen', stale_owner_status=asdict(stale), new_session=nonce)
            save('result', result)
            fresh = specimen(session, disconnect=False)
            assert fresh['registration'] > previous['registration']
            result['fresh_binding_and_cleanup'] = fresh['passed']
        result.update(passed=True, phase='complete', normal_recovery_close=True)
        save('result', result)
        print('Bound-action controller death, native cleanup, stale-owner rejection and fresh binding passed.')
    except BaseException as error:
        result['error'] = repr(error)
        save('result', result)
        raise


if __name__ == '__main__':
    main()
