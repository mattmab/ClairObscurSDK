"""Exercise only the public persistent SDK interface against the live game."""
import json
from pathlib import Path
import expedition33
from expedition33 import sdk

baseline = expedition33.reflect_function(sdk.TARGET)
seen = []
with sdk.Session() as session:
    actor = session.find_object('Default__Actor')
    assert session.call(actor, sdk.TARGET) is False
    for _ in range(10):
        handle = session.hook(actor, sdk.TARGET, seen.append)
        assert handle.active
        assert session.call(actor, sdk.TARGET) is False
        assert session.poll() == 1
        handle.remove()
        handle.remove()
        assert not handle.active
        session.call(actor, sdk.TARGET)
        assert session.poll() == 0
    assert len(seen) == 10
    def bad_callback(context):
        raise SystemExit('Deliberate mod failure')
    bad = session.hook(actor, sdk.TARGET, bad_callback)
    good = session.hook(actor, sdk.TARGET, seen.append)
    session.call(actor, sdk.TARGET)
    assert session.poll() == 2
    assert not bad.active and good.active and len(session.failures) == 1
    assert session.failures[0].exception_type == 'SystemExit'
    good.remove()
    assert expedition33.reflect_function(sdk.TARGET) == baseline
    final = session.hook(actor, sdk.TARGET, seen.append)
    session.call(actor, sdk.TARGET)
    assert session.poll() == 1
assert not final.active
final.remove()
assert expedition33.reflect_function(sdk.TARGET) == baseline
result = {'pid': actor.pid, 'object': actor.name, 'callbacks': len(seen),
          'enable_disable_cycles': 10, 'exception_isolated': True, 'entry_restored': True}
(Path(__file__).resolve().parents[1] / 'evidence/python-live-sdk.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
