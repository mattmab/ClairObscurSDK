"""Reviewed full sequences staged in the current exploration world.

Reuses encounter-owned players, translation, camera restoration and finite
endpoint evidence. Original campaign game actions are never dispatched.
"""
from dataclasses import dataclass
from types import MappingProxyType
import logging
from .._reader import shared_operation
from .._menu_latency import MenuLatency, measure_method
from .controller import StartResult, StopResult, ReplayObservation, BackendState
from .adapters import PreviewAdapter


@dataclass(frozen=True)
class PortableProfile:
    definition: str
    saved_id: str
    sequence: str
    sha256: str
    anchor: tuple

    def matches(self,scene):
        return (scene.get('id'),scene.get('saved_id'),scene.get('sequence'),
                scene.get('sha256',scene.get('definition_sha256')))==(
                    self.definition,self.saved_id,self.sequence,self.sha256)


PROFILES=MappingProxyType({p.definition:p for p in (
    PortableProfile('Sandfall/Content/Cinematics/Simon/SimonIntro/DA_GA_CIN_SimonIntro.uasset',
        'SimonIntro','/Game/Cinematics/Simon/SimonIntro/MCS_SimonIntro.MCS_SimonIntro',
        '1071b0c1f16347a3cba2f93f1a59ff5fcd25405b1464bba41f09a5ee615c18b0',
        (21422.7285,6693.6206,-402267.125)),
    PortableProfile('Sandfall/Content/Cinematics/Simon/SimonOutro/DA_GA_CIN_SimonOutro.uasset',
        'SimonOutro','/Game/Cinematics/Simon/SimonOutro/MCS_SimonOutro.MCS_SimonOutro',
        '714c88af61f43b6ae5be8dd952002fd57e0d8887769014f2476a34e32bba5f1c',
        (21422.7285,6693.6206,-402267.125)),
    PortableProfile('Sandfall/Content/Cinematics/SpringMeadow/LuneArrives/DA_GA_CIN_LuneArrives.uasset',
        'LuneArrives','/Game/Cinematics/SpringMeadow/LuneArrives/MCS_LuneArrives.MCS_LuneArrives',
        '469adb0ef14618a53332396a70e45a2485eb7378a62143c16b13d68a30b109f5',
        (-1988.63037109375,-8683.29296875,6.970677375793457)),
)})


REQUIRED_PROTOCOLS=('sequence_player_protocol','sequence_camera_protocol','sequence_origin_protocol',
           'frame_time_values_protocol','menu_protocol','sequence_retirement_protocol',
           'music_audio_protocol','music_audio_retirement_protocol','retired_world_cleanup_protocol',
           'original_audio_pause_protocol','owned_audio_cleanup_protocol','cinematic_widget_protocol',
           'picto_class_load_protocol','asset_load_protocol')

def available(transport):
    return all(type(getattr(transport,n,0)) is int and getattr(transport,n,0)==1 for n in REQUIRED_PROTOCOLS)


class PortableSceneAdapter(PreviewAdapter):
    def __init__(self,scope,scene,*,panel_pool=None):
        super().__init__(scope,scene)
        self.context=None
        self.services=None
        self.panel_pool=panel_pool
        self._pool_acquired=False
        if panel_pool is not None and panel_pool.scope._session is not scope._session:
            raise ValueError('Cinematic panel pool belongs to another SDK session')
        self.latency=MenuLatency()

    @measure_method('dispatch.total')
    def start(self):
        from ..simon_portable import _snapshot
        from ..cinematic_context_panel import CinematicContextPanel
        from ..sequences import OwnedLevelSequence
        from .title_adapters import OwnedSequenceContext
        from .controller_anchor import context_observer
        profile=PROFILES.get(self.scene.get('id'))
        if (profile is None or not profile.matches(self.scene) or
                self.scene.get('unlocked') is not True or not available(self.scope._session._transport)):
            return StartResult.REJECTED
        # One explicitly owned reader, fresh queries throughout. In particular,
        # do not spawn/validate a new native reader for every reflection read.
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            with self.latency.measure('dispatch.snapshot'):
                self.context,_,position=_snapshot(self.scope)
            # A raised staging area avoids nearby ground props without moving
            # the exploration pawn. It does not prove geometry clearance.
            delta=tuple(position[i]+(1500.,0.,500.)[i]-profile.anchor[i] for i in range(3))
            with self.latency.measure('dispatch.panel_build'):
                if self.panel_pool is None:
                    self.panel=CinematicContextPanel(self.scope._session)
                    self.panel.build()
                else:
                    self.panel=self.panel_pool.acquire(self.context)
                    self._pool_acquired=True
            self.services=OwnedSequenceContext(self.scope,self.panel,
                routing_class=getattr(self.panel_pool,'routing_class',None),
                widget_dependencies=getattr(self.panel_pool,'widget_dependencies',None),
                music_dependencies=getattr(self.panel_pool,'music_dependencies',None))
            # Native music and sequence owners require the attached panel.
            # Keep its construction before input acquisition; never weaken that
            # native ownership requirement to move allocation earlier.
            with self.latency.measure('dispatch.input_lock'):
                self.panel.open()
            with self.latency.measure('dispatch.locked_preparation'):
                with self.latency.measure('dispatch.music_prepare'):
                    self.services.prepare_music()
                loader=getattr(self.panel_pool,'asset_loader',None)
                options={'asset_loader':loader} if loader is not None else {}
                metadata=getattr(self.panel_pool,'sequence_metadata',None)
                if metadata is not None:options['metadata']=metadata
                self.sequence=OwnedLevelSequence(self.scope,**options)
                with self.latency.measure('dispatch.sequence_and_completion'):
                    self.sequence.build(self.panel,profile.sequence,capture_camera=True,origin_translation=delta,completion=True)
                with self.latency.measure('dispatch.context_validate'):
                    if context_observer(self.scope)()!=self.context:
                        self.last=ReplayObservation(BackendState.FAILED,'World changed during cinematic preparation')
                        return StartResult.REJECTED
                # Leave gameplay music running until the endpoint and fresh
                # context are qualified; arm audio immediately before Play.
                with self.latency.measure('dispatch.services_arm'):
                    self.services.arm(self.sequence)
            with self.latency.measure('dispatch.play'):
                self.sequence.play()
        logging.getLogger(__name__).info('Portable cinematic dispatch timings: %s',self.latency.snapshot())
        return StartResult.STARTED

    def poll(self):
        with shared_operation(self.scope.pid,_executable=self.scope._session._transport._executable):
            if self.services is not None:self.services.status()
            result=super().poll()
        self.last=ReplayObservation(result.state,result.detail.replace('Preview:','Full scene:'))
        return self.last

    def stop(self):
        from .._sequence_owner import SequenceCleanupDeferred
        try:
            if self.sequence is not None:
                self.sequence.close();self.sequence=None
            if self.services is not None:
                self.services.close();self.services=None
            if self.panel is not None:
                if self._pool_acquired:
                    if not self.panel_pool.release(self.panel):return StopResult.DEFERRED
                    self._pool_acquired=False
                else:self.panel.close()
                self.panel=None
        except SequenceCleanupDeferred:return StopResult.DEFERRED
        return StopResult.STOPPED

    def close(self,request):
        if request.epoch_valid:return self.stop() is StopResult.STOPPED
        if self.sequence is not None:
            widgets=getattr(self.services,'widgets',None)
            if not self.sequence.retire_world(closed_dependents=(widgets,) if widgets else ()):return False
            self.sequence=None
        if self.services is not None:
            if not self.services.retire_world():return False
            self.services=None
        if self.panel is not None:
            if self._pool_acquired:
                if not self.panel_pool.release(self.panel,retired=True):return False
                self._pool_acquired=False
            elif self.panel.retire_world()!='ack':return False
            self.panel=None
        return True
