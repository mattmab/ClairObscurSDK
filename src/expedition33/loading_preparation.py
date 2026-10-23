"""Owner-thread detached UI preparation; never activates gameplay mods."""
import logging
import time
from .ui_shell_proof import UiProofPending

LOG=logging.getLogger(__name__)

def service_loading_io(session):
    """Yield between acknowledged batches on the Session owner thread only."""
    callback=getattr(session,'_loading_ui_pump',None)
    if callback is None or getattr(session,'_loading_ui_pumping',False):return
    now=time.monotonic()
    if now<getattr(session,'_loading_ui_next_pump',0.):return
    session._loading_ui_pumping=True
    try:callback()
    finally:
        session._loading_ui_pumping=False
        session._loading_ui_next_pump=time.monotonic()+.05

class LoadingPreparation:
    def __init__(self,session,loader):
        self.session=session;self.loader=loader;self.owners={};self.failed=set()

    def observe(self,packet,*,pump=None):
        context=getattr(packet,'ui_context',None) or getattr(packet,'prewarm_context',None)
        if context is None:return not self.owners
        # Only modules admitted by their captured startup declaration can opt in.
        # Preference changes at title are sampled before any optional UI work.
        if context.kind=='title' or getattr(packet,'bootstrap_ready',False) is True:
            views={v['folder']:v for v in self.loader.registry.views()}
            for name in tuple(self.loader._startup_preparations):
                from ._reader import active_reader
                reader=active_reader()
                if reader is not None and reader._closed:
                    # A GC/read race closed this operation's shared worker.
                    # Defer untouched owners until the next fresh operation;
                    # never mark their unattempted construction as failed.
                    return True
                previous=self.owners.get(name)
                title_observer=getattr(previous,'observe_title',None)
                if context.kind=='title' and callable(title_observer):
                    try:title_observer(context)
                    except UiProofPending:
                        continue
                    except Exception:
                        self.failed.add(name);LOG.exception('Loading owner retirement held: %s',name)
                        continue
                if previous is not None and getattr(previous,'released',False) is True:
                    previous.close();del self.owners[name]
                if name in self.owners or name in self.failed:continue
                view=views.get(name)
                if view is None or self.loader.registry._settings.get(view['id']).get('enabled') is not True:continue
                loaded=self.loader._loaded.get(name)
                callback=getattr(loaded[1],'prepare_loading_ui',None) if loaded else None
                if not callable(callback):continue
                started=time.perf_counter()
                try:
                    # Callback must return its owner before attempting construction.
                    owner=callback(self.session)
                    self.owners[name]=owner
                    previous=getattr(self.session,'_loading_ui_pump',None)
                    if pump is not None:self.session._loading_ui_pump=pump
                    try:
                        if pump is not None:pump()
                        owner.prepare(context)
                    finally:
                        if pump is not None:self.session._loading_ui_pump=previous
                    elapsed=(time.perf_counter()-started)*1000
                    timings=getattr(self.loader,'_startup_preparation_timings',None)
                    if timings is not None:timings[name]=timings.get(name,0.)+elapsed
                    LOG.info('Loading preparation complete: %s (%.1f ms)',name,elapsed)
                except Exception:
                    self.failed.add(name)
                    LOG.exception('Loading preparation held: %s',name)
        else:
            for name,owner in self.owners.items():
                if name in self.failed:continue
                try:owner.bind(context,preparing=not getattr(getattr(packet,'admission',None),'activation_ready',False))
                except UiProofPending:return False
                except Exception:
                    self.failed.add(name)
                    LOG.exception('Loading UI handoff held: %s',name)
        # An optional preparation failure remains attached to its mod and owner;
        # it must not hold all unrelated saved mods in an endless startup wait.
        return True

    def close(self):
        for owner in reversed(tuple(self.owners.values())):owner.close()
