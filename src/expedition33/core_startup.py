"""Read-only admission for the persistent native Session core specimen."""
from . import _query, RuntimeQueryError
from ._reader import ReadBatch
from .catalog import _decode_catalog


def _identity(obj):
    return obj.index, obj.serial, obj.address


def _specimen(catalog):
    actors = tuple(o for o in catalog.objects
        if o.name == 'Default__Actor' and o.class_name == 'Actor'
        and o.object_flags & 0x10 and not o.object_flags & 0x40000000)
    functions = tuple(o for o in catalog.objects
        if o.name == 'IsActorBeingDestroyed' and o.class_name == 'Function'
        and not o.object_flags & 0x40000030)
    if len(actors) != 1:
        return None
    actor = actors[0]
    owner = catalog.by_index[actor.class_index]
    if catalog.path_name(owner) != '/Script/Engine.Actor':
        raise RuntimeQueryError('Core specimen Actor class is outside /Script/Engine')
    functions = tuple(o for o in functions if o.outer_index == owner.index
                      and o.outer_serial == owner.serial)
    if len(functions) != 1:
        return None
    return _identity(actor), _identity(functions[0])


def core_bootstrap_ready(pid):
    """Permit one native attach attempt, without world/GI/controller/save checks.

    Native SessionOpen remains the authority for build, thread, GC, exact getter
    schema and dispatch safety. A true result does not prove a Win32 message
    queue is pumping; GetGUIThreadInfo would not prove that either. Never retry
    an uncertain SessionOpen based on this read-only observation.
    """
    if type(pid) is not int or not 0 < pid <= 0xffffffff:
        raise ValueError('Expected process ID')
    try:
        with ReadBatch(pid):
            start, rows = _query(['--catalog-match', str(pid),
                'n=Default__Actor,n=IsActorBeingDestroyed'])
            if start['pid'] != pid:
                raise RuntimeQueryError('Core startup process mismatch')
            thread = start.get('game_thread_id')
            if type(thread) is not int or not 0 < thread <= 0xffffffff:
                return False
            first = _specimen(_decode_catalog(start, rows))
            if first is None:
                return False
            selectors = ','.join(f'{index}:{serial}:{address:x}' for index,serial,address in first)
            after, rows = _query(['--catalog-select', str(pid), selectors])
            if after['pid'] != pid:
                raise RuntimeQueryError('Core startup process mismatch')
            if after.get('game_thread_id') != thread:
                return False
            return _specimen(_decode_catalog(after, rows)) == first
    except RuntimeQueryError as error:
        if any(reason in str(error) for reason in (
                'MATCH_RESULTS_EMPTY', 'GAME_THREAD_ID_NOT_OWNED_BY_TARGET',
                'REGISTRY_COUNTS_INVALID',
                'Object identity changed or belongs to another process',
                'SELECTED_DEPENDENCY_CHANGED', 'SELECTED_DEPENDENCY_NOT_REGISTERED')):
            return False
        raise
