"""Build-specific exact Prologue adapters extracted from verified no-play probes.

No research scripts, subprocesses, arbitrary hooks, or save writes are used.
Read-only catalog/property observation uses the configured SDK reader.
"""
from expedition33._scope import SessionScope
from expedition33.cinematics.title_profiles import PROLOGUE, TITLE_PROFILES
from expedition33._scoped_assignment import NativeScopedAssignment
from expedition33._music_audio_owner import NativeMusicAudioOwner
from expedition33._cinematic_sound_event import NativeCinematicSoundEvent
from expedition33._cinematic_widget import NativeCinematicWidgets
from expedition33.catalog import capture, capture_matching
from expedition33.values import read_values, read_object_reference, StoredArray, StoredMap


def one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise ValueError('Ambiguous Prologue adapter dependency')
    return rows[0]


def require_empty_container(values, name, expected_type):
    """Require a complete typed empty observation; errors never mean empty."""
    keys = [key for key in values.types if key[1] == name]
    if len(keys) != 1:
        raise RuntimeError(f'Detached music container absent or ambiguous: {name}')
    key = keys[0]
    value = values.values.get(key)
    details = dict(property_type=values.types[key], decoded_type=type(value).__name__,
                   error=values.errors.get(key), truncated=key in values.truncated)
    if isinstance(value, StoredArray):
        details.update(length=value.length, copied_count=len(value.items))
    elif isinstance(value, StoredMap):
        details['count'] = len(value.items)
    correct_property = 'MapProperty' if expected_type is StoredMap else 'ArrayProperty'
    if (values.types[key] != correct_property or key in values.errors or key in values.truncated or
            not isinstance(value, expected_type) or value.items or
            (isinstance(value, StoredArray) and value.length != 0)):
        raise RuntimeError(f'Detached music container not verified empty: {name}; {details!r}')


def prepare_widgets(sequence):
    # Same dependencies and ownership contract as the combined v47 no-play test.
    scope = sequence.scope
    names = ('BP_CinematicSystem_C', 'Default__GameplayStatics', 'GameplayStatics', 'SpawnObject',
        'GetCinematicsSystem', 'GetComponentByClass', 'Default__FL_jRPG_CustomFunctionLibrary_C',
        'ExecuteUbergraph_BP_WidgetSequencerTrackInstance', 'BP_WidgetSequencerTrackInstance_C',
        'UserWidget', 'Default__UserWidget', 'RegisterSpawnedWidget', 'UnregisterSpawnedWidget',
        'UpdateCinematicControlsWidget', 'RemoveFromParent')
    catalog = capture_matching(scope.pid, names=names, classes=('BP_jRPG_GI_Custom_C',))
    cls = one(o for o in catalog.objects if o.name == 'BP_CinematicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
    gi = one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.name.startswith('Default__'))
    default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
    statics = one(o for o in catalog.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
    spawn = one(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == statics.index)
    planner = scope.invocation_planner(catalog=catalog, selected_results=True)
    component = planner.prepare(default, spawn, ObjectClass=cls, Outer=gi).invoke(refresh_from_result=True).return_value
    if component is None or component.class_index != cls.index or component.outer_index != gi.index:
        raise RuntimeError('Private cinematic component factory mismatch')
    def named(name):
        return one(o for o in planner._catalog.objects if o.name == name)
    resources = dict(getter=named('GetCinematicsSystem'), native_getter=named('GetComponentByClass'),
        library=named('Default__FL_jRPG_CustomFunctionLibrary_C'), component=component,
        graph=named('ExecuteUbergraph_BP_WidgetSequencerTrackInstance'),
        track_class=named('BP_WidgetSequencerTrackInstance_C'), widget_class=named('UserWidget'),
        register=named('RegisterSpawnedWidget'), unregister=named('UnregisterSpawnedWidget'),
        controls=named('UpdateCinematicControlsWidget'), remove=named('RemoveFromParent'))
    remove = planner.prepare(named('Default__UserWidget'), resources['remove'])._plan
    owner = NativeCinematicWidgets(scope)
    owner.prepare(resources, sequence.player, remove)
    return owner


class OwnedTitleAdapters:
    def __init__(self, session, panel, *, profile=PROLOGUE):
        if TITLE_PROFILES.get(profile.definition) is not profile or not profile.available(session._session._transport):
            raise RuntimeError('An exact natively admitted title profile is required')
        self.profile=profile
        self.scope = SessionScope(session)
        self.panel = panel
        self.audio = self.reference = self.sound = self.widgets = None
        self.original = self.gi = self.gi_cls = self.catalog = None
        self.closed = False
        self._close_failed = False

    def prepare_music(self):
        if self.reference is not None or self.closed:
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
        self.reference = NativeScopedAssignment(self.scope)
        self.reference.open(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem', self.original, detached)
        current, self.catalog = read_object_reference(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem')
        if current is None or (current.index, current.serial, current.address) != (detached.index, detached.serial, detached.address):
            raise RuntimeError('Private music reference was not confirmed')

    def arm(self, sequence):
        if self.audio is None or self.widgets is not None or self.sound is not None or self.closed:
            raise RuntimeError('Prepare the private music adapter first')
        self.widgets = prepare_widgets(sequence)
        catalog = capture()
        if catalog.pid != self.scope.pid:
            raise RuntimeError('Catalog/session mismatch')
        planner = self.scope.invocation_planner(catalog=catalog, selected_results=True)
        cls = one(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
        default = one(o for o in catalog.objects if o.name == 'Default__AudioComponent')
        pause = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'SetPaused')
        if self.profile.sound_mode == 'single_owned_sound':
            sound = one(o for o in catalog.objects if o.name == self.profile.sound_wave and o.class_name == 'SoundWave')
            director = one(o for o in catalog.objects if o.name == self.profile.director and o.class_name == 'BlueprintGeneratedClass')
            event = one(o for o in catalog.objects if o.outer_index == director.index and o.name == 'SequenceEvent')
            component = self.audio.create_sound(planner, self.panel, sound)
            play = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == 'Play')
            self.sound = NativeCinematicSoundEvent(self.scope)
            self.sound.prepare(event, sequence.player, sound, planner.prepare(component, play, StartTime=0.0)._plan)
        elif self.profile.sound_mode == 'none_verified_empty':
            director = one(o for o in catalog.objects if o.name == self.profile.director and o.class_name == 'BlueprintGeneratedClass')
            event = one(o for o in catalog.objects if o.outer_index == director.index and o.name == 'SequenceEvent')
            self.sound = NativeCinematicSoundEvent(self.scope)
            self.sound.prepare_empty(event, sequence.player)
        else:
            raise RuntimeError('Unsupported title sound ownership mode')
        # Empty-channel admission is revalidated by the native sequence owner
        # before Play; it grants no arbitrary event-dispatch bypass.
        self.audio.pause_original_audio(planner.prepare(default, pause, bPause=False)._plan)

    def status(self):
        result = dict(profile_id=self.profile.profile_id, sound_mode=self.profile.sound_mode, widgets=self.widgets.status() if self.widgets else None,
                      sound=self.sound.status() if self.sound else None,
                      audio=self.audio.status() if self.audio else None,
                      reference=self.reference.status() if self.reference else None)
        if (self.sound is not None and result['sound']['state'] == 'armed' and
                getattr(self.scope._session._transport, 'cinematic_sound_diagnostics_protocol', 0) == 1):
            result['sound_routes'] = self.sound.diagnostics()
            if result['sound_routes']['failures']:
                raise RuntimeError('Sound route failure observed')
        if (self.widgets is not None and result['widgets']['state'] == 'armed' and
                getattr(self.scope._session._transport, 'cinematic_widget_diagnostics_protocol', 0) == 1):
            result['widget_routes'] = self.widgets.diagnostics()
            if result['widget_routes']['route_failures']:
                raise RuntimeError('Widget route failure observed')
        if not self.closed:
            for key in ('widgets', 'sound'):
                if result[key] is not None and (result[key]['state'] != 'armed' or result[key]['failed']):
                    raise RuntimeError(f'{key} ownership is no longer armed')
            if self.audio is not None and result['audio'] != 'armed':
                raise RuntimeError('Audio ownership is no longer armed')
            if self.reference is not None and result['reference'] != 'armed':
                raise RuntimeError('Music reference ownership is no longer armed')
        return result

    def close(self):
        if self.closed:
            return
        if self._close_failed:
            raise RuntimeError('Adapter scope cleanup failed; native controller teardown must resolve it')
        # Caller must close the sequence first. Its native cleanup restores all
        # hooks/audio/reference before these retained input identities release.
        try:
            self.scope.close()
        except BaseException:
            self._close_failed = True
            raise
        self.closed = True


# Compatibility name: existing callers retain the reviewed Prologue default.
PrologueAdapters = OwnedTitleAdapters

