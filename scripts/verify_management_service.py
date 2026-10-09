"""Read-only evidence for the SDKManagement-owned native frontend.

Run capture('before', my_mod), capture('open', my_mod), and capture('after', my_mod)
in the persistent console around ordinary mods ui / mods ui close commands.
"""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]


def capture(phase, management):
    if phase not in ('before', 'open', 'after'):
        raise ValueError('Unsupported evidence phase')
    service = management.native
    state = runpy.run_path(str(ROOT / 'scripts/benchmark_native_management.py'))['observe']()
    state['service'] = service.status()
    state['child_scopes'] = len(service.scope._children)
    state['shared_registry'] = service.registry is management.registry
    state['commands'] = list(service.scope._session.console.dispatcher.command_names)
    path = ROOT / 'evidence' / ('management-service-' + phase + '.json')
    path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    assert state['shared_registry'] and 'mods' in state['commands']
    if phase == 'open':
        assert state['service']['state'] == 'open' and state['child_scopes'] == 1
    else:
        assert state['service']['state'] == 'not_created' and state['child_scopes'] == 0
        assert state['focus']['users'][0]['matches_game_viewport']
    if phase == 'after':
        before = json.loads((ROOT / 'evidence/management-service-before.json').read_text())
        assert state['focus']['pid'] == before['focus']['pid']
        assert state['focus']['game_viewport'] == before['focus']['game_viewport']
        assert json.loads(json.dumps(state['holders'])) == before['holders']
    return 'Management service ' + phase + ' verified'
