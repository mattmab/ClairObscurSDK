"""Observe game-side menu cleanup after terminating only our test controller."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33 import sdk, _menu_wire


def main():
    worker = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/verify_live_native_menu.py'), '--disconnect-worker'])
    assert worker.returncode == 23, worker.returncode
    progress = json.loads((ROOT/'evidence/native-menu-disconnect-progress.json').read_text())
    specimen = json.loads((ROOT/'evidence/native-menu-disconnect-live.json').read_text())
    assert progress['disconnect_requested'] and progress['operations'][-1]['operation']=='focus'
    assert not progress['during']['users'][0]['matches_game_viewport']
    observe = runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    holders = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))['holders']
    baseline = {key:tuple(value) for key,value in specimen['baseline_holders'].items()}
    result = dict(passed=False, controller_pid=progress['controller_pid'], python_cleanup_ran=False)
    for attempt in range(10):
        state, owned = observe(), holders()
        result.update(attempt=attempt+1, after=state, holders=owned)
        if state['users'][0]['matches_game_viewport'] and owned==baseline: break
        time.sleep(.25)  # Read-only observations; never replay engine operations.
    assert state['game_viewport']==progress['before']['game_viewport']
    assert state['users'][0]['matches_game_viewport'] and owned==baseline
    # A fresh v14 owner must not inherit the old menu or leases.
    with sdk.Session(menu_ownership=True) as session:
        sent = _menu_wire.request('status', 987)
        response = session._transport.command('menu', sent)
        reply = _menu_wire.decode(sent,response['menu_packet'])
        assert reply.error==0 and not reply.active
        result['new_session_empty'] = True
    result['passed'] = True
    (ROOT/'evidence/native-menu-disconnect-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('Native controller-death cleanup restored the viewport and exact holders; fresh v14 session is empty.')


if __name__=='__main__': main()
