"""Owned dialogue snippets. No music replacement and no fire-and-forget playback."""
import json,time
from functools import lru_cache
from pathlib import Path
from .story_dialogue import identity
from .story_animation import DialogueAnimations

@lru_cache(maxsize=1)
def library():
    return tuple(json.loads(Path(__file__).with_name('story-audio-library.json').read_text(encoding='utf-8'))['clips'])

def choices(query=''):
    words=query.casefold().split()
    return tuple(row for row in library() if all(w in row['path'].casefold() for w in words))

class _Components:
    def __init__(self,owner):self.owner=owner;self._scope=owner.scope;self.closed=False
    def close(self):
        if self.closed:return True
        if self.owner.failed:return False
        for component in self.owner.sounds.values():
            self.owner._call(component,'AudioComponent','Stop')
            self.owner._call(component,'ActorComponent','K2_DestroyComponent',Object=component)
        self.closed=True
        return True

class DialogueAudio:
    _call=DialogueAnimations._call
    _prepare_call=DialogueAnimations._prepare_call
    def __init__(self,scope):
        from ._scope import SessionScope
        self.scope=SessionScope(scope);self.calls={};self.failed=False
        self.sounds={};self.active=None;self.deadline=None
        self.components=_Components(self);self.scope._register_native_owner(self.components)

    @staticmethod
    def key(selection):return (selection['asset'],float(selection['volume']))

    def prepare(self,selection):
        key=self.key(selection)
        if key in self.sounds:
            component=self.sounds[key]
            self._prepare_call(component,'AudioComponent','Play',StartTime=float(selection['start']))
            return component
        if len(self.sounds)>=32:raise ValueError('Use at most 32 distinct audio/volume combinations per prepared conversation')
        from .assets import load_asset
        from .cinematics.controller_anchor import for_scope
        from .catalog import capture_matching,capture_selected
        from .reflection import describe_selected
        source=load_asset(self.scope,selection['asset']).return_value
        if source is None or source.class_name not in ('SoundWave','SoundCue','MetaSoundSource'):
            raise ValueError('Select a game audio sample or cue')
        controller=for_scope(self.scope).context()['controller'][1:]
        catalog=capture_matching(self.scope.pid,names=('Default__GameplayStatics','SpawnSound2D'))
        target=catalog.find_path('/Script/Engine.Default__GameplayStatics')
        function=catalog.find_path('/Script/Engine.GameplayStatics:SpawnSound2D')
        catalog=describe_selected(self.scope.pid,(identity(function),)).catalog.with_observations(catalog)
        catalog=catalog.with_observations(capture_selected(self.scope.pid,(tuple(controller),identity(source))))
        planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
        try:
            prepared=planner.prepare(target,function,WorldContextObject=catalog.by_index[controller[0]],Sound=source,
                VolumeMultiplier=0.,PitchMultiplier=1.,StartTime=0.,ConcurrencySettings=None,
                bPersistAcrossLevelTransition=False,bAutoDestroy=False)
            # Spawn silently for preparation; the retained result is registered
            # for Stop/Destroy before it can be made audible. No music owner.
            self.failed=True
            result=prepared.invoke(fresh_results=True)
            component=result.return_value
            if component is None or component.class_name!='AudioComponent':raise RuntimeError('Audio component did not spawn')
            self.sounds[key]=component;self.failed=False
        finally:planner.close()
        self._call(component,'AudioComponent','Stop')
        self._prepare_call(component,'AudioComponent','Play',StartTime=float(selection['start']))
        self._prepare_call(component,'AudioComponent','SetVolumeMultiplier',NewVolumeMultiplier=float(selection['volume']))
        self._prepare_call(component,'ActorComponent','K2_DestroyComponent',Object=component)
        return component

    def play(self,selection):
        if self.failed:raise RuntimeError('Audio outcome is unknown; close this conversation before retrying')
        component=self.prepare(selection)
        if self.active is not None:self._call(self.active,'AudioComponent','Stop')
        self.active=component;self.deadline=None
        self._call(component,'AudioComponent','SetVolumeMultiplier',NewVolumeMultiplier=float(selection['volume']))
        self._call(component,'AudioComponent','Play',StartTime=float(selection['start']))
        self.deadline=time.monotonic()+selection['duration']

    def poll(self):
        if self.deadline is not None and time.monotonic()>=self.deadline:
            self._call(self.active,'AudioComponent','Stop');self.active=None;self.deadline=None

    def close(self,*,world_retired=False):
        if not world_retired and not self.components.close():return False
        # World retirement is admitted by the caller's world lifecycle. Sounds
        # do not persist across level transitions. Never call purged components.
        if self.components in self.scope._native_owners:self.scope._native_owners.remove(self.components)
        for planner,call in self.calls.values():planner.close()
        self.calls={};self.active=None;self.deadline=None
        from ._retired_tracking import close_lease_only_scope
        return close_lease_only_scope(self.scope)
