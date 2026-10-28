"""Fresh, bounded game-owned cinematic history for the active loaded context.

This observes the same GI map as HasPlayedCinematic. It is not a persisted save
snapshot and never merges history from another slot or previous observation.
"""
from types import MappingProxyType
import re
from expedition33 import RuntimeQueryError
from expedition33.catalog import capture_matching,capture_selected
from expedition33.values import read_object_reference, read_values_many, StoredMap

CONTEXT_FIELDS = ('GameInstanceReference', 'LoadIsInProgress', 'SelectedSlot',
                  'SaveManager', 'SaveLoaded', 'InteractedCinematics')


class PreparedHistorySelectors:
    """Retain selectors only; history, slot and reciprocal links stay fresh."""
    def __init__(self,scope):
        from expedition33._stable_lease import acquire_stable
        scope._check();self.scope=scope
        catalog=capture_matching(scope.pid,classes=('BP_SaveManager_C','GameEngine'))
        engine=one(o for o in catalog.select('GameEngine') if not o.object_flags&0x10)
        manager=one(o for o in catalog.select('BP_SaveManager_C') if not o.object_flags&0x10
                    and catalog.path_name(o).startswith('/Engine/Transient.'))
        chain,catalog=anchor(catalog,project=True)
        self.chain_indices=tuple(o.index for o in chain)
        self.leases=tuple(acquire_stable(scope,o)[0] for o in (*chain,manager))

    def capture(self,scope):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session or not all(o.active for o in self.leases):
            raise RuntimeError('Prepared history selectors are no longer owned by this session')
        return capture_selected(scope.pid,tuple((o.object.index,o.object.serial,o.object.address) for o in self.leases))

    def anchor(self,catalog):
        """Observe all three current links together; never reuse link values."""
        chain=tuple(catalog.by_index[index] for index in self.chain_indices)
        observed=read_values_many(catalog,chain[:3],fields=('GameViewport','World','OwningGameInstance'))
        for owner,name,target in zip(chain,('GameViewport','World','OwningGameInstance'),chain[1:]):
            if identity(field(observed[owner.index],name,'ObjectProperty'))!=identity(target):
                raise RuntimeError('Active world context changed while reading cinematic history')
        if chain[-1].class_name!='BP_jRPG_GI_Custom_C' or chain[-1].object_flags&0x10:
            raise RuntimeError('Active world has no verified game instance')
        return chain,catalog


def observation_error_reason(error):
    """Bounded UI text only; the caller logs the original exception privately."""
    if isinstance(error, RuntimeQueryError):
        codes = re.findall(r'"message"\s*:\s*"([A-Z][A-Z0-9_]{0,95})"', str(error))
        if any(code in ('MATCH_TYPE_NOT_REGISTERED', 'MATCH_TYPE_CHANGED',
                        'DESCRIPTOR_IDENTITY_CHANGED', 'SELECTED_DEPENDENCY_NOT_REGISTERED',
                        'SELECTED_DEPENDENCY_CHANGED') for code in codes):
            return 'Game objects changed during discovery. Refresh after loading finishes.'
        if 'MATCH_RESULTS_EMPTY' in codes:
            return 'The current game context is not available yet. Refresh after loading finishes.'
        if 'timed out' in str(error):
            return 'History observation timed out. Refresh to start a new observation.'
        return 'Current game history could not be read. Details are in the SDK log.'
    trusted = ('A save load is in progress', 'Current game history has no loaded save context',
               'Current selected slot is unavailable',
               'Active world context changed while reading cinematic history',
               'Selected slot or cinematic history changed during observation',
               'History belongs to another world')
    if str(error) in trusted:
        return str(error)
    return 'Current save history could not be verified. Details are in the SDK log.'


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


def anchor(catalog, *, project=False):
    if type(project) is not bool:
        raise ValueError('Anchor projection must be bool')
    engine = one(o for o in catalog.select('GameEngine') if not o.object_flags & 0x10)
    def reference(obj, owner_name, name):
        nonlocal catalog
        owner = catalog.by_index[catalog.find_class(owner_name).index]
        result, catalog = (read_object_reference(catalog, obj, owner, name, project=True)
                           if project else read_object_reference(catalog, obj, owner, name))
        identity(result)
        return result
    viewport = reference(engine, 'Engine', 'GameViewport')
    world = reference(viewport, 'GameViewportClient', 'World')
    gi = reference(world, 'World', 'OwningGameInstance')
    if gi.class_name != 'BP_jRPG_GI_Custom_C' or gi.object_flags & 0x10:
        raise RuntimeError('Active world has no verified game instance')
    return (engine, viewport, world, gi), catalog


def context(catalog, manager, gi):
    # A projected batch retains each object's fresh identity/metadata validation;
    # it is not atomic. The second complete context observation below remains
    # mandatory, including the reciprocal references and exact history payload.
    observed = read_values_many(catalog, (manager, gi), fields=CONTEXT_FIELDS)
    manager_values, gi_values = observed[manager.index], observed[gi.index]
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


def read_current_history(session,*,prepared=None):
    session._check()
    catalog = (prepared.capture(session) if prepared is not None else
               capture_matching(session.pid, classes=('BP_SaveManager_C', 'GameEngine')))
    if catalog.pid != session.pid:
        raise RuntimeError('Current history catalog session mismatch')
    observe_anchor=(prepared.anchor if isinstance(prepared,PreparedHistorySelectors) else
                    lambda current:anchor(current,project=True))
    chain_before, catalog = observe_anchor(catalog)
    gi = chain_before[-1]
    manager = one(o for o in catalog.select('BP_SaveManager_C')
                  if not o.object_flags & 0x10 and catalog.path_name(o).startswith('/Engine/Transient.'))
    manager_cls = catalog.by_index[manager.class_index]
    manager_gi, catalog = read_object_reference(catalog, manager, manager_cls, 'GameInstanceReference', project=True)
    if identity(manager_gi) != identity(gi):
        raise RuntimeError('Selected manager is outside the active world context')
    gi_cls = catalog.by_index[gi.class_index]
    reciprocal, catalog = read_object_reference(catalog, gi, gi_cls, 'SaveManager', project=True)
    if identity(reciprocal) != identity(manager):
        raise RuntimeError('Current manager reference is not reciprocal')
    # The ordinary stored-value decoder validates each native map's metadata and
    # complete bounded payload. String keys and strict bool values below admit
    # only its Name->Bool branch; an empty map grants no unlocks. Describing the
    # entire GI class would require unrelated descriptors absent from this
    # intentionally selected catalog and provides no stronger unlock evidence.
    before = context(catalog, manager, gi)
    chain_after, catalog = observe_anchor(catalog)
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
