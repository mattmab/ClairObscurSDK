"""Live candidate measurements; call with a caller-owned menu in persistent Python.

Keep the menu variable even if open fails, so its ownership can be inspected and
cleaned up. This script never retries or opens a second controller.
"""
import json
from pathlib import Path
import runpy
import time

ROOT = Path(__file__).resolve().parents[1]


def observe():
    focus = runpy.run_path(str(ROOT / 'scripts/inspect_slate_focus_dispatch.py'))['observe']()
    holders = runpy.run_path(str(ROOT / 'scripts/verify_live_widget_lifecycle.py'))['holders']()
    return {'focus': focus, 'holders': holders}


def measure_open(menu):
    before = observe()
    assert before['focus']['users'][0]['matches_game_viewport']
    record = {'before': before, 'completed': False}
    started = time.perf_counter()
    try:
        menu.open()
        record['completed'] = True
    except BaseException as error:
        record['error'] = repr(error)
        raise
    finally:
        record.update(seconds=time.perf_counter() - started,
                      state=menu.panel.state, uncertain=menu.panel.uncertain)
        (ROOT / 'evidence/native-management-cached-open.json').write_text(
            json.dumps(record, indent=2), encoding='utf-8')
    return {'open_seconds': record['seconds'], 'state': record['state']}


def verify_closed(menu):
    assert menu.panel.state == 'closed' and not menu.panel.uncertain
    before = json.loads((ROOT / 'evidence/native-management-cached-open.json').read_text())['before']
    after = observe()
    (ROOT / 'evidence/native-management-cached-after.json').write_text(
        json.dumps(after, indent=2), encoding='utf-8')
    assert after['focus']['pid'] == before['focus']['pid']
    assert after['focus']['game_viewport'] == before['focus']['game_viewport']
    assert after['focus']['users'][0]['matches_game_viewport']
    assert json.loads(json.dumps(after['holders'])) == before['holders']
    return 'Cached menu closed; exact viewport and retained-holder baseline restored'
