"""Actual Python -> native -> game-thread reflected dispatch -> boolean return."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import expedition33

metadata = expedition33.reflect_function('Actor.IsActorBeingDestroyed')
before = expedition33.stored_bools('Default__Actor')
result = expedition33.invoke_proof()
after = expedition33.stored_bools('Default__Actor')
assert result.pid == before.pid == after.pid == metadata.pid
assert result.object_index == before.index == after.index
assert result.function_index == metadata.index
assert result.game_thread_id == metadata.game_thread_id
assert result.result is False, 'The native default Actor should not be being destroyed'
assert before == after, 'Observed default-object stored booleans changed'
assert result.hook_removed and result.remote_module_unloaded
output = {'timestamp': datetime.now(timezone.utc).isoformat(),
          'source': 'actual live reflected invocation, not a read-only substitute',
          'function': asdict(metadata), 'invocation': asdict(result),
          'before_after_booleans_equal': True}
path = Path(__file__).resolve().parents[1] / 'evidence/python-live-invocation.json'
path.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(json.dumps(asdict(result)))
