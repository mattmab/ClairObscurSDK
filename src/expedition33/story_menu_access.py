"""Save-scoped early access to the original cosmetic/game menu."""
from ._scope import SessionScope
from .catalog import capture_matching
from .story_save_identity import StorySaveIdentity
from ._reader import shared_operation

ROOT='/Game/Gameplay/Exploration/BP_ExplorationProgressionSystem.BP_ExplorationProgressionSystem_C:'

class StoryMenuAccess:
    def __init__(self,parent,key,gi):
        self.scope=SessionScope(parent);self.key=key;self.done=False;self.unknown=False
        self.identity=StorySaveIdentity(self.scope);self.planner=None
        with shared_operation(parent.pid):
            prepared=getattr(parent._session,'_story_construction_resources',None)
            names=('IsExplorationCapacityUnlocked','SetExplorationCapacityUnlocked')
            if prepared is not None and all(any(o.name==name for o in prepared.metadata) for name in names):
                from .values import capture_selected_values
                c,values=capture_selected_values(parent.pid,((gi.index,gi.serial,gi.address),),fields=('ExplorationProgressionState',),references=True)
                if values[gi.index].errors or values[gi.index].truncated:raise RuntimeError('Current exploration system observation is incomplete')
                c=c.with_observations(prepared.catalog(self.scope,names))
            else:c=capture_matching(parent.pid,classes=('BP_ExplorationProgressionSystem_C',),names=names)
            targets=[o for o in c.objects if o.class_name=='BP_ExplorationProgressionSystem_C'
                and (o.outer_index,o.outer_serial)==(gi.index,gi.serial) and not o.object_flags&48]
            if len(targets)!=1:raise RuntimeError('One current game-instance exploration system required')
            from .reflection import describe_selected
            functions=tuple(c.find_path(ROOT+name) for name in ('IsExplorationCapacityUnlocked','SetExplorationCapacityUnlocked'))
            c=c.with_observations(describe_selected(parent.pid,tuple((o.index,o.serial,o.address) for o in functions)).catalog)
            self.planner=self.scope.invocation_planner(catalog=c,selected_results=True)
            # Original CanOpenGameMenu checks E_ExplorationCapacity value 4
            # (NewEnumerator4, display name GameMenu). No other capacity changes.
            self.get=self.planner.prepare_blueprint(targets[0],c.find_path(ROOT+'IsExplorationCapacityUnlocked'),Capacity=4)
            self.set=self.planner.prepare_blueprint(targets[0],c.find_path(ROOT+'SetExplorationCapacityUnlocked'),Capacity=4,Unlocked=True)
    def unlock(self):
        if self.done:return
        if self.unknown:raise RuntimeError('Menu unlock outcome uncertain; do not replay')
        with shared_operation(self.scope.pid):
            if self.identity.read()!=self.key:raise RuntimeError('Menu unlock save changed')
            with self.get.invoke() as result:unlocked=result.outputs['IsUnlocked']
            if unlocked is not True:
                self.unknown=True
                with self.set.invoke():pass
                with self.get.invoke() as result:
                    if result.outputs['IsUnlocked'] is not True:raise RuntimeError('Game menu unlock not acknowledged')
                self.unknown=False
            self.done=True
    def close(self):
        if self.unknown:return False
        if self.planner is not None:self.planner.close();self.planner=None
        self.scope.close();return True
