"""Run verify(shared_session) from persistent console Python; no new transport.

Creates two versions of a research mod under evidence, leaving both sources and
request results for inspection. Existing installed mods are not edited.
"""
import hashlib
import json
from pathlib import Path
import uuid

from expedition33.mods import ModLoader

ROOT = Path(__file__).resolve().parents[1]


def verify(session):
    destination = ROOT / 'evidence' / ('mod-reload-' + uuid.uuid4().hex)
    folder = destination / 'mods' / 'Probe'
    folder.mkdir(parents=True)
    source = (ROOT / 'mods/ManagementExample/mod.py').read_text(encoding='utf-8')
    records = []
    baseline = sum(h.active for h in session._hooks)
    def write(version):
        text = source.replace("self.label = 'Actor observation'", "self.label = 'Reload version " + str(version) + "'")
        data = text.encode('utf-8')
        (destination / ('version-' + str(version) + '.py')).write_bytes(data)
        (folder / 'mod.py').write_bytes(data)
        return hashlib.sha256(data).hexdigest()
    digest1 = write(1)
    loader = ModLoader(destination / 'mods', session=session)
    def request(payload, success=True):
        reply = loader.actions.dispatch(payload)
        records.append(dict(request=payload, response=reply))
        (destination / 'requests.json').write_text(json.dumps(records, indent=2))
        assert reply['success'] is success, reply
        return reply.get('result')
    try:
        loader.load('Probe'); loader.enable('Probe')
        old_scope = loader._loaded['Probe'][2]
        first = request({'op':'action', 'name':'example.observe_actor'})
        assert first == {'label':'Reload version 1', 'is_actor_being_destroyed':False}
        digest2 = write(2)
        request({'op':'mod_reload', 'mod':'Probe', 'expected_sha256':digest2}, False)
        request({'op':'mod_reload', 'mod':'Probe', 'expected_sha256':digest1, 'allow_mutation':True}, False)
        request({'op':'mod_reload', 'mod':'Probe', 'expected_sha256':digest2, 'allow_mutation':True})
        assert old_scope._closed
        assert sum(h.active for h in session._hooks) == baseline + 1
        second = request({'op':'action', 'name':'example.observe_actor'})
        assert second == {'label':'Reload version 2', 'is_actor_being_destroyed':False}
        replacement = loader._loaded['Probe'][1]
        unchanged = request({'op':'reload_changed_mod', 'mod':'Probe',
                             'expected_sha256':digest2, 'allow_mutation':True})
        assert unchanged['changed'] is False and loader._loaded['Probe'][1] is replacement
        request({'op':'mod_disable', 'mod':'Probe', 'allow_mutation':True})
        request({'op':'action', 'name':'example.observe_actor'}, False)
    finally:
        loader.close()
    assert sum(h.active for h in session._hooks) == baseline
    result = dict(passed=True, hook_baseline=baseline, hooks_after=sum(h.active for h in session._hooks),
                  first_sha256=digest1, second_sha256=digest2, evidence=str(destination))
    (destination / 'result.json').write_text(json.dumps(result, indent=2))
    return result
