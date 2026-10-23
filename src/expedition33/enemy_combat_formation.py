"""Deterministic experimental formation from observed original actor positions.

This plans coordinates only. It does not prove floor support, mesh clearance,
navigation, enemy compatibility or readiness to mutate a live encounter.
"""
import math


def plan_added_positions(locations, *, spacing=450.):
    """Preserve separated positions; repair overlaps using original side axes."""
    if (type(locations) not in (list,tuple) or not 4<=len(locations)<=10 or
        type(spacing) not in (int,float) or not math.isfinite(spacing) or not 250<=spacing<=600):
        raise ValueError('Expected 4..10 observed positions and spacing 250..600 cm')
    if any(type(p) not in (list,tuple) or len(p)!=3 or
           any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>1e7 for v in p)
           for p in locations):
        raise ValueError('Expected finite observed world coordinates')
    center=locations[0]
    directions=[]
    for side in locations[1:3]:
        delta=(side[0]-center[0],side[1]-center[1]);length=math.hypot(*delta)
        if not 100<length<1000:raise ValueError('Original formation geometry is unsupported')
        directions.append(tuple(v/length for v in delta))
    if sum(a*b for a,b in zip(*directions))>-.5:
        raise ValueError('Original side directions do not form a separated formation')
    accepted=list(locations[:3]);overlapping=[]
    for slot,old in enumerate(locations[3:],3):
        if any(math.dist(old[:2],p[:2])<spacing-1 for p in accepted):
            overlapping.append((slot,old))
        else:accepted.append(old)
    result=[]
    for slot,old in overlapping:
        destination=None
        for candidate in range(14):
            side_index=candidate%2;rank=candidate//2+1
            side=locations[side_index+1];direction=directions[side_index]
            proposed=tuple(side[i]+rank*spacing*direction[i] for i in (0,1))+(old[2],)
            if math.dist(old,proposed)>2000:continue
            if any(math.dist(proposed[:2],p[:2])<spacing-1 for p in accepted):continue
            destination=proposed;break
        if destination is None:raise ValueError('No separated position within bounded placement distance; no partial plan')
        accepted.append(destination);result.append(dict(slot=slot,destination=destination))
    return tuple(result)
