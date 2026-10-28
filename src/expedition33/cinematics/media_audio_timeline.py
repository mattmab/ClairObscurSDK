"""Bounded media-clock action planner, independent of dispatch and asset admission.

Only reviewed normalized sections may enter this planner. It does not authorize
AliciaBirth playback: native curve/easing and source contracts still gate that
adapter. Actions must commit only after every owned invocation is acknowledged.
"""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Section:
    identity: str
    source: str
    start: float
    end: float
    source_offset: float
    gain: object
    pitch: float = 1.0

@dataclass(frozen=True)
class Action:
    operation: str
    section: str
    value: float | None = None

@dataclass(frozen=True)
class Step:
    serial: int
    position: float
    actions: tuple
    active: frozenset
    gains: tuple

class MediaAudioPlanner:
    def __init__(self,sections,*,capacity,volume_max=1.,maximum_clock_step=.25):
        self.sections=tuple(sections)
        if type(capacity) is not int or not 1<=capacity<=64 or not 1<=len(self.sections)<=capacity:
            raise ValueError('Complete audio preparation exceeds the native owner capacity')
        if type(volume_max) not in (int,float) or not math.isfinite(volume_max) or not 0<volume_max<=2:
            raise ValueError('Unverified native volume bound')
        if type(maximum_clock_step) not in (int,float) or not 0<maximum_clock_step<=1:
            raise ValueError('Bounded clock tolerance required')
        identities=set()
        for s in self.sections:
            if type(s) is not Section or type(s.identity) is not str or not s.identity or s.identity in identities:
                raise ValueError('Unique reviewed section identities required')
            if type(s.source) is not str or not s.source.startswith('/Game/') or '..' in s.source:
                raise ValueError('Exact source asset path required')
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in (s.start,s.end,s.source_offset,s.pitch)):
                raise ValueError('Finite normalized section timings required')
            if not 0<=s.start<s.end or s.source_offset<0 or s.pitch!=1. or not callable(s.gain):
                raise ValueError('Unsupported section timing, pitch or gain evaluator')
            identities.add(s.identity)
        self.volume_max=float(volume_max);self.maximum_clock_step=maximum_clock_step
        self.position=None;self.active=frozenset();self.gains={};self.serial=0;self.pending=None

    def plan(self,position,*,playing,elapsed=None):
        if self.pending is not None:raise RuntimeError('Unacknowledged audio step cannot be replayed')
        if type(playing) is not bool or type(position) not in (int,float) or not math.isfinite(position) or position<0:
            raise ValueError('A valid copied native media clock is required')
        if elapsed is not None and (type(elapsed) not in (int,float) or not math.isfinite(elapsed) or elapsed<0):
            raise ValueError('A finite nonnegative monotonic poll interval is required')
        if not playing:
            if self.active:raise RuntimeError('Stopped media requires stopping owned audio')
            return None # Async opening is not a running scheduler clock.
        if self.position is None and position>self.maximum_clock_step:
            raise RuntimeError('Initial media clock missed the synchronized start window')
        # Media advances while controller/native calls are in flight. Bound
        # unexplained forward movement, not the total time between polls.
        forward_limit=self.maximum_clock_step+(elapsed if elapsed is not None else 0.)
        if self.position is not None and (position<self.position or position-self.position>forward_limit):
            raise RuntimeError(f'Media clock discontinuity requires stopping owned audio: previous={self.position:.6f}, current={position:.6f}, delta={position-self.position:.6f}, elapsed={elapsed!r}, limit={forward_limit:.6f}')
        active=frozenset(s.identity for s in self.sections if s.start<=position<s.end)
        actions=[Action('stop',identity) for identity in sorted(self.active-active)]
        gains={}
        for s in self.sections:
            if s.identity not in active:continue
            gain=s.gain(position)
            if type(gain) not in (int,float) or not math.isfinite(gain) or not 0<=gain<=self.volume_max:
                raise ValueError('Authored gain exceeds verified native support; do not clamp it')
            gain=float(gain);gains[s.identity]=gain
            # Gain before Play ensures no frame of unintended default volume.
            if s.identity not in self.active or self.gains.get(s.identity)!=gain:
                actions.append(Action('gain',s.identity,gain))
            if s.identity not in self.active:
                actions.append(Action('play',s.identity,float(s.source_offset+position-s.start)))
        self.pending=Step(self.serial+1,float(position),tuple(actions),active,tuple(gains.items()))
        return self.pending

    def commit(self,step):
        if step is not self.pending or step is None:raise RuntimeError('Only the exact acknowledged audio step may commit')
        self.position=step.position;self.active=step.active;self.gains=dict(step.gains);self.serial=step.serial;self.pending=None

    def discard_after_cleanup(self):
        """Use only after native owners confirmed close; never retry unknown calls."""
        self.pending=None;self.active=frozenset();self.gains={};self.position=None
