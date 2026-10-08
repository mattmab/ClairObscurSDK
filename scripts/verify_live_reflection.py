"""Live-only native class metadata check; no canned data or offline fallback."""
from dataclasses import asdict
import json
from pathlib import Path
from datetime import datetime, timezone
import expedition33


actor = expedition33.reflect_class('Actor')
hud = expedition33.reflect_class('HUD')
root = expedition33.reflect_class('Object')
assert actor.hierarchy == ('Actor', 'Object'), actor.hierarchy
assert hud.hierarchy == ('HUD', 'Actor', 'Object'), hud.hierarchy
assert root.hierarchy == ('Object',) and not root.properties
assert actor.pid == hud.pid == root.pid
actor_fields = {(p.owner, p.name): p for p in actor.properties}
hud_fields = {(p.owner, p.name): p for p in hud.properties}
assert actor_fields and actor_fields.items() <= hud_fields.items()
assert actor_fields['Actor', 'PrimaryActorTick'].type == 'StructProperty'
assert actor_fields['Actor', 'RootComponent'].type == 'ObjectProperty'
assert actor_fields['Actor', 'PrimaryActorTick'].struct_name == 'ActorTickFunction'
assert actor_fields['Actor', 'RemoteRole'].enum_name == 'ENetRole'
enum_field = actor_fields['Actor', 'UpdateOverlapsMethodDuringLevelStreaming']
assert enum_field.enum_name == 'EActorUpdateOverlapsMethod'
assert enum_field.inner_type == 'ByteProperty' and enum_field.inner_element_size == 1
assert actor_fields['Actor', 'Tags'].inner_type == 'NameProperty'
assert actor_fields['Actor', 'Tags'].inner_element_size == 8
assert actor_fields['Actor', 'Children'].inner_type == 'ObjectProperty'
for cls in (actor, hud, root):
    sizes = dict(zip(cls.hierarchy, cls.sizes))
    assert len({(p.owner, p.name) for p in cls.properties}) == len(cls.properties)
    for p in cls.properties:
        assert p.offset + p.element_size * p.dimension <= sizes[p.owner]
try:
    expedition33.reflect_class('__E33_RESEARCH_NONEXISTENT_CLASS__')
except expedition33.RuntimeQueryError as error:
    assert 'NO_VALID_OBJECTS' in str(error)
else:
    raise AssertionError('Missing native class silently accepted')
evidence = {'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': 'live independent native bridge',
            'classes': [asdict(cls) for cls in (actor, hud, root)]}
path = Path(__file__).resolve().parents[1] / 'evidence/python-live-reflection.json'
path.write_text(json.dumps(evidence, indent=2), encoding='utf-8')
for cls in (actor, hud, root):
    print(cls.name, cls.hierarchy, cls.sizes, len(cls.properties), 'properties')
