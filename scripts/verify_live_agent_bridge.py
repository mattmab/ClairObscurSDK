"""Validate the ported agent protocol against an already-running SDK controller.

Load ManagementExample metadata first through the console. This verifier enables
and disables that example through the original mutation-gated request protocol.
It never retries a mutation or replaces the controller.
"""
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
send = runpy.run_path(str(ROOT / 'scripts/e33_introspect.py'))['send']
records = []


def request(payload, *, succeeds=True):
    reply = send(payload, timeout=30)
    records.append({'request': payload, 'response': reply})
    (ROOT / 'evidence/agent-bridge-live.json').write_text(json.dumps(records, indent=2))
    assert reply['ok'], reply
    assert reply['result']['success'] is succeeds, reply
    return reply['result'].get('result')


status = request({'op': 'dev_status'})
assert not status['raw_exec_supported']
mods = request({'op': 'mod_list'})
assert any(m['name'] == 'ManagementExample' and not m['enabled'] for m in mods)
request({'op': 'mod_enable', 'mod': 'ManagementExample'}, succeeds=False)
request({'op': 'mod_enable', 'mod': 'ManagementExample', 'allow_mutation': True})
for alias in ('action', 'call_debug_action', 'run_test_action'):
    result = request({'op': alias, 'name': 'example.observe_actor'})
    assert result['is_actor_being_destroyed'] is False
request({'op': 'action', 'name': 'example.observe_actor', 'args': {'unexpected': 1}}, succeeds=False)
request({'op': 'mod_disable', 'mod': 'ManagementExample', 'allow_mutation': True})
request({'op': 'action', 'name': 'example.observe_actor'}, succeeds=False)
assert not any(a['name'] == 'example.observe_actor' for a in request({'op': 'dev_status'})['actions'])
request({'op': 'logs', 'contains': 'Introspection', 'limit': 3})
request({'op': 'mod_enable', 'mod': 'ManagementExample', 'allow_mutation': True})
assert request({'op': 'action', 'name': 'example.observe_actor'})['is_actor_being_destroyed'] is False
request({'op': 'mod_disable', 'mod': 'ManagementExample', 'allow_mutation': True})
print('Live agent protocol, game-thread getter, aliases and lifecycle passed')
