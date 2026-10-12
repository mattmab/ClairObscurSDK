"""Single-scene proof through the original, audited game-action executor.

Not a catalog-wide adapter. Requires the opt-in v63 native admission gate.
The game owns actors, cameras, audio, and its normal post-scene transitions.
"""
import json
from pathlib import Path

from expedition33 import _query
from expedition33.catalog import capture_matching
from expedition33.cinematics.history import read_current_history

WORLD = '/Game/Levels/OrangeForest/Level_OraneForest_Main.Level_OraneForest_Main'
ASSET = '/Game/Levels/OrangeForest/GameActions/DA_GA_CIN_MCS_ScavengerIntro.DA_GA_CIN_MCS_ScavengerIntro'
SAVE_ID = 'Cine_ScavengerIntro_Orange'
OUTPUT = Path(__file__).resolve().parents[1] / 'evidence/scavenger-native-replay-attempt.json'


def _one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise RuntimeError('Expected one current native replay identity')
    return rows[0]


def _values(obj):
    _, rows = _query(['--read-values', str(obj.pid), f'{obj.index}:{obj.serial}:{obj.address:x}'])
    return rows


def _field(rows, name):
    row = _one(r for r in rows if r.get('name') == name and
               r.get('event') in ('stored_value', 'stored_value_error'))
    if row['event'] != 'stored_value':
        raise RuntimeError('Unreadable native replay state: ' + name)
    return row['value']


def run(session):
    session._check()
    history = read_current_history(session)
    if history['history'].items.get(SAVE_ID) is not True:
        raise RuntimeError('Scavenger Intro is not confirmed unlocked in this save')
    catalog = capture_matching(session.pid, names=('ExecuteGameAction', 'DA_GA_CIN_MCS_ScavengerIntro',
        'GameAction', 'GameActionInstance'), classes=('BP_GameActionExecutorComponent_C', 'BP_CinematicSystem_C'))
    prefix = WORLD + ':PersistentLevel.'
    executor = _one(o for o in catalog.objects if o.class_name == 'BP_GameActionExecutorComponent_C'
                    and catalog.path_name(o).startswith(prefix) and not o.object_flags & 0x30)
    component = _one(o for o in catalog.objects if o.class_name == 'BP_CinematicSystem_C'
                     and o.outer_index == executor.outer_index and not o.object_flags & 0x30)
    world = _one(o for o in catalog.outer_chain(executor) if catalog.path_name(o) == WORLD)
    if (world.pid, world.index, world.serial, world.address) != tuple(history['context_identities']['world']):
        raise RuntimeError('Scavenger executor is not in the active loaded world')
    asset = _one(o for o in catalog.objects if catalog.path_name(o) == ASSET)
    function = _one(o for o in catalog.objects if o.class_name == 'Function'
                    and o.name == 'ExecuteGameAction' and o.outer_index == executor.class_index)
    active = _field(_values(executor), 'GameActionInstancesInExecution')
    if active != {'$array': {'length': 0, 'items': []}}:
        raise RuntimeError('A game action is already executing')
    current = _values(component)
    for name in ('LevelSequencePlayer', 'LoadCinematicAssetRequest'):
        if _field(current, name) is not None:
            raise RuntimeError('A native cinematic is already active or preparing')
    report = {'pid': session.pid, 'asset': ASSET, 'world': WORLD, 'save_id': SAVE_ID,
              'unlocked': True, 'dispatch_returned': False, 'playback_verified': False,
              'executor': catalog.path_name(executor), 'component': catalog.path_name(component)}
    OUTPUT.write_text(json.dumps(report, indent=2), encoding='utf8')
    try:
        with session.invocation_planner(catalog=catalog, selected_results=True) as planner:
            with planner.prepare(executor, function, GameAction=asset).invoke():
                report['dispatch_returned'] = True
    except Exception as error:
        report['error'] = str(error)
        report['outcome'] = getattr(error, 'outcome', 'preparation_failed')
        raise
    finally:
        OUTPUT.write_text(json.dumps(report, indent=2), encoding='utf8')
    return report
