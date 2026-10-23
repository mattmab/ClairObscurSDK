"""Copied passive map context; no Session or mutations enter the read worker."""
from dataclasses import dataclass
from types import SimpleNamespace
from expedition33.map_runtime import context

@dataclass(frozen=True)
class MapContext:
    world: str
    visit: tuple
    pawn: tuple
    ready: bool

    def copy(self):
        return dict(world=self.world,visit=list(self.visit),pawn=list(self.pawn),ready=self.ready)

class ContextObserver:
    def __init__(self,pid):
        self._target=SimpleNamespace(pid=pid)

    def observe(self):
        value=context(self._target)
        if value is None:return None
        return MapContext(value['world'],tuple(value['visit']),tuple(value['pawn']),value['ready'])

    def close(self):
        # context() bounds and closes its own ReadBatch on this worker thread.
        pass
