"""Exclusive transfer of an idle primary encounter channel; no native reset."""
from ._enemy_spawn_owner import EnemySpawnOwner

class StoryEncounterChannel:
    def __init__(self,scope):
        self.scope=scope;self.transport=scope._session._transport;self.previous=None;self.owner=None;self.closed=False
    def acquire(self):
        self.scope._check()
        if self.owner is not None:return self.owner
        previous=getattr(self.transport,'_enemy_spawn_owner',None)
        if previous is not None and (previous.has_native_work or previous._closed or previous.phase!='ready'):
            raise RuntimeError('Finish and retire the existing encounter before the story trial')
        if getattr(self.transport,'_story_encounter_channel',None) is not None:raise RuntimeError('Another story encounter owns this channel')
        # Constructors below only reserve a Python identity; no native command
        # is dispatched. Preserve the dormant owner, including its scope.
        self.previous=previous;self.transport._story_encounter_channel=self
        self.transport._enemy_spawn_owner=None
        try:self.owner=EnemySpawnOwner(self.scope)
        except BaseException:
            self.transport._enemy_spawn_owner=previous;self.transport._story_encounter_channel=None;raise
        return self.owner
    def close(self):
        if self.closed:return True
        if self.owner is not None and not self.owner.close():return False
        if getattr(self.transport,'_story_encounter_channel',None) is not self:raise RuntimeError('Story encounter reservation changed')
        if getattr(self.transport,'_enemy_spawn_owner',None) is not None:raise RuntimeError('Encounter owner did not acknowledge release')
        self.transport._enemy_spawn_owner=self.previous if self.previous is not None and not self.previous._closed else None
        self.transport._story_encounter_channel=None
        self.closed=True;return True
