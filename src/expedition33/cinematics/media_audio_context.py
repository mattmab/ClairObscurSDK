"""Existing native audio ownership without replacing the game's music reference.

Media tracks are driven through owned explicit components; no interactive-music
Blueprint event needs to resolve a private GameInstance system for this category.
"""
from expedition33._scope import SessionScope
from expedition33._music_audio_owner import NativeMusicAudioOwner
from expedition33.catalog import capture
from expedition33.values import read_values,read_object_reference,StoredMap,StoredArray
from .title_adapters import one,require_empty_container

class MediaAudioContext:
    def __init__(self,session,panel):
        transport=session._session._transport
        for name in ('music_audio_protocol','owned_sound_protocol','original_audio_pause_protocol','owned_audio_cleanup_protocol'):
            if type(getattr(transport,name,0)) is not int or getattr(transport,name,0)!=1:
                raise RuntimeError('Verified native isolated audio ownership required')
        self.scope=SessionScope(session);self.panel=panel
        self.audio=self.original=self.gi=self.gi_cls=self.catalog=self.planner=None
        self.closed=False

    def prepare(self):
        if self.audio is not None or self.closed:
            raise RuntimeError('Music adapter already used')
        catalog = capture()
        if catalog.pid != self.scope.pid:
            raise RuntimeError('Catalog/session mismatch')
        cls = one(o for o in catalog.objects if o.name == 'BP_InteractiveMusicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
        self.gi = one(o for o in catalog.objects if o.class_name == 'BP_jRPG_GI_Custom_C' and not o.name.startswith('Default__'))
        self.gi_cls = catalog.by_index[self.gi.class_index]
        self.original, catalog = read_object_reference(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem')
        if self.original is None:
            raise RuntimeError('Original music identity unavailable')
        planner = self.scope.invocation_planner(catalog=catalog, selected_results=True)
        default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
        statics = one(o for o in catalog.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
        spawn = one(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == statics.index)
        detached = planner.prepare(default, spawn, ObjectClass=cls, Outer=self.gi).invoke(refresh_from_result=True).return_value
        catalog = planner._catalog
        if detached is None or detached.class_index != cls.index or detached.outer_index != self.gi.index:
            raise RuntimeError('Detached music ownership mismatch')
        values = read_values(catalog, detached)
        require_empty_container(values, 'InteractiveMusicByContext', StoredMap)
        require_empty_container(values, 'AudioComponentsToUnspawn', StoredArray)
        audio_cls = one(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
        component_cls = one(o for o in catalog.objects if o.name == 'ActorComponent' and o.class_name == 'Class')
        audio_default = one(o for o in catalog.objects if o.name == 'Default__AudioComponent')
        stop = one(o for o in catalog.objects if o.name == 'Stop' and o.outer_index == audio_cls.index)
        destroy = one(o for o in catalog.objects if o.name == 'K2_DestroyComponent' and o.outer_index == component_cls.index)
        self.audio = NativeMusicAudioOwner(self.scope)
        self.audio.prepare(self.original, detached, audio_cls, planner.prepare(audio_default, stop)._plan,
                           planner.prepare(audio_default, destroy, Object=audio_default)._plan)
        self.catalog=planner._catalog
        self.planner=planner
        return self

    def pause_original(self):
        if self.audio is None or self.closed:raise RuntimeError('Prepare private audio first')
        catalog=self.planner._catalog
        cls=one(o for o in catalog.objects if o.name=='AudioComponent' and o.class_name=='Class')
        default=one(o for o in catalog.objects if o.name=='Default__AudioComponent')
        function=one(o for o in catalog.objects if o.outer_index==cls.index and o.name=='SetPaused')
        return self.audio.pause_original_audio(self.planner.prepare(default,function,bPause=False)._plan)

    def close(self):
        if self.closed:return True
        if self.audio is not None and not self.audio.close():return False
        self.scope.close();self.closed=True
        return True

    def retire_world(self):
        if self.closed:return True
        from .retirement import retire_owner_tracking
        if self.audio is not None and not self.audio.retire_world():return False
        if not retire_owner_tracking(self.scope,(self.audio,)):return False
        if self.planner is not None:self.planner.close()
        self.closed=True
        return True
