"""Exercise a failed import and explicit file recovery using a borrowed live Session."""
import json
from pathlib import Path
import runpy

from expedition33.mod_archive import build_bytes
from expedition33.mod_install import inspect_transaction, recover_transaction
from expedition33.mods import ModLoader, ModError

ROOT = Path(__file__).resolve().parents[1]


def verify(session):
    # First establish a valid live-installed specimen in its own research root.
    installed = runpy.run_path(str(ROOT / 'scripts/verify_live_staged_install.py'))['verify'](session)
    destination = Path(installed['evidence'])
    source = destination / 'source'
    with (source / 'mod.py').open('a', encoding='utf-8') as stream:
        stream.write('\nraise RuntimeError("intentional recovery specimen import failure")\n')
    archive, candidate = build_bytes(source)
    (destination / 'staging/Probe.zip').write_bytes(archive)
    baseline = sum(h.active for h in session._hooks)
    with ModLoader(destination / 'mods', session=session) as loader:
        loader.load('Probe'); loader.enable('Probe')
        old_scope = loader._loaded['Probe'][2]
        try:
            loader.install_staged('Probe', expected_sha256=candidate.sha256)
        except ModError as error:
            assert 'intentional recovery specimen import failure' in str(error), error
            failure = str(error)
        else:
            raise AssertionError('Failed candidate unexpectedly activated')
        assert old_scope._closed and not loader.status() and not loader.actions.actions
        assert sum(h.active for h in session._hooks) == baseline
    transactions = destination / 'mods/.transactions'
    failed = [inspect_transaction(destination / 'mods', p.name) for p in transactions.iterdir()]
    failed = [state for state in failed if state['phase'] == 'activating']
    assert len(failed) == 1, failed
    before = failed[0]
    (destination / 'recovery-before.json').write_text(json.dumps(before, indent=2))
    transaction_id = Path(before['journal']).parent.name
    # The fixture loader has closed and all its hooks are gone. File recovery
    # acquires its now-unowned root; the main management root remains untouched.
    restored = recover_transaction(destination / 'mods', transaction_id,
                                   expected_journal_sha256=before['journal_sha256'])
    assert restored['phase'] == 'rolled_back'
    with ModLoader(destination / 'mods', session=session) as fresh:
        fresh.load('Probe'); fresh.enable('Probe')
        reply = fresh.actions.dispatch({'op': 'action', 'name': 'example.observe_actor'})
        assert reply['success'] and reply['result'] == {
            'label': 'Archive version 2', 'is_actor_being_destroyed': False}, reply
    assert sum(h.active for h in session._hooks) == baseline
    result = dict(passed=True, failure=failure, recovered=restored, live_getter=reply,
                  hooks_before=baseline, hooks_after=sum(h.active for h in session._hooks),
                  evidence=str(destination))
    (destination / 'recovery-result.json').write_text(json.dumps(result, indent=2))
    return result
