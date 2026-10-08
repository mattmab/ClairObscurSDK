"""Persistent native hook, explicit removal, controller death, and reopen."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import expedition33
from expedition33._session import SessionTransport

baseline = expedition33.reflect_function('Actor.IsActorBeingDestroyed')
before = expedition33.stored_bools('Default__Actor')
results = []
for run in range(3):
    with SessionTransport() as session:
        obj = next(row for row in session.objects if row['class_name'] == 'Actor')
        session.command('enable')
        session.command('enable')
        assert session.command('ping')['result'] == 1
        # The native invocation and copied events below prove persistence across
        # separate commands without relying on the read-only metadata query,
        # which deliberately rejects function entries outside the game image.
        for _ in range(2):
            assert session.command('invoke')['result'] == 0
        events = session.command('drain')
        assert events['dropped'] == 0 and len(events['events']) == 2
        for event in events['events']:
            assert int(event['object_address'], 16) == int(obj['address'], 16)
            assert event['thread'] == session.start['game_thread_id'] and event['result'] == 0
        assert session.command('drain')['events'] == []
        session.command('disable')
        session.command('disable')
        assert session.command('invoke')['result'] == 0
        assert session.command('drain')['events'] == []
        assert expedition33.reflect_function('Actor.IsActorBeingDestroyed') == baseline
        session.command('enable')
        assert session.command('invoke')['result'] == 0
        assert len(session.command('drain')['events']) == 1
        results.append({'run': run, 'pid': session.start['pid'], 'events': events['events']})
    assert expedition33.reflect_function('Actor.IsActorBeingDestroyed') == baseline

crashed = SessionTransport()
crashed.command('enable')
crashed._abort()  # Deliberately kill only our own controller, leaving cleanup to the game-owned watcher.
deadline = time.monotonic() + 10
while True:
    try:
        restored = expedition33.reflect_function('Actor.IsActorBeingDestroyed') == baseline
    except expedition33.RuntimeQueryError:
        restored = False
    if restored:
        break
    assert time.monotonic() < deadline, 'Disconnect did not restore the original function entry'
    time.sleep(0.05)
with SessionTransport() as reopened:
    assert reopened.command('ping')['result'] == 0
    assert reopened.command('invoke')['result'] == 0
assert expedition33.stored_bools('Default__Actor') == before
output = {'timestamp': datetime.now(timezone.utc).isoformat(), 'runs': results,
          'normal_close_restored': True, 'controller_exit_restored': True,
          'reopen_after_disconnect': True, 'properties_unchanged': True}
(Path(__file__).resolve().parents[1] / 'evidence/python-live-session.json').write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output))
