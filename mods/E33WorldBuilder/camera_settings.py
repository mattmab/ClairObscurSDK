"""Validated, atomically saved camera preferences."""
import json
import math
from pathlib import Path

DEFAULTS = dict(sensitivity=1.25, fly_speed=1600., highlight=True, duplicate_click=False)

def validate(values):
    result = dict(DEFAULTS, **values)
    for key, low, high in (('sensitivity', .05, 10.), ('fly_speed', 100., 10000.)):
        value = result[key]
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError(f'{key} must be between {low:g} and {high:g}')
        result[key] = float(value)
    if type(result['highlight']) is not bool and result['highlight'] != 'click':raise ValueError('highlight must be automatic, on click, or off')
    if type(result['duplicate_click']) is not bool:raise ValueError('duplicate_click must be boolean')
    return {key: result[key] for key in DEFAULTS}

class CameraSettings:
    def __init__(self, root):
        self.path = Path(root)/'camera-settings.json'
        try:self.values = validate(json.loads(self.path.read_text(encoding='utf8')))
        except (OSError, ValueError, TypeError):self.values = dict(DEFAULTS)

    def save(self, values):
        values = validate(values)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(values, indent=2)+'\n', encoding='utf8')
        temporary.replace(self.path)
        self.values = values

def selected_owned(owned, identity):
    """Match the complete native identity; a recycled index is not a selection."""
    return next((row for row in owned.values() if tuple(row.get('component', ())) == tuple(identity)), None)
