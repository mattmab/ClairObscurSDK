"""Read-only startup gate: saved gameplay mods need a possessed exploration pawn."""
from types import SimpleNamespace
from ._reader import ReadBatch
from .catalog import capture_selected
from .values import read_values, read_object_reference
from .cinematics.original_game_action import controller_context


def attachment_ready(pid):
    """A pause widget alone can exist during map loading; do not attach then."""
    return gameplay_ready(pid) and menu_ready(pid)


def menu_ready(pid):
    """The core UI needs the live controller's pause widget, not a pawn."""
    with ReadBatch(pid, share=True):
        context = controller_context(SimpleNamespace(pid=pid))
        catalog = capture_selected(pid, (context['controller'][1:],))
        controller = catalog.by_index[context['controller'][1]]
        values = read_values(catalog, controller)
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
