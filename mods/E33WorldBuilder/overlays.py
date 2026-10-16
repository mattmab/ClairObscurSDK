"""Camera-free entry point shared with the Map Overlays companion."""
import logging
import time
from expedition33.catalog import capture_matching
from expedition33.values import read_values_with_references


def context(mod):
    with mod.menu_reads():
        c=capture_matching(mod.session.pid,classes=('PlayerController',))
        for pc in c.select('PlayerController'):
            if pc.object_flags & 0x30:continue
            values,c=read_values_with_references(c,pc,fields=('Pawn','bIsLocalPlayerController'))
            values={k[1]:v for k,v in values.values.items()}
            if not values.get('bIsLocalPlayerController'):continue
            pawn=values.get('Pawn')
            if pawn is None:return None
            obj=pawn
            while obj.class_name!='World' and obj.outer_index>=0:obj=c.by_index[obj.outer_index]
            if obj.class_name!='World':return None
            return dict(world=c.path_name(obj),visit=[obj.index,obj.serial,obj.address],
                        ready=pawn.class_name in ('BP_jRPG_Character_World_C','BP_jRPG_Character_WorldMap_pawn_C'))
    return None


def load(mod,map_id,expected,discover):
    started=time.perf_counter()
    current=context(mod)
    if not current or not current['ready'] or current!=expected:
        raise RuntimeError('Game map changed or exploration is not ready')
    data=mod.library.store.read(map_id)
    if data['world']!=current['world']:raise ValueError('Save belongs to a different vanilla map')
    previous=getattr(mod,'_overlay_visit',None)
    if mod.active:raise RuntimeError('Leave the builder camera before automatic map loading')
    if previous and previous!=current['visit']:
        # Retire only the previous world's now-stale tracking and leases.
        mod.restore();mod.library._catalog=None;mod.library.registry_names_ready=False
        mod.library.loader_metadata=[];mod.library.active_map=None
    if mod.started:mod.command(26)
    if mod.library.owned or mod.last.get('edits'):
        raise RuntimeError('Current scene has tracked edits; overlay deferred until a clean map visit')
    with mod.menu_reads():ids=discover(mod.session.pid)
    discovered=time.perf_counter()
    ids[48]=None  # No HUD widget is installed for camera-free ownership.
    mod.started=True
    try:
        mod.command(62,ids=ids)
        mod._overlay_visit=current['visit']
        result=mod.library.load(map_id)
        logging.getLogger(__name__).info('Overlay load timing: prepare_ms=%.1f load_ms=%.1f', (discovered-started)*1000,(time.perf_counter()-discovered)*1000)
        return result
    finally:
        # Keep spawned assets/edits but relinquish native active ownership.
        # Overlay mode never changes the player view or movement mode.
        mod.command(22);mod.active=False
