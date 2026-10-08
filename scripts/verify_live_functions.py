"""Validate live parameter layouts against independently decompiled native thunks."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
import expedition33

names = ('Actor.IsActorBeingDestroyed', 'Actor.GetActorEnableCollision', 'Actor.K2_GetActorLocation')
functions = [expedition33.reflect_function(name) for name in names]
for fn in functions:
    assert fn.owner == 'Actor' and fn.game_thread_id > 0
    assert len(fn.parameters) == 1
    assert fn.parameters[0].name == 'ReturnValue' and fn.parameters[0].offset == fn.return_offset == 0
    assert fn.flags & 0x400  # Branch leading to native dispatch in this target.
for fn, entry in zip(functions[:2], (0x333be80, 0x3339a70)):
    assert fn.params_size == 1 and fn.entry_rva == entry
    assert fn.parameters[0].type == 'BoolProperty'
    assert fn.parameters[0].bool_encoding == 0xff010001
assert functions[2].params_size == 24 and functions[2].parameters[0].type == 'StructProperty'
assert len({fn.pid for fn in functions}) == len({fn.game_thread_id for fn in functions}) == 1
try:
    expedition33.reflect_function('Object.IsActorBeingDestroyed')
except expedition33.RuntimeQueryError as error:
    assert 'NO_VALID_OBJECTS' in str(error)
else:
    raise AssertionError('Wrong owner matched a function from Actor')
evidence = {'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'live read-only function metadata; no invocation',
            'functions': [asdict(fn) for fn in functions]}
path = Path(__file__).resolve().parents[1] / 'evidence/python-live-functions.json'
path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
for fn in functions:
    print(fn.owner + '.' + fn.name, fn.params_size, hex(fn.entry_rva), 'GameThread', fn.game_thread_id)
