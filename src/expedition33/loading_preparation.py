"""Owner-thread detached UI preparation; never activates gameplay mods."""
import logging
import time

LOG=logging.getLogger(__name__)

class LoadingPreparation:
    def __init__(self,session,loader):
        self.session=session;self.loader=loader;self.owners={};self.failed=set()

    def observe(self,packet):
        context=getattr(packet,'ui_context',None) or getattr(packet,'prewarm_context',None)
        if context is None:return not self.owners
        # Only modules admitted by their captured startup declaration can opt in.
        # Preference changes at title are sampled before any optional UI work.
        if context.kind=='title':
            views={v['folder']:v for v in self.loader.registry.views()}
            for name in tuple(self.loader._startup_preparations):
                previous=self.owners.get(name)
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
                    owner.prepare(context)
                    elapsed=(time.perf_counter()-started)*1000
                    timings=getattr(self.loader,'_startup_preparation_timings',None)
                    if timings is not None:timings[name]=timings.get(name,0.)+elapsed
                    LOG.info('Loading preparation complete: %s (%.1f ms)',name,elapsed)
                except Exception:
                    self.failed.add(name)
                    LOG.exception('Loading preparation held: %s',name)
        else:
            from .ui_shell_proof import UiProofPending
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
