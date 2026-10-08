"""Real UFunction entry observer -> copied native events -> Python callbacks."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
import expedition33

before = expedition33.stored_bools('Default__Actor')
metadata_before = expedition33.reflect_function('Actor.IsActorBeingDestroyed')
owner_thread = threading.get_ident()
seen = []
def callback(context):
    assert threading.get_ident() == owner_thread
    seen.append(context)

first = expedition33.observe_proof(callback)
assert len(seen) == 2 and tuple(seen) == first.contexts
assert not first.callback_failures and first.entry_restored and first.module_resident
assert all(c.object.pid == before.pid and c.object.index == before.index and
           c.object.serial == before.serial and c.result is False for c in seen)
failed_calls = []
def bad(context):
    failed_calls.append(context)
    raise RuntimeError('intentional observer callback failure')
failure = expedition33.observe_proof(bad)
assert len(failed_calls) == 1 and len(failure.callback_failures) == 1
assert failure.callback_failures[0].message == 'intentional observer callback failure'
second = expedition33.observe_proof(callback)
assert len(seen) == 4 and not second.callback_failures
assert expedition33.stored_bools('Default__Actor') == before
assert expedition33.reflect_function('Actor.IsActorBeingDestroyed') == metadata_before
invocation = expedition33.invoke_proof()
assert invocation.result is False and invocation.remote_module_unloaded
output = {'timestamp': datetime.now(timezone.utc).isoformat(),
          'source': 'live Unreal UFunction entry observer, not a synthesized invocation notification',
          'first': asdict(first), 'contained_failure': asdict(failure), 'second': asdict(second),
          'subsequent_invocation': asdict(invocation), 'properties_and_entry_unchanged': True}
path = Path(__file__).resolve().parents[1] / 'evidence/python-live-observer.json'
path.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(output))
