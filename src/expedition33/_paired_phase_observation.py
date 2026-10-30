"""Read-only evidence for the exact paired Duolliste phase presentation.

This observes game-owned cinematic state; it neither owns nor modifies it.
An active sequence/player or matching view target never proves visible pixels.
"""
from dataclasses import dataclass

from ._reader import ReadBatch
from .catalog import capture_matching, capture_selected
from .values import StoredStruct, read_values_with_references
from .cinematics.original_game_action import controller_context

SOURCE = '/Game/Levels/CleasTower/GameActions/DA_GA_SQT_DuallisteAlpha.DA_GA_SQT_DuallisteAlpha:BP_GameAction_TriggerBattle_C_1'
SEQUENCE = '/Game/Cinematics/ForgottenBattlefield/DuallistePhase2/CS_FB_DuollistePhase2.CS_FB_DuollistePhase2'
CINEMATIC_ID = 'DuollistPhase2'
SYSTEM_CLASS = '/Game/Gameplay/CinematicSystem/BP_CinematicSystem.BP_CinematicSystem_C'
ID_FIELD = 'Cinematic_LevelSequence_ID_91_4BF2F07945DDA6A45F872BB126F199C0'


def _id(obj):
    return None if obj is None else (obj.index, obj.serial, obj.address)


def _read(catalog, obj, fields):
    values, catalog = read_values_with_references(catalog, obj, fields=fields)
    rows = {key[1]: value for key, value in values.values.items()}
    if values.errors or values.truncated or set(rows) != set(fields) or len(rows) != len(values.values):
        raise RuntimeError('Incomplete paired cinematic observation')
    return rows, catalog


def _struct_field(value, field):
    # Unrelated fields may be unsupported native-owned types. Only the exact
    # selected copied field is required; never fill an absent field by guessing.
    if not isinstance(value, StoredStruct) or value.truncated or field not in value.fields or field in value.errors:
        raise RuntimeError('Required paired cinematic struct field unavailable: ' + field)
    return value.fields[field]


@dataclass(frozen=True)
class PairPhaseObservation:
    world: tuple
    system: tuple
    requested_id: str
    is_cinematic: bool
    sequence_started: bool
    actor: tuple | None
    player: tuple | None
    asset_path: str | None
    player_status: object
    camera_target: tuple | None
    camera_class: str | None
    state: str


def classify(*, requested_id, is_cinematic, sequence_started, actor, player, asset_path):
    """Classify evidence only; no state represents visual acceptance."""
    if type(requested_id) is not str or type(is_cinematic) is not bool or type(sequence_started) is not bool:
        raise ValueError('Strict copied cinematic ID/boolean fields required')
    if requested_id != CINEMATIC_ID:
        return 'other_or_idle'
    if not is_cinematic:
        return 'pair_requested_not_active'
    if actor is None or player is None:
        return 'pair_preparing'
    if asset_path != SEQUENCE:
        return 'pair_asset_mismatch'
    return 'pair_sequence_started' if sequence_started else 'pair_sequence_not_started'


def observe(scope, *, expected_context=None):
    """Copy one bounded current-world sample, without invoking game functions.

    Uses a filtered CinematicSystem discovery, then selected reference reads.
    Pass the battle owner's context to reject a world/controller replacement.
    Sampling every frame is discouraged; use phase boundaries or bounded cadence.
    A caller must combine these observations with live visual evidence.
    """
    scope._check()
    session = scope._session
    context = controller_context(session, project=True)
    if expected_context is not None and context != expected_context:
        raise RuntimeError('Paired cinematic context changed before observation')
    with ReadBatch(scope.pid, share=True, _executable=session._transport._executable):
        catalog = capture_matching(scope.pid, classes=('BP_CinematicSystem_C',))
        world = tuple(context['world'][1:])
        systems = [obj for obj in catalog.objects if obj.class_name == 'BP_CinematicSystem_C'
                   and not obj.object_flags & 0x30
                   and any(_id(outer) == world for outer in catalog.outer_chain(obj))]
        if len(systems) != 1:
            raise RuntimeError('Expected one current-world paired cinematic system')
        system = systems[0]
        if catalog.path_name(catalog.by_index[system.class_index]) != SYSTEM_CLASS:
            raise RuntimeError('Paired cinematic system class changed')
        values, catalog = _read(catalog, system, ('CurrentTriggerCinematicParameters',
            'IsPlayingCinematic', 'SequenceStarted', 'LevelSequencePlayerActor', 'LevelSequencePlayer'))
        requested = _struct_field(values['CurrentTriggerCinematicParameters'], ID_FIELD)
        actor, player = values['LevelSequencePlayerActor'], values['LevelSequencePlayer']
        asset_path = status = None
        if actor is not None and player is not None:
            if actor.class_name != 'LevelSequenceActor' or player.class_name != 'LevelSequencePlayer':
                raise RuntimeError('Unexpected paired cinematic actor/player types')
            if player.outer_index != actor.index or player.outer_serial != actor.serial:
                raise RuntimeError('Paired cinematic player is outside its actor')
            a, catalog = _read(catalog, actor, ('SequencePlayer', 'LevelSequenceAsset'))
            p, catalog = _read(catalog, player, ('Sequence', 'Status'))
            if (_id(a['SequencePlayer']) != _id(player) or a['LevelSequenceAsset'] is None
                    or _id(a['LevelSequenceAsset']) != _id(p['Sequence'])):
                raise RuntimeError('Paired cinematic actor/player asset mismatch')
            asset_path = catalog.path_name(p['Sequence'])
            status = p['Status']
        selected = capture_selected(scope.pid, (tuple(context['controller'][1:]),))
        catalog = catalog.with_observations(selected)
        controller = catalog.by_index[context['controller'][1]]
        camera, catalog = _read(catalog, controller, ('PlayerCameraManager',))
        camera_target = camera_class = None
        if camera['PlayerCameraManager'] is not None:
            camera, catalog = _read(catalog, camera['PlayerCameraManager'], ('ViewTarget',))
            target = _struct_field(camera['ViewTarget'], 'Target')
            camera_target = _id(target)
            camera_class = None if target is None else catalog.path_name(catalog.by_index[target.class_index])
        state = classify(requested_id=requested, is_cinematic=values['IsPlayingCinematic'],
                         sequence_started=values['SequenceStarted'], actor=actor, player=player, asset_path=asset_path)
        result = PairPhaseObservation(tuple(context['world']), _id(system), requested,
            values['IsPlayingCinematic'], values['SequenceStarted'], _id(actor), _id(player),
            asset_path, status, camera_target, camera_class, state)
    scope._check()
    if controller_context(session, project=True) != context:
        raise RuntimeError('Paired cinematic context changed during observation')
    return result
