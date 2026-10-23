"""Read-only enemy arena observations; these do not authorize spawning."""
from .catalog import capture_matching, capture_selected
from .cinematics.original_game_action import controller_context
from ._reader import ReadBatch

ARENA_CLASS='/Game/Levels/Battle_Maps/BP_BattleMap.BP_BattleMap_C'
_EXCLUDED_FLAGS=0x40018030


def _identity(obj):
    return (obj.index,obj.serial,obj.address)


def _arena_candidates(catalog,world_identity):
    """Filter by original class ancestry and exact owning-world identity."""
    classes=[obj for obj in catalog.objects if catalog.path_name(obj)==ARENA_CLASS]
    if len(classes)!=1:
        raise RuntimeError('Original battle-map class is unavailable or ambiguous')
    original=classes[0]
    if original.index not in catalog.classes:
        raise RuntimeError('Original battle-map class descriptor is missing')
    world_identity=tuple(world_identity)
    rows=[]
    for obj in catalog.objects:
        if obj.object_flags&_EXCLUDED_FLAGS or original.index not in catalog.ancestors(obj.class_index):
            continue
        worlds=[outer for outer in catalog.outer_chain(obj) if outer.class_name=='World']
        if len(worlds)!=1 or _identity(worlds[0])!=world_identity:
            continue
        rows.append(dict(identity=_identity(obj),path=catalog.path_name(obj),
                         class_path=catalog.path_name(catalog.by_index[obj.class_index])))
    if len(rows)>256:
        raise RuntimeError('Current-world battle-map candidate limit exceeded')
    return rows


def observe_battle_arenas(session):
    """Observe original current-world arenas without invocation or retention.

    This is neither an atomic snapshot nor a readiness guarantee. A native
    operation must revalidate identities, world and arena state before mutation.
    Candidate order does not reproduce the engine's fallback enumeration order.
    """
    with ReadBatch(session.pid,share=True,_executable=session._transport._executable):
        context=controller_context(session)
        catalog=capture_matching(session.pid,classes=('BP_BattleMap_C',))
        catalog=catalog.with_observations(capture_selected(session.pid,(context['world'][1:],)))
        rows=_arena_candidates(catalog,context['world'][1:])
        after=controller_context(session)
        if after!=context:
            raise RuntimeError('World/controller changed during enemy arena observation')
    return dict(world_path=context['world_path'],world_identity=tuple(context['world'][1:]),
                arenas=rows,candidate_count=len(rows),read_only=True,
                readiness='unverified',
                limitations=('Arena presence does not prove streaming or spawn-point readiness.',
                             'No candidate ordering or nearest-arena guarantee.',
                             'Observations require native revalidation before mutation.'))
