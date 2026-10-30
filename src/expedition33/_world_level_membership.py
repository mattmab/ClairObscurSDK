"""Read-only current-world admission for actors in streamed levels.

An actor's outer World may be a generated-cell source World even while its
ULevel is visible in the active World. Admission therefore requires reciprocal
OwningWorld and complete World.Levels membership, not outer names alone.
"""
from dataclasses import dataclass

from ._reader import ReadBatch, active_reader
from .catalog import capture_selected
from .cinematics.history import field, identity
from .cinematics.original_game_action import controller_context
from .values import StoredArray, read_values_with_references


@dataclass(frozen=True)
class ActorLevelMembership:
    actor: tuple
    level: tuple
    world: tuple
    controller: tuple
    level_visible: bool


def _context_key(context):
    return tuple(context['controller']),tuple(context['world']),context['world_path']


def _read(catalog,obj,names):
    observed,catalog=read_values_with_references(catalog,obj,fields=tuple(names))
    return {name:field(observed,name,kind) for name,kind in names.items()},catalog


def _level_ids(value):
    if (not isinstance(value,StoredArray) or value.length!=len(value.items) or
            not 1<=value.length<=256 or any(obj is None or obj.class_name!='Level' for obj in value.items)):
        raise RuntimeError('Complete bounded active World.Levels observation required')
    result=tuple(identity(obj) for obj in value.items)
    if len(set(result))!=len(result):
        raise RuntimeError('Duplicate active world level identity')
    return result


def _live(obj):
    if obj.object_flags&0x40000030 or getattr(obj,'item_flags',0)&0x200000:
        raise RuntimeError('Actor, level or world is a template or retiring object')


def observe_actor_membership(scope,actor,*,expected_context):
    """Prove one exact actor belongs to a visible level of the current World.

    Only selected identity/property observations and the existing filtered
    LocalPlayer context reader are used. No full catalog enumeration, streaming,
    loads, native invocation or object retention occurs. Rechecks detect changes,
    but cannot form a GC-atomic snapshot or prove camera/actor visibility.
    """
    scope._check()
    if actor.pid!=scope.pid:
        raise ValueError('Actor observation belongs to another process')
    expected=_context_key(expected_context)
    if any(len(row)!=4 or row[0]!=scope.pid for row in expected[:2]):
        raise ValueError('Expected same-process current world/controller identities')
    executable=scope._session._transport._executable
    with ReadBatch(scope.pid,share=active_reader() is None,_executable=executable):
        if _context_key(controller_context(scope._session,project=True))!=expected:
            raise RuntimeError('Actor membership world/controller changed before observation')
        selected=(identity(actor)[1:],expected[1][1:])
        catalog=capture_selected(scope.pid,selected)
        actor=catalog.resolve(actor)
        world=catalog.by_index[expected[1][1]]
        _live(actor);_live(world)
        if world.class_name!='World' or identity(world)!=expected[1]:
            raise RuntimeError('Current world identity differs')
        if not any(catalog.path_name(catalog.by_index[index])=='/Script/Engine.Actor'
                   for index in catalog.ancestors(actor.class_index)):
            raise RuntimeError('Selected object is not an actor')
        level=catalog.by_index.get(actor.outer_index)
        if (level is None or level.serial!=actor.outer_serial or level.class_name!='Level' or
                catalog.path_name(catalog.by_index[level.class_index])!='/Script/Engine.Level'):
            raise RuntimeError('Actor has no exact registered outer Level')
        _live(level)
        observed,catalog=_read(catalog,level,{'OwningWorld':'ObjectProperty','bIsVisible':'BoolProperty'})
        owner,visible=observed['OwningWorld'],observed['bIsVisible']
        if owner is None or identity(owner)!=expected[1] or visible is not True:
            raise RuntimeError('Actor level is not visible in the current owning World')
        observed,catalog=_read(catalog,world,{'Levels':'ArrayProperty'})
        levels=_level_ids(observed['Levels'])
        if identity(level) not in levels:
            raise RuntimeError('Actor level is not a current World.Levels member')
        # Re-observe the same identities, not same-name substitutes. Streaming
        # turnover or reparenting during the operation invalidates the snapshot.
        fresh=capture_selected(scope.pid,(*selected,identity(level)[1:]))
        fresh_actor,fresh_level,fresh_world=(fresh.resolve(obj) for obj in (actor,level,world))
        for obj in (fresh_actor,fresh_level,fresh_world):_live(obj)
        if (fresh_actor.outer_index,fresh_actor.outer_serial)!=(level.index,level.serial):
            raise RuntimeError('Actor level changed during membership observation')
        observed,fresh=_read(fresh,fresh_level,{'OwningWorld':'ObjectProperty','bIsVisible':'BoolProperty'})
        if (observed['OwningWorld'] is None or identity(observed['OwningWorld'])!=expected[1] or
                observed['bIsVisible'] is not True):
            raise RuntimeError('Actor level visibility or owning World changed during observation')
        observed,fresh=_read(fresh,fresh_world,{'Levels':'ArrayProperty'})
        if _level_ids(observed['Levels'])!=levels:
            raise RuntimeError('World level membership changed during observation')
        if _context_key(controller_context(scope._session,project=True))!=expected:
            raise RuntimeError('Actor membership world/controller changed during observation')
    scope._check()
    return ActorLevelMembership(identity(actor),identity(level),expected[1],expected[0],True)
