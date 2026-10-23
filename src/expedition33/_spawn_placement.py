"""Geometry for placing an assembled actor; callers supply measured world bounds.

This does not query terrain, spawn actors or enable collision. The caller must
measure the complete assembly at the requested orientation, resolve terrain at
the proposed footprint and check the translated bounds before committing it.
"""
from dataclasses import dataclass
import math


def _vector(value):
    result = tuple(value)
    if len(result) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) for v in result):
        raise ValueError('Expected three finite coordinates')
    return result


def _nonnegative(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('Expected a finite nonnegative distance')
    return value


@dataclass(frozen=True)
class AssemblyBounds:
    center: tuple
    extent: tuple

    def __post_init__(self):
        object.__setattr__(self, 'center', _vector(self.center))
        extent = _vector(self.extent)
        if any(v < 0 for v in extent) or not any(extent):
            raise ValueError('Expected nonempty measured bounds')
        object.__setattr__(self, 'extent', extent)


def horizontal_candidate(bounds, player_position, forward, player_radius, clearance):
    """Return an assembly center outside the player's horizontal exclusion disk.

    Circumscribed radius is conservative even for diagonal approaches and
    assemblies whose geometry is offset from the actor origin.
    """
    player = _vector(player_position)
    direction = _vector(forward)
    radius = _nonnegative(player_radius)
    gap = _nonnegative(clearance)
    length = math.hypot(direction[0], direction[1])
    if not length:
        raise ValueError('Expected a horizontal direction')
    distance = math.hypot(bounds.extent[0], bounds.extent[1]) + radius + gap
    return (player[0] + direction[0] / length * distance,
            player[1] + direction[1] / length * distance, bounds.center[2])


def grounded_translation(bounds, actor_origin, candidate_center, ground_z, clearance=0):
    """Translate measured bounds so their bottom rests above confirmed ground.

    ground_z must come from the target footprint, not the player's elevation.
    Returned actor origin preserves the measured assembly-to-root offset.
    Collision must remain disabled until the caller validates this placement.
    """
    origin = _vector(actor_origin)
    candidate = _vector(candidate_center)
    gap = _nonnegative(clearance)
    if type(ground_z) not in (int, float) or not math.isfinite(ground_z):
        raise ValueError('Expected confirmed finite ground height')
    center = (candidate[0], candidate[1], ground_z + gap + bounds.extent[2])
    translated = tuple(origin[i] + center[i] - bounds.center[i] for i in range(3))
    return translated, AssemblyBounds(center, bounds.extent)
