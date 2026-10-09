"""Validate archive replacement on a borrowed game Session; retain all evidence."""
import json
from pathlib import Path
import uuid
from expedition33.mods import ModLoader
from expedition33.mod_archive import build_bytes
from expedition33.mod_install import inspect_transaction

ROOT = Path(__file__).resolve().parents[1]


def verify(session):
    destination = ROOT / 'evidence' / ('staged-live-' + uuid.uuid4().hex)
    installed = destination / 'mods/Probe'
    staged = destination / 'staging'
    source = destination / 'source'
    for path in (installed, staged, source): path.mkdir(parents=True)
    entry = (ROOT / 'mods/ManagementExample/mod.py').read_text(encoding='utf-8')
    entry = 'from .label import read_label\n' + entry.replace("self.label = 'Actor observation'", 'self.label = read_label()')
    helper = 'import json\nfrom pathlib import Path\ndef read_label():\n return json.loads(Path(__file__).with_name("data.json").read_text())["label"]\n'
    for folder, version in ((installed, 1), (source, 2)):
        (folder / 'mod.py').write_text(entry, encoding='utf-8')
        (folder / 'label.py').write_text(helper)
        (folder / 'data.json').write_text(json.dumps({'label':'Archive version ' + str(version)}))
    archive, candidate = build_bytes(source)
    (staged / 'Probe.zip').write_bytes(archive)
    records = []
    baseline = sum(h.active for h in session._hooks)
    loader = ModLoader(destination / 'mods', session=session)
    def request(payload, success=True):
        reply = loader.actions.dispatch(payload)
        records.append(dict(request=payload, response=reply))
        (destination / 'requests.json').write_text(json.dumps(records, indent=2))
        assert reply['success'] is success, reply
        return reply.get('result')
    try:
        loader.load('Probe'); loader.enable('Probe')
        assert request({'op':'action', 'name':'example.observe_actor'}) == {
            'label':'Archive version 1', 'is_actor_being_destroyed':False}
        old_scope = loader._loaded['Probe'][2]
        payload = dict(op='mod_install_staged', mod='Probe', expected_sha256=candidate.sha256)
        request(payload, False)
        outcome = request(dict(payload, allow_mutation=True))
        assert outcome['phase'] == 'committed' and old_scope._closed
        assert json.loads((Path(outcome['backup']) / 'data.json').read_text())['label'] == 'Archive version 1'
        assert request({'op':'action', 'name':'example.observe_actor'}) == {
            'label':'Archive version 2', 'is_actor_being_destroyed':False}
        assert sum(h.active for h in session._hooks) == baseline + 1
    finally:
        loader.close()
    assert sum(h.active for h in session._hooks) == baseline
    with ModLoader(destination / 'mods', session=session) as fresh:
        fresh.load('Probe'); fresh.enable('Probe')
        reply = fresh.actions.dispatch({'op':'action', 'name':'example.observe_actor'})
        records.append(dict(fresh_loader_reply=reply))
        assert reply['success'] and reply['result'] == {
            'label':'Archive version 2', 'is_actor_being_destroyed':False}
    assert sum(h.active for h in session._hooks) == baseline
    journal = inspect_transaction(destination / 'mods', Path(outcome['journal']).parent.name)
    result = dict(passed=True, archive_sha256=candidate.sha256, hooks_before=baseline,
                  hooks_after=sum(h.active for h in session._hooks), journal=journal, evidence=str(destination))
    (destination / 'requests.json').write_text(json.dumps(records, indent=2))
    (destination / 'result.json').write_text(json.dumps(result, indent=2))
    return result
