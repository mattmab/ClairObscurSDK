"""Verified unweighted float-channel math, not a complete scene admission policy."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class CubicKey:
    frame: int
    value: float
    arrive_tangent: float
    leave_tangent: float

class UnweightedCubicChannel:
    def __init__(self,keys,*,default):
        self.keys=tuple(keys);self.default=default
        if len(self.keys)>64 or type(default) not in (int,float) or not math.isfinite(default):raise ValueError('Bounded finite float channel required')
        previous=None
        for key in self.keys:
            if type(key) is not CubicKey or type(key.frame) is not int or (previous is not None and key.frame<=previous):raise ValueError('Strictly ordered exact frame keys required')
            if any(type(v) not in (int,float) or not math.isfinite(v) for v in (key.value,key.arrive_tangent,key.leave_tangent)):raise ValueError('Finite unweighted cubic fields required')
            previous=key.frame
    def evaluate(self,frame):
        if type(frame) not in (int,float) or not math.isfinite(frame):raise ValueError('Finite incoming sequence frame required')
        if not self.keys:return float(self.default)
        if frame<=self.keys[0].frame:return float(self.keys[0].value)
        if frame>=self.keys[-1].frame:return float(self.keys[-1].value)
        for left,right in zip(self.keys,self.keys[1:]):
            if left.frame<=frame<right.frame:
                dt=right.frame-left.frame;alpha=(frame-left.frame)/dt;inverse=1.-alpha
                # Same-build142c90d40 unweighted branch. Channel TickResolution
                # is intentionally absent: only the weighted branch reads it.
                a=left.value+dt*left.leave_tangent/3.
                b=right.value-dt*right.arrive_tangent/3.
                return inverse**3*left.value+3*inverse*inverse*alpha*a+3*inverse*alpha*alpha*b+alpha**3*right.value
        raise RuntimeError('Unreachable channel interval')

@dataclass(frozen=True)
class SectionGain:
    """Type-0 native easing on inclusive/exclusive section bounds, in root frames."""
    channel: UnweightedCubicChannel
    lower: int
    upper: int
    ease_in: int = 0
    ease_out: int = 0
    tick_rate: int = 24000

    def __post_init__(self):
        if any(type(v) is not int for v in (self.lower,self.upper,self.ease_in,self.ease_out,self.tick_rate)):
            raise ValueError('Exact integer root-frame timings required')
        if not 0<=self.lower<self.upper or min(self.ease_in,self.ease_out)<0 or self.tick_rate<=0:
            raise ValueError('Invalid section easing range')

    def __call__(self,seconds):
        if type(seconds) not in (int,float) or not math.isfinite(seconds):
            raise ValueError('Finite media time required')
        frame=seconds*self.tick_rate
        clamp=lambda v:max(0.,min(1.,v))
        gain_in=clamp((frame-self.lower)/self.ease_in) if self.ease_in else 1.
        gain_out=1.-clamp((frame-(self.upper-self.ease_out))/self.ease_out) if self.ease_out else 1.
        return self.channel.evaluate(frame)*gain_in*gain_out
