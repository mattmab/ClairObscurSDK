"""Bounded live teardown timing using a caller-owned two-control panel.

Keep panel alive across failures. Call open_panel(panel), inspect it, then
close_panel(panel) in the persistent console. No retry or second controller.
"""
import json
from pathlib import Path
import runpy
import time

ROOT = Path(__file__).resolve().parents[1]


def observe():
    return runpy.run_path(str(ROOT / 'scripts/benchmark_native_management.py'))['observe']()


def open_panel(panel):
    before = observe()
    assert before['focus']['users'][0]['matches_game_viewport']
    (ROOT / 'evidence/cached-cleanup-before.json').write_text(json.dumps(before, indent=2))
    panel.build()
    panel.set_text(panel.title, 'SDK cleanup validation')
    panel.set_text(panel.detail, 'Two retained controls; teardown uses one fresh planning observation.')
    for index, label in enumerate(panel.labels):
        panel.set_text(label, 'Cleanup specimen ' + str(index + 1))
    panel.open()
    assert panel.state == 'open' and not panel.uncertain
    return 'Two-control cleanup specimen open'


def close_panel(panel):
    started = time.perf_counter()
    assert panel.close()
    seconds = time.perf_counter() - started
    assert panel.state == 'closed' and not panel.uncertain
    after = observe()
    before = json.loads((ROOT / 'evidence/cached-cleanup-before.json').read_text())
    record = dict(after=after, seconds=seconds, state=panel.state,
                  uncertain=panel.uncertain, remaining_children=len(panel.children))
    (ROOT / 'evidence/cached-cleanup-after.json').write_text(json.dumps(record, indent=2))
    assert after['focus']['pid'] == before['focus']['pid']
    assert after['focus']['game_viewport'] == before['focus']['game_viewport']
    assert after['focus']['users'][0]['matches_game_viewport']
    assert json.loads(json.dumps(after['holders'])) == before['holders']
    return {'cleanup_seconds': seconds, 'exact_baseline_restored': True}
