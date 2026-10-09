"""Observe game-side menu cleanup after terminating only our test controller."""
import json
from pathlib import Path
import runpy
import subprocess
import sys
import time
import argparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from expedition33 import sdk, _menu_wire


def main(*,button_references=False):
    args=[sys.executable, '-B', str(ROOT/'scripts/verify_live_native_menu.py'), '--disconnect-worker']
    stem='button-reference-disconnect' if button_references else 'native-menu-disconnect'
    if button_references: args.append('--button-references')
    worker = subprocess.run(args)
    assert worker.returncode == 23, worker.returncode
    progress = json.loads((ROOT/f'evidence/{stem}-progress.json').read_text())
    specimen = json.loads((ROOT/f'evidence/{stem}-live.json').read_text())
    assert progress['disconnect_requested'] and progress['operations'][-1]['operation']=='focus'
    assert not progress['during']['users'][0]['matches_game_viewport']
    if button_references: assert progress['operations'][-1]['button_reference_state']==2
    observe = runpy.run_path(str(ROOT/'scripts/inspect_slate_focus_dispatch.py'))['observe']
    holders = runpy.run_path(str(ROOT/'scripts/verify_live_widget_lifecycle.py'))['holders']
    baseline = {key:tuple(value) for key,value in specimen['baseline_holders'].items()}
    result = dict(passed=False, controller_pid=progress['controller_pid'], python_cleanup_ran=False)
    result['runtime_version']=15 if button_references else 14
    for attempt in range(10):
        state, owned = observe(), holders()
        result.update(attempt=attempt+1, after=state, holders=owned)
        if state['users'][0]['matches_game_viewport'] and owned==baseline: break
        time.sleep(.25)  # Read-only observations; never replay engine operations.
    assert state['game_viewport']==progress['before']['game_viewport']
    assert state['users'][0]['matches_game_viewport'] and owned==baseline
    # A fresh owner of the same runtime must not inherit the old menu or leases.
    with sdk.Session(menu_ownership=True,button_references=button_references) as session:
        sent = _menu_wire.request('status', 987)
        response = session._transport.command('menu', sent)
        reply = _menu_wire.decode(sent,response['menu_packet'])
        assert reply.error==0 and not reply.active
        if button_references:
            assert session._transport.button_reference_protocol==1
            assert response.get('button_reference_state')==0
            result['new_session_button_reference_state']=response['button_reference_state']
        result['new_session_empty'] = True
    result['passed'] = True
    (ROOT/f'evidence/{stem}-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Native controller-death cleanup restored viewport and exact holders; fresh v{result["runtime_version"]} session is empty.')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--button-references',action='store_true')
    main(button_references=parser.parse_args().button_references)
