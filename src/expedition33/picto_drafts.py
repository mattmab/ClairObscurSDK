"""Local, per-Picto draft state and verified scaling-table previews."""
import math

STAT_KEYS = (1, 6, 8, 9)


def preview_stats(scaling, level, multipliers):
    """BP_ItemInstance_Gear.RefreshCurrentGearStats: FCeil(base * multiplier)."""
    if type(level) is not int or not 1 <= level <= 33 or level not in scaling:
        raise ValueError('Unobserved Picto scaling level')
    result = {}
    for key in STAT_KEYS:
        base, multiplier = scaling[level][key], multipliers.get(key, 0.)
        if not math.isfinite(base) or base < 0 or not math.isfinite(multiplier) or not 0 <= multiplier <= 10:
            raise ValueError('Invalid Picto preview input')
        result[key] = math.ceil(base * multiplier)
    return result


class PictoDraft:
    """Retain only changed fields, with their original values for conflict checks."""
    def __init__(self, identity):
        self.identity = identity
        self.changes = {}
        self.baselines = {}

    def stage(self, field, value, current):
        baseline = self.baselines.get(field, current)
        if value == baseline:
            self.changes.pop(field, None)
            self.baselines.pop(field, None)
        else:
            self.baselines[field] = baseline
            self.changes[field] = value

    def value(self, field, current):
        return self.changes.get(field, current)

    def conflicts(self, current):
        return tuple(field for field, value in self.baselines.items() if current.get(field) != value)

    def acknowledge(self, field):
        self.changes.pop(field, None)
        self.baselines.pop(field, None)
