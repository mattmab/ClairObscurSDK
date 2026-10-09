"""Read-only before/after evidence for the native management renderer.

Call capture_state('before') from persistent Python before constructing the menu;
call capture_state('after') after its Close callback finishes. No SDK mutations.
"""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def capture_state(phase):
    if phase not in ('before', 'after'):
        raise ValueError('Expected before or after')
    focus = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']()
    holders = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_lifecycle.py'))['holders']()
    state = {'focus': focus, 'holders': holders}
    path = ROOT / 'evidence' / f'native-management-{phase}.json'
    path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    if phase == 'after':
        before = json.loads((ROOT / 'evidence/native-management-before.json').read_text())
        assert before['focus']['pid'] == focus['pid']
        assert before['focus']['game_viewport'] == focus['game_viewport']
        assert focus['users'][0]['matches_game_viewport']
        assert json.loads(json.dumps(holders)) == before['holders']
    else:
        assert focus['users'][0]['matches_game_viewport']
    return 'Native management ' + phase + ' state captured and verified'
