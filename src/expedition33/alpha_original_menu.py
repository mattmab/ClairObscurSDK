"""Alpha-only menu orchestration over the existing original-roster adapter.

No exploration identity promotion, source-policy changes or native operations.
"""
from .original_encounter_roster import resolve_source

ALPHA = 'a65ad026a55174bc'
ANCHOR = '46477e3952ad5200'
ALPHA_CLASS = '/Game/Characters/Enemies/HumanEnnemies/Simon/BP_EnemyBattle_Simon_ALPHA.BP_EnemyBattle_Simon_ALPHA_C'
ANCHOR_CLASS = '/Game/Characters/Enemies/YellowForest/Gault/BP_jRPG_EnemyWorld_Gault.BP_jRPG_EnemyWorld_Gault_C'


def _validate_catalog(model):
    route = resolve_source(model.catalog, ALPHA)
    for identity, class_path in ((ALPHA, ALPHA_CLASS), (ANCHOR, ANCHOR_CLASS)):
        matches = [e for e in model.catalog['entries'] if e.get('id')==identity]
        if len(matches)!=1 or matches[0].get('class_path')!=class_path:
            raise ValueError('Original Alpha entry identity no longer matches the catalog')
        if identity==ANCHOR and not matches[0].get('spawn_available'):
            raise ValueError('Original Alpha encounter anchor is unavailable')
    return route


def check_available(model):
    _validate_catalog(model)
    if model.mode!='isolated':
        raise ValueError('Alpha Simon original entry requires isolated mode')
    transport = model.spawner._scope._session._transport
    if (getattr(transport, 'owned_authored_entry_protocol', 0)!=1 or
            getattr(transport, 'encounter_retry_tuning_protocol', 0)!=1):
        raise RuntimeError('Alpha Simon requires the original-entry and retry runtime guards')
    if model.arena_identity is None:
        raise ValueError('Choose a current-world arena first')
    if any(getattr(model, key, None) is not None for key in (
            '_pending', '_pending_addition', '_npc_pending', '_helper_pending', '_original_pending', '_direct_pending')):
        raise RuntimeError('Another encounter operation is pending')
    if model.spawner._owner.has_native_work:
        raise RuntimeError('Remove the existing owned encounter first')
    if any(owner is not None and owner.phase!='closed' for owner in (
            model.npc_encounter, model.spawner.helper_encounter, getattr(model.spawner,'original_fight',None))):
        raise RuntimeError('Remove the existing NPC or boss encounter first')


def unavailable_reason(model):
    try:
        check_available(model)
    except (ValueError, RuntimeError) as error:
        return str(error)
    return None


def queue(model):
    check_available(model)
    # Preserve the user's selection at the click, including difficulty/health.
    tuning = model._capture_tuning()
    model._original_pending = dict(arena=tuple(model.arena_identity), tuning=tuning)
    return 'Starting Alpha Simon in the selected arena; closing the menu first.'


def poll(model):
    pending = getattr(model, '_original_pending', None)
    if pending is None:
        return
    # Consume before any engine work. Unknown outcomes are never replayed.
    model._original_pending = None
    model.want_open = False
    model._last_operation = dict(mode='original_alpha_roster', enemy_id=ALPHA,
        completed=False, dispatch_attempted=False, exploration_assembly_verified=False)
    try:
        model.native.parent.close_menu()
        check_available(model)
        if tuple(model.arena_identity)!=pending['arena']:
            raise RuntimeError('Selected arena changed before Alpha entry')
        tuning = pending['tuning']
        options = {'tuning': tuning} if tuning is not None and not tuning.is_default else {}
        spawned = model.spawner.spawn(ANCHOR, policy='isolated', arena_identity=pending['arena'],
                                      grounded=True, activate=False, **options)
        model._adopt_bound_arena(pending['arena'], spawned)
        model._last_operation['dispatch_attempted'] = True
        model._last_operation['result'] = model.spawner.start_authored_encounter(
            ALPHA, experimental=True, dispatch=True)
        model._last_operation['completed'] = True
        model._last_error = None
    except Exception as error:
        # Keep any owned anchor/entry journal available for explicit retirement.
        model._last_error = str(error)
