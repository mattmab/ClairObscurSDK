"""Durable Picto overrides keyed by reflected ItemDefinitionID, never pointers."""
import copy
import math
from expedition33.settings import SettingsStore, SettingsError

MOD_ID = 'sdk.picto-editor'


def validate(profiles):
    if type(profiles) is not dict or len(profiles) > 1024:
        raise SettingsError('Invalid Picto profiles')
    for identity, fields in profiles.items():
        if type(identity) is not str or not 1 <= len(identity) <= 256 or any(ord(c) < 32 for c in identity):
            raise SettingsError('Invalid Picto definition ID')
        if type(fields) is not dict or not fields or set(fields) - {'multipliers', 'level', 'cost', 'mastered', 'owned'}:
            raise SettingsError('Invalid Picto override fields')
        for key, value in fields.items():
            if key == 'multipliers':
                if type(value) is not dict or not value or set(value) - {'1', '6', '8', '9'}:
                    raise SettingsError('Invalid Picto stat keys')
                if any(type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 10 for v in value.values()):
                    raise SettingsError('Invalid Picto multiplier')
            elif key in ('mastered', 'owned'):
                if type(value) is not bool:
                    raise SettingsError('Invalid Picto mastery state')
            elif type(value) is not int or not (1 <= value <= 33 if key == 'level' else 0 <= value <= 100):
                raise SettingsError('Invalid Picto level or cost')
    return profiles


class PictoPreferences:
    def __init__(self, path):
        self.store = SettingsStore(path)
        options = self.store.get(MOD_ID).get('options', {})
        if options and (options.get('schema') != 1 or set(options) != {'schema', 'pictos'}):
            raise SettingsError('Unsupported Picto configuration schema')
        self.profiles = validate(options.get('pictos', {}))

    def remember(self, identity, mode, value, stat=None):
        self.remember_many(identity, [(mode, value, stat)])

    def remember_ownership(self, identities, desired):
        self.remember_field(identities, 'owned', desired)

    def remember_field(self, identities, field, value):
        updated = copy.deepcopy(self.profiles)
        for identity in identities:
            updated.setdefault(identity, {})[field] = value
        validate(updated)
        self.store.save(MOD_ID, {'options': {'schema': 1, 'pictos': updated}})
        self.profiles = updated

    def remember_many(self, identity, changes):
        updated = copy.deepcopy(self.profiles)
        record = updated.setdefault(identity, {})
        for mode, value, stat in changes:
            if mode == 'stat':
                record.setdefault('multipliers', {})[str(stat)] = value
            else:
                record['mastered' if mode == 'mastery' else mode] = value
        validate(updated)
        self.store.save(MOD_ID, {'options': {'schema': 1, 'pictos': updated}})
        self.profiles = updated
