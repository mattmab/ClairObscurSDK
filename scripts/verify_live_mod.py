"""Public loader lifecycle and a real, harmless Python mod."""
import json
import logging
from pathlib import Path
import expedition33
from expedition33.mods import ModLoader

root = Path(__file__).resolve().parents[1]
messages = []
class Capture(logging.Handler):
    def emit(self, record):
        messages.append(record.getMessage())
logger = logging.getLogger('expedition33.mods.ExampleMod')
capture = Capture()
logger.addHandler(capture)
logger.setLevel(logging.INFO)
baseline = expedition33.reflect_function('Actor.IsActorBeingDestroyed')
try:
    with ModLoader(root / 'mods') as loader:
        assert 'ExampleMod' in loader.discover()
        for _ in range(3):
            loader.load('ExampleMod')
            loader.load('ExampleMod')
            loader.enable('ExampleMod')
            loader.enable('ExampleMod')
            assert loader.status()[0].enabled
            assert loader.poll('ExampleMod') == 0
            loader.disable('ExampleMod')
            loader.disable('ExampleMod')
            assert not loader.status()[0].enabled
            loader.unload('ExampleMod')
            loader.unload('ExampleMod')
            assert loader.status() == ()
            assert expedition33.reflect_function('Actor.IsActorBeingDestroyed') == baseline
    assert len([message for message in messages if message.startswith('Observed ')]) == 3
finally:
    logger.removeHandler(capture)
result = {'cycles': 3, 'messages': messages, 'entry_restored_each_cycle': True}
(root / 'evidence/python-live-mod.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
