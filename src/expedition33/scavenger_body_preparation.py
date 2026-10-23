"""Candidate-only original Scavenger body preparation using existing SDK owners.

This removes the editor dependency from the already tested body-only path.
It supplies no combat authority, mask, grounding proof, or catalog admission.
Construct and retain this object before calling prepare; unknown outcomes retain
both scopes and their native owner until explicit retirement succeeds.
"""
import hashlib
import json
import math
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
BODY = '/Game/Characters/Enemies/YellowForest/Boss_Scavenger/scavengers_rigg.scavengers_rigg'
CLIP = '/Game/Animations/Enemies/YellowForest/Scavenger/Anim_Othi/A_Scavengers_HideAtkV2.A_Scavengers_HideAtkV2'
SOURCE = '/Game/Levels/OrangeForest/GameActions/DA_GA_SQT_BossScavenger.DA_GA_SQT_BossScavenger:BP_GameAction_TriggerBattle_C_0'


def contract():
    result = json.loads((HERE / 'scavenger-body-contract.json').read_text())
    if (result['schema'] != 1 or result['runtime_scene_protocol'] != 7 or
            result['body'] != BODY or result['animation'] != CLIP or
            result['body_only'] is not True or result['combat_enabled'] is not False or
            len(result['dependencies']) != 134):
        raise ValueError('Exact body preparation contract required')
    return result


def plan(position=(1600, 0, 0), yaw=180):
    """Bounded player-relative proposal; never an original-map placement claim."""
    if type(position) not in (tuple, list) or len(position) != 3:
        raise ValueError('Three player-relative coordinates required')
    if any(type(v) not in (float, int) or not math.isfinite(v) or abs(v) > 5000 for v in position):
        raise ValueError('Player-relative position outside existing scene bounds')
    if type(yaw) not in (float, int) or not math.isfinite(yaw) or abs(yaw) > 360:
        raise ValueError('Bounded yaw required')
    evidence = contract()
    raw = (HERE / 'scavenger-body.plan').read_bytes()
    if len(raw) != 3304 or hashlib.sha256(raw).hexdigest() != evidence['plan_sha256']:
        raise ValueError('Compiled original body plan changed')
    result = bytearray(raw)
    struct.pack_into('<3d', result, 8 + 8 * 8, *position)
    struct.pack_into('<d', result, 8 + 8 * 12, yaw)
    return bytes(result)


def select_dependencies(spec, context, objects):
    """Select exact paths from fresh observations; reject ambiguous identities."""
    result = []
    for row in spec:
        if row['kind'] == 'context':
            if row['name'] not in context: raise ValueError('Missing current context dependency')
            result.append(context[row['name']])
        else:
            matches = [obj for path, cls, obj in objects if path == row['path'] and
                       (row.get('class_name') is None or cls == row['class_name'])]
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous exact dependency: ' + row['path'])
            result.append(matches[0])
    if len(result) != 134: raise ValueError('Exact existing native input count required')
    return tuple(result)


def resolve_dependencies(scope):
    from expedition33.assets import load_asset
    from expedition33.catalog import capture_matching, capture_selected
    from expedition33.values import read_object_reference
    from expedition33.cinematics.original_game_action import controller_context
    from expedition33._reader import ReadBatch

    specs = contract()['dependencies']
    before = controller_context(scope._session)
    asset_paths = tuple(dict.fromkeys(row['path'] for row in specs if row['kind'] == 'asset'))
    names = sorted({row['path'].rsplit(':', 1)[-1].rsplit('.', 1)[-1]
                    for row in specs if row['kind'] != 'context'} |
                   {'Player', 'Controller', 'LocalPlayer'})
    initial = capture_matching(scope.pid, names=names)
    retained = []
    for path in asset_paths:
        found = [obj for obj in initial.objects if initial.path_name(obj) == path and
                 not obj.object_flags & 0x40000000]
        if len(found) > 1: raise ValueError('Ambiguous original asset: ' + path)
        obj = scope.retain(found[0]).object if found else load_asset(scope, path).return_value
        if obj is None: raise RuntimeError('Original asset load failed: ' + path)
        retained.append(obj)
    with ReadBatch(scope.pid, share=True, _executable=scope._session._transport._executable):
        c = capture_matching(scope.pid, names=names, classes=('LocalPlayer',))
        c = c.with_observations(capture_selected(scope.pid, tuple((o.index, o.serial, o.address) for o in retained)))
        locals_ = [o for o in c.select('LocalPlayer') if not o.object_flags & 0x30]
        if len(locals_) != 1: raise RuntimeError('Exact current local player required')
        local = locals_[0]
        player, c = read_object_reference(c, local, c.by_index[c.find_class('Player').index], 'PlayerController')
        if player is None or (player.index, player.serial, player.address) != tuple(before['controller'][1:]):
            raise RuntimeError('Current controller changed')
        pawn, c = read_object_reference(c, player, c.by_index[c.find_class('Controller').index], 'Pawn')
        if pawn is None or pawn.class_name not in ('BP_jRPG_Character_World_C', 'BP_jRPG_Character_WorldMap_pawn_C'):
            raise RuntimeError('Normal exploration pawn required')
        inputs = select_dependencies(specs, dict(local=local, controller=player, pawn=pawn),
                                     [(c.path_name(o), o.class_name, o) for o in c.objects
                                      if not o.object_flags & 0x40000000])
    if controller_context(scope._session) != before:
        raise RuntimeError('World/controller changed during body preparation')
    return inputs


class ScavengerBodyPreparation:
    """Retain before prepare; explicit cleanup always owns uncertain outcomes."""
    def __init__(self, parent_scope):
        from expedition33._scope import SessionScope
        from expedition33.native_visual_staging import NativeVisualStage
        self.scope = SessionScope(parent_scope)
        try: self.owner = NativeVisualStage(self.scope)
        except BaseException:
            self.scope.close()
            raise
        self.loading = SessionScope(self.scope)
        self.attempted = False
        self.closed = False

    def prepare(self, position=(1600, 0, 0), yaw=180):
        if self.attempted or self.closed: raise RuntimeError('Body preparation is never replayed')
        raw = plan(position, yaw)
        self.attempted = True
        inputs = resolve_dependencies(self.loading)
        result = self.owner.prepare(raw, inputs)
        self.loading.close()
        return result

    def close(self):
        if self.closed: return True
        if not self.owner.close(): return False
        self.loading.close()
        self.scope.close()
        self.closed = True
        return True
