"""Exercise live reflected boolean storage, including inherited properties."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import expedition33


actor = expedition33.stored_bools('Default__Actor')
hud = expedition33.stored_bools('Default__HUD')
repeat = expedition33.stored_bools('Default__Actor')
assert actor == repeat, 'Default-object observations changed between calls'
assert actor.class_name == 'Actor' and hud.class_name == 'HUD'
assert actor.pid == hud.pid and actor.index != hud.index
fields = {(v.owner, v.name): v for v in actor.values}
assert fields['Actor', 'bHidden'].value is False
assert fields['Actor', 'bCallPreReplication'].value is True
# The target export routine independently establishes mask semantics. Exercise
# distinct live bits in a shared byte, without changing any game state.
assert fields['Actor', 'bHidden'].raw_byte == fields['Actor', 'bCallPreReplication'].raw_byte
assert fields['Actor', 'bHidden'].mask != fields['Actor', 'bCallPreReplication'].mask
assert any(v.owner == 'HUD' for v in hud.values)
assert any(v.owner == 'Actor' for v in hud.values)
assert {v.value for v in actor.values} == {False, True}
output = {'timestamp': datetime.now(timezone.utc).isoformat(),
          'source': 'live native reflected backing-storage reads; no writes or invocation',
          'actor': asdict(actor), 'hud': asdict(hud), 'repeat_equal': True}
path = Path(__file__).resolve().parents[1] / 'evidence/python-live-bools.json'
path.write_text(json.dumps(output, indent=2), encoding='utf-8')
print(actor.object_name, actor.index, len(actor.values), 'stored booleans')
print(hud.object_name, hud.index, len(hud.values), 'stored booleans')
