"""Fresh, bounded game-owned cinematic history for the active loaded context.

This observes the same GI map as HasPlayedCinematic. It is not a persisted save
snapshot and never merges history from another slot or previous observation.
"""
from types import MappingProxyType
from expedition33.catalog import capture_matching
from expedition33.values import read_object_reference, read_values, StoredMap


def identity(obj):
    if obj is None:
        raise RuntimeError('Current history context reference is null')
    return (obj.pid, obj.index, obj.serial, obj.address)


def one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise RuntimeError('Current history context is ambiguous or unavailable')
    return rows[0]


def field(observed, name, kind):
    key = one(key for key in observed.types if key[1] == name)
    if (observed.types[key] != kind or key not in observed.values or key in observed.errors or
            key in observed.truncated):
        raise RuntimeError(f'Current history field is incomplete: {name}')
    return observed.values[key]


def anchor(catalog):
    engine = one(o for o in catalog.select('GameEngine') if not o.object_flags & 0x10)
    def reference(obj, owner_name, name):
        nonlocal catalog
        owner = catalog.by_index[catalog.find_class(owner_name).index]
        result, catalog = read_object_reference(catalog, obj, owner, name)
        identity(result)
        return result
    viewport = reference(engine, 'Engine', 'GameViewport')
    world = reference(viewport, 'GameViewportClient', 'World')
    gi = reference(world, 'World', 'OwningGameInstance')
    if gi.class_name != 'BP_jRPG_GI_Custom_C' or gi.object_flags & 0x10:
        raise RuntimeError('Active world has no verified game instance')
    return (engine, viewport, world, gi), catalog


def context(catalog, manager, gi):
    manager_values = read_values(catalog, manager)
    gi_values = read_values(catalog, gi)
    if identity(field(manager_values, 'GameInstanceReference', 'ObjectProperty')) != identity(gi):
        raise RuntimeError('Save manager belongs to another game instance')
    if identity(field(gi_values, 'SaveManager', 'ObjectProperty')) != identity(manager):
        raise RuntimeError('Game instance save manager is not reciprocal')
    if field(manager_values, 'LoadIsInProgress', 'BoolProperty') is not False:
        raise RuntimeError('A save load is in progress')
    if field(gi_values, 'SaveLoaded', 'BoolProperty') is not True:
        raise RuntimeError('Current game history has no loaded save context')
    slot = field(manager_values, 'SelectedSlot', 'IntProperty')
    if type(slot) is not int or slot < 0:
        raise RuntimeError('Current selected slot is unavailable')
    history = field(gi_values, 'InteractedCinematics', 'MapProperty')
    if not isinstance(history, StoredMap):
        raise RuntimeError('Current cinematic history is not a complete map')
    if len(history.items) > 4096 or any(type(k) is not str or not k or type(v) is not bool for k, v in history.items.items()):
        raise RuntimeError('Current cinematic history is not a bounded Name-to-Bool map')
    return slot, dict(history.items)


def read_current_history(session):
    session._check()
    catalog = capture_matching(session.pid, classes=('BP_SaveManager_C', 'GameEngine'))
    if catalog.pid != session.pid:
        raise RuntimeError('Current history catalog session mismatch')
    chain_before, catalog = anchor(catalog)
    gi = chain_before[-1]
    manager = one(o for o in catalog.select('BP_SaveManager_C')
                  if not o.object_flags & 0x10 and catalog.path_name(o).startswith('/Engine/Transient.'))
    manager_cls = catalog.by_index[manager.class_index]
    manager_gi, catalog = read_object_reference(catalog, manager, manager_cls, 'GameInstanceReference')
    if identity(manager_gi) != identity(gi):
        raise RuntimeError('Selected manager is outside the active world context')
    gi_cls = catalog.by_index[gi.class_index]
    reciprocal, catalog = read_object_reference(catalog, gi, gi_cls, 'SaveManager')
    if identity(reciprocal) != identity(manager):
        raise RuntimeError('Current manager reference is not reciprocal')
    # The ordinary read_values decoder validates each native map's metadata and
    # complete bounded payload. String keys and strict bool values below admit
    # only its Name->Bool branch; an empty map grants no unlocks. Describing the
    # entire GI class would require unrelated descriptors absent from this
    # intentionally selected catalog and provides no stronger unlock evidence.
    before = context(catalog, manager, gi)
    chain_after, catalog = anchor(catalog)
    if tuple(map(identity, chain_before)) != tuple(map(identity, chain_after)):
        raise RuntimeError('Active world context changed while reading cinematic history')
    after = context(catalog, manager, gi)
    session._check()
    if before != after:
        raise RuntimeError('Selected slot or cinematic history changed during observation')
    slot, history = after
    return dict(history=StoredMap(MappingProxyType(history)), history_source='current-session game history',
        game_instance=catalog.path_name(gi), manager=catalog.path_name(manager), selected_slot=slot,
        context_identities=dict(zip(('engine', 'viewport', 'world', 'game_instance'), map(identity, chain_after))),
        field='InteractedCinematics', field_type='MapProperty', decoded=True, read_error=None)
