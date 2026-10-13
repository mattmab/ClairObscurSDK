"""Clear SDK overrides without mutating game objects or inventing baseline values."""
import copy
from .picto_preferences import MOD_ID


def clear_saved(preferences, identity=None):
    """Atomically forget one definition, or all definitions when identity is None."""
    updated = copy.deepcopy(preferences.profiles)
    if identity is None:
        updated.clear()
    else:
        if not isinstance(identity, str) or not identity:
            raise ValueError('A Picto definition identity is required')
        updated.pop(identity, None)
    preferences.store.save(MOD_ID, {'options': {'schema': 1, 'pictos': updated}})
    preferences.profiles = updated
