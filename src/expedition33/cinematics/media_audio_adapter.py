"""Owned media-clock audio composition, separate from scene admission."""
from expedition33.assets import load_asset
from expedition33.catalog import capture_selected
from .media_audio_context import MediaAudioContext
from .audio_profile import decode_sections
from .owned_audio_timeline import OwnedAudioTimelineDispatcher
import json
from pathlib import Path

def admitted_audio_profile(media_profile):
    # Only this reviewed bundled manifest may request composition. Capability
    # advertisement alone does not admit an arbitrary media asset or timeline.
    document=json.loads(Path(__file__).with_name('aliciabirth_audio.json').read_text())
    if document.get('admitted') is not True:return None
    exact=document.get('media',{})
    if any(getattr(media_profile,key,None)!=value for key,value in exact.items()):return None
    if set(exact)!={'definition','definition_sha256','sequence','saved_id','movie_path'}:
        raise ValueError('Exact media mapping missing from audio admission')
    return document

class MediaAudioAdapter:
    def __init__(self,session,panel,profile):
        self.sections=decode_sections(profile)
        transport=session._session._transport
        if getattr(transport,'owned_sound_capacity',0)<len(self.sections) or getattr(transport,'owned_sound_volume_max',0)<2:
            raise RuntimeError('Native audio capacity 32 and gain 2 required')
        if type(getattr(transport,'timespan_values_protocol',0)) is not int or transport.timespan_values_protocol!=1:
            raise RuntimeError('Verified copied media clock required')
        self.context=MediaAudioContext(session,panel)
        self.dispatcher=None;self.state='new';self.error=None

    def prepare(self):
        if self.state!='new':raise RuntimeError('Audio composition already used')
        self.state='preparing';context=self.context
        context.prepare()
        sources={}
        for path in dict.fromkeys(s.source for s in self.sections):
            result=load_asset(context.scope,path)
            source=result.return_value
            if source is None or source.class_name!='SoundWave':raise ValueError('Exact SoundWave source required')
            sources[path]=source
        observations=capture_selected(context.scope.pid,tuple((o.index,o.serial,o.address) for o in sources.values()))
        context.planner.refresh_from(context.planner._catalog.with_observations(observations))
        self.dispatcher=OwnedAudioTimelineDispatcher(context.audio,context.planner,context.panel,self.sections)
        self.dispatcher.prepare(sources);self.state='prepared'
        return self

    def start(self):
        if self.state!='prepared':raise RuntimeError('Prepared audio composition required')
        if self.context.pause_original() is not True:
            raise RuntimeError('Original audio pause was not acknowledged; playback cannot start')
        self.state='running'

    def poll(self,video,playing):
        if self.state!='running':raise RuntimeError('Audio composition is not running')
        try:
            timing=video.media_position()
            return self.dispatcher.advance(timing['time_seconds'],playing=playing)
        except BaseException as error:
            self.state='failed';self.error=repr(error);raise

    def close(self):
        if self.state=='closed':return True
        self.state='cleanup_pending'
        if not self.context.close():return False
        if self.dispatcher is not None:self.dispatcher.timeline.discard_after_cleanup()
        self.state='closed';return True

    def retire_world(self):
        if self.state=='closed':return True
        self.state='retirement_pending'
        if not self.context.retire_world():return False
        if self.dispatcher is not None:self.dispatcher.timeline.discard_after_cleanup()
        self.state='closed';return True
