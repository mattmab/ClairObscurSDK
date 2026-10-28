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
from expedition33._menu_latency import MenuLatency,measure_method
from expedition33._stable_lease import available as stable_leases_available,acquire_stable
from expedition33.catalog import capture, capture_matching, capture_selected
from expedition33.values import read_values, read_values_many, read_object_reference, StoredArray, StoredMap


def one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise ValueError('Ambiguous Prologue adapter dependency')
    return rows[0]


def retain_prepared_dependencies(scope,roots):
    # Assign zero serials under native ownership before unrelated actor/sequence
    # work can promote them. Capture still validates every selector per play.
    stable=stable_leases_available(getattr(scope._session,'_transport',None))
    return tuple(acquire_stable(scope,obj)[0] if obj.serial==0 and stable else scope.retain(obj)
                 for obj in roots)


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


WIDGET_ROUTING_CLASS='/Game/Gameplay/UI/Sequencer/BP_WidgetSequencerTrackInstance.BP_WidgetSequencerTrackInstance_C'


def prepare_widget_routing(scope):
    """Load and retain the routing class without attaching input or audio."""
    from expedition33.picto_class_load import load_class
    routing=load_class(scope,WIDGET_ROUTING_CLASS).return_value
    if routing is None or routing.name!='BP_WidgetSequencerTrackInstance_C':
        raise RuntimeError('Exact cinematic widget routing class unavailable')
    return routing


WIDGET_DEPENDENCY_NAMES = ('BP_CinematicSystem_C', 'Default__GameplayStatics', 'GameplayStatics', 'SpawnObject',
        'GetCinematicsSystem', 'GetComponentByClass', 'Default__FL_jRPG_CustomFunctionLibrary_C',
        'ExecuteUbergraph_BP_WidgetSequencerTrackInstance', 'BP_WidgetSequencerTrackInstance_C',
        'UserWidget', 'Default__UserWidget', 'RegisterSpawnedWidget', 'UnregisterSpawnedWidget',
        'UpdateCinematicControlsWidget', 'RemoveFromParent')

class PreparedWidgetDependencies:
    """Scoped selectors, never a reusable catalog or native ownership token."""
    def __init__(self,scope):
        scope._check()
        self.scope=scope
        catalog=capture_matching(scope.pid,names=WIDGET_DEPENDENCY_NAMES,classes=('BP_jRPG_GI_Custom_C',))
        roots=[one(o for o in catalog.objects if o.name==name) for name in WIDGET_DEPENDENCY_NAMES]
        roots.append(one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.name.startswith('Default__')))
        self.leases=retain_prepared_dependencies(scope,roots)

    def capture(self,scope):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session or not all(lease.active for lease in self.leases):
            raise RuntimeError('Prepared widget dependencies are no longer owned by this SDK session')
        # A selected read checks serial/address and supplies a fresh dependency
        # closure. Do not merge in the preparation snapshot or reuse call plans.
        return capture_selected(scope.pid,tuple((lease.object.index,lease.object.serial,lease.object.address)
                                                for lease in self.leases))


def prepare_widgets(sequence,*,retain_track_class=False,routing_class=None,dependencies=None):
    # Same dependencies and ownership contract as the combined v47 no-play test.
    scope = sequence.scope
    latency = MenuLatency()
    # Full scenes need not reference a title-card track. Retain the exact
    # routing class explicitly instead of relying on a prior title playback.
    if retain_track_class:
        if routing_class is None:routing=prepare_widget_routing(scope)
        else:
            current=capture_selected(scope.pid,((routing_class.index,routing_class.serial,routing_class.address),))
            routing=current.by_index[routing_class.index]
            if current.path_name(routing)!=WIDGET_ROUTING_CLASS or routing.class_name!='BlueprintGeneratedClass':
                raise RuntimeError('Prepared cinematic widget routing class changed')
            scope.retain(routing)
    with latency.measure('widgets.dependencies'):
        catalog = (dependencies.capture(scope) if dependencies is not None else
                   capture_matching(scope.pid,names=WIDGET_DEPENDENCY_NAMES,classes=('BP_jRPG_GI_Custom_C',)))
    cls = one(o for o in catalog.objects if o.name == 'BP_CinematicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
    gi = one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.name.startswith('Default__'))
    default = one(o for o in catalog.objects if o.name == 'Default__GameplayStatics')
    statics = one(o for o in catalog.objects if o.name == 'GameplayStatics' and o.class_name == 'Class')
    spawn = one(o for o in catalog.objects if o.name == 'SpawnObject' and o.outer_index == statics.index)
    planner = scope.invocation_planner(catalog=catalog, selected_results=True)
    with latency.measure('widgets.component_factory'):
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
    with latency.measure('widgets.remove_plan'):
        remove = planner.prepare(named('Default__UserWidget'), resources['remove'])._plan
    owner = NativeCinematicWidgets(scope)
    owner.latency = latency
    owner.prepare(resources, sequence.player, remove)
    return owner


MUSIC_DEPENDENCY_NAMES=('BP_InteractiveMusicSystem_C','Default__GameplayStatics','GameplayStatics','SpawnObject',
 'AudioComponent','ActorComponent','Default__AudioComponent','Stop','K2_DestroyComponent','SetPaused','S_InteractiveMusic')

class PreparedMusicDependencies:
    """Retained selectors only; current GI references and schemas stay per play."""
    def __init__(self,scope):
        scope._check();self.scope=scope
        c=capture_matching(scope.pid,names=MUSIC_DEPENDENCY_NAMES,classes=('BP_jRPG_GI_Custom_C',))
        roots=[one(o for o in c.objects if o.name==name and o.class_name==kind) for name,kind in (
          ('BP_InteractiveMusicSystem_C','BlueprintGeneratedClass'),('GameplayStatics','Class'),
          ('AudioComponent','Class'),('ActorComponent','Class'))]
        statics,audio,component=roots[1:4]
        roots.append(one(o for o in c.objects if o.name=='S_InteractiveMusic'))
        roots.extend(one(o for o in c.objects if o.name==name) for name in ('Default__GameplayStatics','Default__AudioComponent'))
        for owner,name in ((statics,'SpawnObject'),(audio,'Stop'),(audio,'SetPaused'),(component,'K2_DestroyComponent')):
            roots.append(one(o for o in c.objects if o.name==name and o.class_name=='Function' and o.outer_index==owner.index))
        roots.append(one(o for o in c.objects if o.class_name=='BP_jRPG_GI_Custom_C' and not o.name.startswith('Default__')))
        # Discover the GI's property-type selectors during preparation. The
        # descriptors themselves are deliberately not cached: read/assignment
        # planning still describes the current schema on every playback.
        from expedition33.reflection import describe_selected,REFERENCE_KINDS
        gi_class=c.by_index[roots[-1].class_index]
        metadata=describe_selected(scope.pid,((gi_class.index,gi_class.serial,gi_class.address),))
        indices={gi_class.index}
        for descriptor in metadata.descriptors.values():
            indices.update(row['index'] for row in descriptor.owners)
            for prop in descriptor.properties:
                indices.update(prop[kind+'_index'] for kind in REFERENCE_KINDS
                               if prop.get(kind+'_index') is not None)
        known={obj.index for obj in roots}
        roots.extend(metadata.catalog.by_index[index] for index in sorted(indices-known))
        if len(roots)>1024:raise RuntimeError('Prepared music dependency limit exceeded')
        self.leases=retain_prepared_dependencies(scope,roots)

    def capture(self,scope):
        self.scope._check();scope._check()
        if scope._session is not self.scope._session or not all(lease.active for lease in self.leases):
            raise RuntimeError('Prepared music dependencies are no longer owned by this SDK session')
        return capture_selected(scope.pid,tuple((lease.object.index,lease.object.serial,lease.object.address)
                                                for lease in self.leases))


class OwnedSequenceContext:
    """Private music and widget services shared by reviewed owned sequences."""
    def __init__(self, session, panel, *, routing_class=None, widget_dependencies=None, music_dependencies=None):
        self.scope = SessionScope(session)
        self.panel = panel
        self.audio = self.reference = self.sound = self.widgets = None
        self.original = self.gi = self.gi_cls = self.catalog = None
        self.closed = False
        self._close_failed = False
        self._pause_plan = None
        self.routing_class=routing_class
        self.widget_dependencies=widget_dependencies
        self.music_dependencies=music_dependencies

    @measure_method('music.prepare')
    def prepare_music(self):
        if self.reference is not None or self.closed:
            raise RuntimeError('Music adapter already used')
        dependencies=getattr(self,'music_dependencies',None)
        with self.latency.measure('music.dependencies'):
            catalog=(dependencies.capture(self.scope) if dependencies is not None else
                     capture_matching(self.scope.pid,names=MUSIC_DEPENDENCY_NAMES,classes=('BP_jRPG_GI_Custom_C',)))
        if catalog.pid != self.scope.pid:
            raise RuntimeError('Catalog/session mismatch')
        cls = one(o for o in catalog.objects if o.name == 'BP_InteractiveMusicSystem_C' and o.class_name == 'BlueprintGeneratedClass')
        self.gi = one(o for o in catalog.objects if o.class_name == 'BP_jRPG_GI_Custom_C' and not o.name.startswith('Default__'))
        self.gi_cls = catalog.by_index[self.gi.class_index]
        # The GI has additional reflected property constraints beyond this one
        # assignment. Discover that exact descriptor closure, not every UObject.
        if dependencies is None:
            from expedition33.reflection import describe_selected
            metadata=describe_selected(self.scope.pid,((self.gi_cls.index,self.gi_cls.serial,self.gi_cls.address),))
            catalog=catalog.with_observations(metadata.catalog)
        self.original, catalog = read_object_reference(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem', project=True)
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
        values = read_values_many(catalog,(detached,),
            fields=('InteractiveMusicByContext','AudioComponentsToUnspawn'))[detached.index]
        require_empty_container(values, 'InteractiveMusicByContext', StoredMap)
        require_empty_container(values, 'AudioComponentsToUnspawn', StoredArray)
        audio_cls = one(o for o in catalog.objects if o.name == 'AudioComponent' and o.class_name == 'Class')
        component_cls = one(o for o in catalog.objects if o.name == 'ActorComponent' and o.class_name == 'Class')
        audio_default = one(o for o in catalog.objects if o.name == 'Default__AudioComponent')
        stop = one(o for o in catalog.objects if o.name == 'Stop' and o.outer_index == audio_cls.index)
        pause = one(o for o in catalog.objects if o.name == 'SetPaused' and o.outer_index == audio_cls.index)
        destroy = one(o for o in catalog.objects if o.name == 'K2_DestroyComponent' and o.outer_index == component_cls.index)
        # Reuse this scoped planner's AudioComponent metadata. Arming still
        # validates this exact plan natively immediately before the handoff.
        self._pause_plan = planner.prepare(audio_default, pause, bPause=False)._plan
        self.audio = NativeMusicAudioOwner(self.scope)
        self.audio.prepare(self.original, detached, audio_cls, planner.prepare(audio_default, stop)._plan,
                           planner.prepare(audio_default, destroy, Object=audio_default)._plan)
        self.reference = NativeScopedAssignment(self.scope)
        self.reference.open(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem', self.original, detached)
        current, self.catalog = read_object_reference(catalog, self.gi, self.gi_cls, 'InteractiveMusicSystem', project=True)
        if current is None or (current.index, current.serial, current.address) != (detached.index, detached.serial, detached.address):
            raise RuntimeError('Private music reference was not confirmed')

    def _arm_title(self, sequence):
        if self.audio is None or self.widgets is not None or self.sound is not None or self.closed:
            raise RuntimeError('Prepare the private music adapter first')
        self._retirement_sequence_owner = sequence.owner
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

    def _title_status(self):
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

    def arm(self, sequence):
        if self.audio is None or self.widgets is not None or self.closed or self._pause_plan is None:
            raise RuntimeError('Prepare the private music adapter first')
        self._retirement_sequence_owner=sequence.owner
        routing=getattr(self,'routing_class',None)
        options={'routing_class':routing} if routing is not None else {}
        dependencies=getattr(self,'widget_dependencies',None)
        if dependencies is not None:options['dependencies']=dependencies
        self.widgets=prepare_widgets(sequence,retain_track_class=True,**options)
        if self.audio.pause_original_audio(self._pause_plan) is not True:
            raise RuntimeError('Original audio pause was not acknowledged')

    def status(self):
        result=dict(widgets=self.widgets.status() if self.widgets else None,
                    audio=self.audio.status() if self.audio else None,
                    reference=self.reference.status() if self.reference else None)
        if not self.closed:
            if self.widgets is not None and (result['widgets']['state']!='armed' or result['widgets']['failed']):
                raise RuntimeError('Cinematic widget ownership is no longer armed')
            if self.audio is not None and result['audio']!='armed':raise RuntimeError('Audio ownership is no longer armed')
            if self.reference is not None and result['reference']!='armed':raise RuntimeError('Music reference ownership is no longer armed')
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

    def retire_world(self):
        """Sequence retirement already removed routes; never compensate here."""
        if self.closed:return True
        from .retirement import retire_owner_tracking
        receipt=getattr(self,'_retirement_sequence_owner',None)
        if self.widgets is not None or self.sound is not None:
            if receipt is None or getattr(receipt,'_retirement_ack',False) is not True:
                raise RuntimeError('Title routes require an acknowledged parent sequence retirement')
            from expedition33._cinematic_sound_event import NativeCinematicSoundEvent
            if self.sound is not None:
                if type(self.sound) is not NativeCinematicSoundEvent or self.sound.scope is not self.scope:
                    raise RuntimeError('Unrelated cinematic sound owner')
                self.sound.state='closed'
        if self.audio is not None and not self.audio.retire_world():return False
        # The exact audio owner ACK includes compare-and-restore of its private
        # GI assignment; no stale reference query or normal compensation here.
        if self.reference is not None:
            if type(self.reference) is not NativeScopedAssignment or self.reference.scope is not self.scope:
                raise RuntimeError('Unrelated cinematic reference owner')
            self.reference.state='closed'
        if not retire_owner_tracking(self.scope,(self.widgets,self.sound,self.audio,self.reference)):
            return False
        self.closed=True
        return True


class OwnedTitleAdapters(OwnedSequenceContext):
    def __init__(self, session, panel, *, profile=PROLOGUE):
        if TITLE_PROFILES.get(profile.definition) is not profile or not profile.available(session._session._transport):
            raise RuntimeError('An exact natively admitted title profile is required')
        super().__init__(session,panel)
        self.profile=profile

    def arm(self,sequence):return self._arm_title(sequence)
    def status(self):return self._title_status()

# Compatibility name: existing callers retain the reviewed Prologue default.
PrologueAdapters = OwnedTitleAdapters

