"""Read-only startup gate: saved gameplay mods need a possessed exploration pawn."""
from types import SimpleNamespace
from ._reader import ReadBatch
from .catalog import capture_selected
from .values import read_values, read_values_many, read_object_reference
from .cinematics.original_game_action import controller_context
from .cinematics.history import anchor, identity


def menu_availability(pid):
    """Readiness tri-state; a transient read is not evidence of retirement."""
    from . import RuntimeQueryError
    from .cinematics.original_game_action import NotReady
    try:
        return menu_ready(pid)
    except NotReady:
        return None
    except RuntimeQueryError as error:
        if any(message in str(error) for message in (
                'Object identity changed or belongs to another process',
                'Object property reference changed during observation', 'READ_FAILED')):
            return None
        raise


def bootstrap_ready(pid):
    """Observe a coherent engine/viewport/world/GI chain without requiring a save.

    This only admits attempting the native Session handshake. It grants no
    gameplay, widget-construction, console or engine-mutation capability.
    Each capture/anchor performs new native reads, even when the reader worker
    is borrowed. It is a bounded double observation, not an atomic GC snapshot.
    """
    from .catalog import capture_matching
    not_ready = ('Current history context reference is null',
                 'Current history context is ambiguous or unavailable',
                 'Active world has no verified game instance',
                 'Object identity changed or belongs to another process')
    try:
        # Default share=False can borrow an existing share=True reader. A nested
        # share=True owner is forbidden; the worker does not cache observations.
        with ReadBatch(pid):
            before_catalog = capture_matching(pid, classes=('GameEngine',))
            if before_catalog.pid != pid:
                raise RuntimeError('Bootstrap catalog process mismatch')
            before, _ = anchor(before_catalog, project=True)
            after_catalog = capture_matching(pid, classes=('GameEngine',))
            if after_catalog.pid != pid:
                raise RuntimeError('Bootstrap catalog process mismatch')
            after, _ = anchor(after_catalog, project=True)
            return tuple(map(identity, before)) == tuple(map(identity, after))
    except RuntimeError as error:
        if str(error) in not_ready:
            return False
        raise


def attachment_ready(pid):
    """A pause widget alone can exist during map loading; do not attach then."""
    return gameplay_ready(pid) and menu_ready(pid)


def menu_ready(pid):
    """The core UI needs the live controller's pause widget, not a pawn."""
    with ReadBatch(pid, share=True):
        context = controller_context(SimpleNamespace(pid=pid), project=True)
        catalog = capture_selected(pid, (context['controller'][1:],))
        controller = catalog.by_index[context['controller'][1]]
        values = read_values_many(catalog, (controller,),
            fields=('PauseMenuWidget',))[controller.index]
        owners = [owner for owner, name in values.types if name == 'PauseMenuWidget']
        if len(owners) != 1:
            return False
        pause, _ = read_object_reference(catalog, controller,
            catalog.by_index[owners[0]], 'PauseMenuWidget', project=True)
        return pause is not None and pause.class_name == 'WBP_PauseMenu_C'


def gameplay_ready(pid):
    with ReadBatch(pid, share=True):
        context = controller_context(SimpleNamespace(pid=pid))
        catalog = capture_selected(pid, (context['controller'][1:],))
        controller = catalog.by_index[context['controller'][1]]
        values = read_values(catalog, controller)
        owners = [owner for owner, name in values.types if name == 'Pawn']
        if len(owners) != 1:
            return False
        # Selected controller metadata need not contain its current Pawn. Read
        # and validate that live reference into a fresh closure explicitly.
        pawn, _ = read_object_reference(catalog, controller, catalog.by_index[owners[0]], 'Pawn')
        return (pawn is not None and pawn.class_name in
                ('BP_jRPG_Character_WorldMap_pawn_C', 'BP_jRPG_Character_World_C',
                 'BP_WorldMapCharacter_C'))
