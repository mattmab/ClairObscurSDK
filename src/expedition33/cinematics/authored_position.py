"""Exact conversion from authored tick resolution to owned-player frames."""
from fractions import Fraction
import math,struct


def _rate(value):
    if (type(value) not in (tuple,list) or len(value)!=2 or
            any(type(n) is not int or not 0<n<(1<<31) for n in value)):
        raise ValueError('Expected a positive signed frame-rate numerator and denominator')
    return Fraction(*value)


def player_position(tick,source_rate,player_rate):
    """Return the int32 frame and float32 subframe consumed by Unreal.

    Keep rational arithmetic through the rate conversion, including negative
    positions. Normalize float32 rounding into the following frame so the wire
    never contains the invalid subframe 1.0.
    """
    if type(tick) is not int or not -(1<<31)<=tick<(1<<31):
        raise ValueError('Expected a signed authored tick')
    position=Fraction(tick)*_rate(player_rate)/_rate(source_rate)
    frame=position.numerator//position.denominator
    subframe=struct.unpack('<f',struct.pack('<f',float(position-frame)))[0]
    if subframe==1.0:frame+=1;subframe=0.0
    if not -(1<<31)<=frame<(1<<31) or not math.isfinite(subframe):
        raise ValueError('Converted player position exceeds the native frame range')
    return frame,subframe
