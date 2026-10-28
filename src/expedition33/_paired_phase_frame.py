"""Exact original paired encounter frame; no arbitrary-map relocation claim.

Copied source configuration only. These checks do not establish collision,
streaming readiness, ownership or authority to place an arena.
"""
import math

WORLD = '/Game/Levels/CleasTower/Level_Side_CleasTower.Level_Side_CleasTower'
ARENA = WORLD + ':PersistentLevel.BP_BattleMap_C_UAID_581122C6E7A55E9802_2111835188'
CLASS = '/Game/Levels/Battle_Maps/BattleMap_SpecialEnemies/BP_BattleMap_DuollistAlpha.BP_BattleMap_DuollistAlpha_C'
LOCATION = (-35030.83759038431, -3713.4009074234305, -28225.771533)
YAW = -50.23245300000002


def require_original_frame(world_path, pose):
    """Reject a relocated pose for an original-context presentation candidate.

    ``pose`` is the existing arena's quaternion/translation/reserved/scale format.
    No source actor is mutated. Callers must additionally validate current-world
    identity, owned actor/children, physical support and cinematic dependencies.
    """
    if world_path != WORLD:
        raise ValueError('Paired original cinematic requires the original CleasTower world')
    pose = tuple(pose)
    if len(pose) != 12 or any(type(value) not in (int, float) or not math.isfinite(value) for value in pose):
        raise ValueError('Finite exact original paired arena pose required')
    if any(abs(pose[i+4] - LOCATION[i]) > .001 for i in range(3)):
        raise ValueError('Relocated paired arena does not match the original cinematic frame')
    angle = math.radians(YAW) / 2
    quaternion = (0., 0., math.sin(angle), math.cos(angle))
    dot = sum(a*b for a,b in zip(pose[:4], quaternion))
    if (abs(abs(dot)-1.) > 1e-8 or abs(sum(value*value for value in pose[:4])-1.) > 1e-8
            or pose[7] != 0 or pose[11] != 0 or any(abs(value-1.) > 1e-8 for value in pose[8:11])):
        raise ValueError('Original paired arena orientation/scale differs')
    return pose


def original_pose(world_path):
    """Return the exact source pose only for the original presentation world."""
    angle = math.radians(YAW) / 2
    pose = (0., 0., math.sin(angle), math.cos(angle), *LOCATION, 0., 1., 1., 1., 0.)
    return require_original_frame(world_path, pose)
