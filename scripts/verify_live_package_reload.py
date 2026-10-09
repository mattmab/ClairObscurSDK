"""Verify helper-only replacement on a borrowed live Session, leaving raw evidence."""
import hashlib
import json
from pathlib import Path
import sys
import uuid
from expedition33.mods import ModLoader
from expedition33.mod_archive import build_bytes

ROOT = Path(__file__).resolve().parents[1]


def verify(session):
    destination = ROOT / 'evidence' / ('package-reload-' + uuid.uuid4().hex)
    folder = destination / 'mods/Probe'
    folder.mkdir(parents=True)
    source = (ROOT / 'mods/ManagementExample/mod.py').read_text(encoding='utf-8')
    source = 'from .label import LABEL\n' + source.replace("self.label = 'Actor observation'", 'self.label = LABEL')
    (folder / 'mod.py').write_text(source, encoding='utf-8')
    digest = hashlib.sha256((folder / 'mod.py').read_bytes()).hexdigest()
    def version(number):
        (folder / 'label.py').write_text('LABEL = "Helper version ' + str(number) + '"\n')
        archive, candidate = build_bytes(folder)
        (destination / ('version-' + str(number) + '.zip')).write_bytes(archive)
        return candidate.summary()['python_package_sha256']
    first_digest = version(1)
    baseline = sum(h.active for h in session._hooks)
    records = []
    loader = ModLoader(destination / 'mods', session=session)
    def request(payload, success=True):
        reply = loader.actions.dispatch(payload)
        records.append(dict(request=payload, response=reply))
        (destination / 'requests.json').write_text(json.dumps(records, indent=2))
        assert reply['success'] is success, reply
        return reply.get('result')
    try:
        loader.load('Probe'); loader.enable('Probe')
        old_key = loader._loaded['Probe'][0]
        assert request({'op':'action', 'name':'example.observe_actor'}) == {
            'label':'Helper version 1', 'is_actor_being_destroyed':False}
        next_digest = version(2)
        payload = dict(op='reload_changed_mod', mod='Probe', expected_sha256=digest, allow_mutation=True)
        request(payload, False)
        request(dict(payload, expected_package_sha256=first_digest), False)
        assert request(dict(payload, expected_package_sha256=next_digest))['changed']
        assert not any(n == old_key or n.startswith(old_key + '.') for n in sys.modules)
        assert sum(h.active for h in session._hooks) == baseline + 1
        assert request({'op':'action', 'name':'example.observe_actor'}) == {
            'label':'Helper version 2', 'is_actor_being_destroyed':False}
        assert not request(dict(payload, expected_package_sha256=next_digest))['changed']
    finally:
        loader.close()
    assert sum(h.active for h in session._hooks) == baseline
    result = dict(passed=True, hooks_before=baseline, hooks_after=sum(h.active for h in session._hooks),
                  evidence=str(destination), entry_sha256=digest,
                  first_package_sha256=first_digest, second_package_sha256=next_digest)
    (destination / 'result.json').write_text(json.dumps(result, indent=2))
    return result
