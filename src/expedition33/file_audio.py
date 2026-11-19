"""Owned local WAV decoding through Unreal's MediaSoundComponent and VO mixer.

The invisible disposable carrier uses the existing native actor journal, which
destroys its registered sound component on controller loss or world retirement.
No SDK menu or Windows helper-process audio is involved.
"""
import math,time,wave
from pathlib import Path
from .catalog import capture_matching,capture_selected
from ._reader import shared_operation
from .story_dialogue import identity
from .reflection import describe_selected
from .story_facial import DialogueFacialPerformance as Calls
from .cinematics.blueprint_actor import BlueprintActor

MEDIA='/Script/MediaAssets.MediaPlayer:'
SOUND='/Script/MediaAssets.MediaSoundComponent:'
SYNTH='/Script/AudioMixer.SynthComponent:'
VOICE='/Game/Audio/01_SoundClass/SoundClass_Vo.SoundClass_Vo'
MEDIA_OBJECTS=('/Script/Engine.CameraActor','/Script/MediaAssets.MediaPlayer',
    '/Script/MediaAssets.FileMediaSource','/Script/MediaAssets.MediaSoundComponent',
    '/Script/AudioMixer.SynthComponent','/Script/Engine.Default__GameplayStatics',VOICE)
MEDIA_FUNCTIONS=('/Script/Engine.GameplayStatics:SpawnObject',SOUND+'SetMediaPlayer',
    SYNTH+'SetVolumeMultiplier',SYNTH+'Stop',SYNTH+'Start',
    '/Script/MediaAssets.FileMediaSource:SetFilePath',
    *(MEDIA+name for name in ('Close','OpenSource','IsReady','IsPlaying','IsPaused','Pause','Play')))


class _FileAudioMetadata:
    """Process-owned audio types/functions; never an actor or playback value."""
    def __init__(self,resources):
        self.resources=resources;self.scope=resources.scope;self.session=self.scope._session
        self.ready=False;self.paths=frozenset(MEDIA_FUNCTIONS);self.objects={};self.observations=None
    def prepare(self):
        self.scope._check()
        self.resources.load(VOICE)
        paths=MEDIA_OBJECTS+MEDIA_FUNCTIONS
        names=tuple(dict.fromkeys(path.rsplit(':',1)[-1].rsplit('.',1)[-1] for path in paths))
        found=capture_matching(self.scope.pid,names=names)
        for path in paths:self.objects[path]=self.resources.hold(found.find_path(path)).object
        functions=tuple(self.objects[path] for path in MEDIA_FUNCTIONS)
        snapshot=describe_selected(self.scope.pid,tuple(identity(obj) for obj in functions))
        from .story_performance_preflight import _pod_closure
        catalog,descriptors=_pod_closure(self.scope.pid,snapshot)
        with self.scope.invocation_planner(catalog=catalog,selected_results=True) as planner:
            planner._metadata.read('struct',catalog,tuple(d.object for d in descriptors.values()),
                lambda catalog,objects:descriptors)
            self.observations=planner.observations()
        self.ready=True
    def _check(self,scope):
        scope._check();self.scope._check()
        if not self.ready or scope._session is not self.session:
            raise RuntimeError('File audio metadata is unavailable or belongs to another session')
    def catalog(self,scope,paths):
        self._check(scope)
        if not paths or any(path not in self.objects for path in paths):raise ValueError('Exact prepared file audio selectors required')
        return capture_selected(scope.pid,tuple(identity(self.objects[path]) for path in paths))
    def planner(self,scope,objects):
        self._check(scope)
        planner=scope.invocation_planner(observations=self.observations,selected_results=True)
        try:planner.adopt_observations(capture_selected(scope.pid,tuple(dict.fromkeys(identity(o) for o in objects))))
        except BaseException:planner.close();raise
        return planner


def warm_file_audio(resources):
    """Warm exact media metadata at title; partial acquisition is never replayed."""
    session=resources.scope._session;session._check();resources.scope._check()
    previous=getattr(session,'_file_audio_preparation',None)
    if previous is not None:
        if previous.resources is not resources or not previous.ready:
            raise RuntimeError('File audio metadata preparation is incomplete or changed; not replayed')
        previous._check(resources.scope)
        return previous
    owner=_FileAudioMetadata(resources)
    session._file_audio_preparation=owner
    with shared_operation(session.pid):owner.prepare()
    session._file_audio_metadata=owner
    return owner

def wav_file(path):
    path=Path(path).resolve(strict=True)
    if path.suffix.lower()!='.wav' or path.stat().st_size>4*1024*1024:raise ValueError('Bounded WAV file required')
    with wave.open(str(path),'rb') as f:
        rate,frames=f.getframerate(),f.getnframes()
        if f.getsampwidth()!=2 or f.getnchannels() not in (1,2) or not 8000<=rate<=48000 or not 0<frames<=rate*120:
            raise ValueError('PCM16 WAV up to 120 seconds required')
        if len(f.readframes(frames))!=frames*f.getnchannels()*2:raise ValueError('Truncated WAV')
    return path.as_posix(),frames/rate

class OwnedFileAudio:
    _call=Calls._call
    _void=Calls._void
    _values=Calls._values
    _hold=Calls._hold
    _set_scalar=Calls._set_scalar
    def __init__(self,parent,*,volume=1.):
        if type(volume) not in (int,float) or not math.isfinite(volume) or not 0<=volume<=4:raise ValueError('File audio gain must be between zero and four')
        parent._check();self._scope=parent;self.carrier=BlueprintActor(parent);self.scope=self.carrier.scope
        self.volume=float(volume)
        self.calls={};self.planners=[];self.unknown=False;self.closed=False;self.prepared=False
        self.player=None;self.source=None;self.component=None;self.playing=False;self.paused=False;self.started=None
        self.path=None;self.duration=None;self.last_status=None;self.next_poll=0.;self.ready=False
        self._preparation=None
        parent._register_native_owner(self);parent._close_before_descendants(self)
    @property
    def _closed(self):return self.closed
    def _prepare_call(self,obj,path,**arguments):
        key=(identity(obj),path)
        metadata=getattr(getattr(self.scope,'_session',None),'_file_audio_metadata',None)
        if key in self.calls or metadata is None or path not in metadata.paths:
            return Calls._prepare_call(self,obj,path,**arguments)
        metadata._check(self.scope)
        objects=(obj,)+tuple(value for value in arguments.values() if hasattr(value,'class_index'))
        cached=getattr(self,'_audio_call_planner',None)
        if cached is None:
            planner=metadata.planner(self.scope,objects)
            self.planners.append(planner);self._audio_call_planner=(metadata,planner)
        else:
            if cached[0] is not metadata:raise RuntimeError('File audio metadata changed during preparation')
            # A fresh observation revokes a planner's existing calls. Clone
            # retained schema observations before adding this target, keeping
            # earlier setup/cleanup calls usable in their original generation.
            planner=self.scope.invocation_planner(observations=cached[1].observations(),selected_results=True)
            try:planner.adopt_observations(capture_selected(self.scope.pid,tuple(dict.fromkeys(identity(o) for o in objects))))
            except BaseException:planner.close();raise
            self.planners.append(planner);self._audio_call_planner=(metadata,planner)
        catalog=planner._catalog
        call=planner.prepare(catalog.by_index[obj.index],catalog.find_path(path),**arguments)
        self.calls[key]=call
        return call
    def prepare(self):
        while not self.prepare_step():pass
    def prepare_step(self):
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            if self.closed or self.unknown:raise RuntimeError('File audio owner unavailable')
            if self.prepared:return True
            if getattr(self,'_preparation',None) is None:self._preparation=self._prepare_steps()
            try:next(self._preparation)
            except StopIteration:self._preparation=None
            except BaseException:
                self._preparation=None;raise
            return self.prepared
    def _prepare_steps(self):
        if self.closed or self.unknown:raise RuntimeError('File audio owner unavailable')
        if self.prepared:return
        # Reviewed empty carrier profile; never revealed or made a view target.
        if self.carrier.state=='new':self.carrier.prepare_camera((0.,0.,0.,1.,0.,0.,0.,0.,1.,1.,1.,0.))
        if self.carrier.state!='prepared':raise RuntimeError('Owned audio carrier is not prepared')
        yield
        actor=capture_selected(self.scope.pid,(self.carrier.identity,)).by_index[self.carrier.identity[0]]
        metadata=getattr(self.scope._session,'_file_audio_metadata',None)
        c=(metadata.catalog(self.scope,MEDIA_OBJECTS) if metadata is not None else
            capture_matching(self.scope.pid,names=('MediaPlayer','FileMediaSource','MediaSoundComponent','SynthComponent','Default__GameplayStatics','SoundClass_Vo')))
        if self.player is None:
            with self._call(c.find_path('/Script/Engine.Default__GameplayStatics'),'/Script/Engine.GameplayStatics:SpawnObject',
                    ObjectClass=c.find_path('/Script/MediaAssets.MediaPlayer'),Outer=actor) as result:
                if result.return_value is None:raise RuntimeError('Media player construction failed')
                self.player=self._hold(result.return_value)
        if self.player.class_name!='MediaPlayer' or self.player.outer_index!=actor.index:raise RuntimeError('Unexpected media owner')
        yield
        if self.source is None:
            with self._call(c.find_path('/Script/Engine.Default__GameplayStatics'),'/Script/Engine.GameplayStatics:SpawnObject',
                    ObjectClass=c.find_path('/Script/MediaAssets.FileMediaSource'),Outer=actor) as result:
                if result.return_value is None:raise RuntimeError('File media source construction failed')
                self.source=self._hold(result.return_value)
        if self.source.class_name!='FileMediaSource' or self.source.outer_index!=actor.index:raise RuntimeError('Unexpected file media owner')
        yield
        if self.component is None:
            root=self._values(actor,('RootComponent',))['RootComponent']
            with self._call(root,'/Script/Engine.SceneComponent:GetRelativeTransform') as result:relative=result.return_value
            with self._call(actor,'/Script/Engine.Actor:AddComponentByClass',Class=c.find_path('/Script/MediaAssets.MediaSoundComponent'),
                    bManualAttachment=True,RelativeTransform=relative,bDeferredFinish=False) as result:
                if result.return_value is None:raise RuntimeError('Media sound component construction failed')
                self.component=self._hold(result.return_value)
        if self.component.class_name!='MediaSoundComponent' or self.component.outer_index!=actor.index:
            raise RuntimeError('Media sound component belongs to another actor')
        yield
        self._prepare_flags()
        yield
        voice=self._hold(c.find_path(VOICE));old=self._values(self.component,('SoundClass',))['SoundClass']
        if identity(old)!=identity(voice):
            owner=c.find_path('/Script/AudioMixer.SynthComponent')
            ids=[identity(x) for x in (self.component,owner,voice,old) if x is not None]
            # Assignment describes every field declared by SynthComponent;
            # include its reflected dependency closure, not just object refs.
            observed=describe_selected(self.scope.pid,(identity(owner),)).catalog.with_observations(capture_selected(self.scope.pid,ids))
            self.unknown=True
            try:self.scope.assign_object(self.component,owner,'SoundClass',voice,expected=old,allow_mutation=True,catalog=observed)
            except Exception as error:
                if isinstance(error,ValueError) or getattr(error,'outcome',None)=='not_dispatched':self.unknown=False
                raise
            self.unknown=False
        yield
        self._void(self.component,SOUND+'SetMediaPlayer',NewMediaPlayer=self.player)
        self.set_volume(self.volume)
        yield
        # Compile the first-line playback calls before reporting readiness.
        # Planning is read-only: do not start the synth or open a silent file.
        yield from self._prepare_playback_calls()
        self.prepared=True
    def _prepare_flags(self):
        """Observe owned player/synth defaults once; keep each native CAS proof."""
        from .values import capture_selected_values
        from .story_dialogue import field
        rows=((self.player,'NativeAudioOut',False),(self.player,'PlayOnOpen',True),(self.player,'Loop',False),
              (self.component,'bAllowSpatialization',False),(self.component,'bStopWhenOwnerDestroyed',True),
              (self.component,'bAutoDestroy',False),(self.component,'bIsUISound',False))
        catalog,values=capture_selected_values(self.scope.pid,(identity(self.player),identity(self.component)),
            fields=tuple(name for _,name,_ in rows),references=True)
        if any(value.errors or value.truncated for value in values.values()):
            raise RuntimeError('Owned audio configuration observation incomplete')
        changes=[]
        for obj,name,wanted in rows:
            value=values[obj.index];keys=[key for key in value.types if key[1]==name]
            if len(keys)!=1 or value.types[keys[0]]!='BoolProperty':raise ValueError('Owned audio flag schema changed: '+name)
            old=field(value,name)
            if type(old) is not bool:raise ValueError('Owned audio flag is not boolean: '+name)
            if old!=wanted:changes.append((obj,name,wanted,old))
        for obj,name,wanted,old in changes:
            self.unknown=True
            try:self.scope.assign_scalar(obj,name,wanted,expected=old,allow_mutation=True,catalog=catalog)
            except ValueError:
                self.unknown=False;raise
            except Exception as error:
                if getattr(error,'outcome',None)=='not_dispatched':self.unknown=False
                raise
            self.unknown=False
    def _prepare_playback_calls(self):
        rows=((self.player,MEDIA+'Close',{}),(self.component,SYNTH+'Stop',{}),
              (self.component,SYNTH+'Start',{}),
              (self.source,'/Script/MediaAssets.FileMediaSource:SetFilePath',{'Path':''}),
              (self.player,MEDIA+'OpenSource',{'MediaSource':self.source}),
              *((self.player,MEDIA+name,{}) for name in ('IsReady','IsPlaying','IsPaused','Pause','Play')))
        metadata=getattr(getattr(self.scope,'_session',None),'_file_audio_metadata',None)
        if metadata is not None:
            planner=metadata.planner(self.scope,(self.player,self.source,self.component))
            catalog=planner._catalog;self.planners.append(planner)
        else:
            names=tuple(dict.fromkeys(path.rsplit(':',1)[-1] for _,path,_ in rows))
            found=capture_matching(self.scope.pid,names=names)
            functions=tuple(found.find_path(path) for _,path,_ in rows)
            snapshot=describe_selected(self.scope.pid,tuple(identity(fn) for fn in functions))
            actors=tuple(dict.fromkeys(identity(obj) for obj,_,_ in rows))
            catalog=snapshot.catalog.with_observations(capture_selected(self.scope.pid,actors))
            planner=self.scope.invocation_planner(catalog=catalog,selected_results=True)
            self.planners.append(planner)
            # Preserve the already verified descriptor closure for all ten calls.
            planner._metadata.read('struct',snapshot.catalog,functions,
                                   lambda catalog,objects:snapshot.descriptors)
        yield
        for obj,path,arguments in rows:
            self.calls[identity(obj),path]=planner.prepare(catalog.by_index[obj.index],
                                                         catalog.find_path(path),**arguments)
        # These ten bounded plans use the descriptor/actor observation above
        # and never invoke gameplay. Yielding after each tiny compilation made
        # speech readiness wait through ten more complete world-loading polls.
        # Keep the metadata yield and all native construction boundaries above;
        # publish prepared only after this whole read-only group succeeds.
    def set_volume(self,value):
        if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=4:raise ValueError('File audio gain must be between zero and four')
        if self.closed or self.unknown:raise RuntimeError('File audio owner unavailable')
        if self.component is not None:self._void(self.component,SYNTH+'SetVolumeMultiplier',VolumeMultiplier=float(value))
        self.volume=float(value)
    def play(self,path):
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            return self._play(path)
    def _play(self,path):
        path,duration=wav_file(path);self.prepare()
        if not self.stop():raise RuntimeError('Previous audio cleanup pending')
        self._void(self.component,SYNTH+'Start')
        self._void(self.source,'/Script/MediaAssets.FileMediaSource:SetFilePath',Path=path)
        with self._call(self.player,MEDIA+'OpenSource',MediaSource=self.source) as result:accepted=result.return_value
        if accepted is not True:
            self._void(self.component,SYNTH+'Stop');raise RuntimeError('Game media decoder rejected WAV')
        self.path=path;self.duration=duration;self.playing=True;self.paused=False
        self.started=time.monotonic();self.ready=False;self.next_poll=0.;self.last_status=None
    def poll(self):
        if self.closed or self.unknown:raise RuntimeError('File audio owner unavailable')
        if not self.playing:return True
        now=time.monotonic()
        if now<self.next_poll:return False
        self.next_poll=now+.1
        with self._call(self.player,MEDIA+'IsReady') as result:ready=result.return_value
        if not ready:
            if self.ready:self.stop();return True
            if now-self.started>2.:
                self.stop();raise RuntimeError('Game WAV decoding exceeded 2 seconds')
            return False
        self.ready=True
        with self._call(self.player,MEDIA+'IsPlaying') as result:playing=result.return_value
        with self._call(self.player,MEDIA+'IsPaused') as result:paused=result.return_value
        self.last_status=dict(ready=ready,playing=playing,paused=paused)
        if not playing and not paused:self.stop();return True
        return False
    def pause(self,value):
        if not self.playing or not self.ready or value==self.paused:return
        with self._call(self.player,MEDIA+('Pause' if value else 'Play')) as result:accepted=result.return_value
        if accepted is True:self.paused=value
    def stop(self):
        if self.unknown:return False
        if self.closed:return True
        if self.player is not None:self._void(self.player,MEDIA+'Close')
        if self.component is not None:self._void(self.component,SYNTH+'Stop')
        self.playing=False;self.paused=False;self.ready=False
        return True
    def close(self,*,world_retired=False):
        if self.closed:return True
        if self.unknown:return False
        if not world_retired and not self.stop():return False
        # Native destruction stops the synth; no calls into retired components.
        result=self.carrier.retire_world() if world_retired else self.carrier.close()
        if not result:return False
        for planner in self.planners:planner.close()
        self.planners=[];self.calls={};self.closed=True;self.playing=False
        self._preparation=None
        return True
