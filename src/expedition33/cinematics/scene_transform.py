"""Pure pivot math for placing an authored scene and its owned actors.

The native origin rotates source-world coordinates about zero.  Its translation
must therefore compensate for the authored anchor in order to place that
anchor at the desired world location.  These functions do not dispatch native
operations or imply that a runtime supports rotation.
"""
import math


def _vector(value, name, limit=10_000_000.):
    if (type(value) not in (tuple, list) or len(value) != 3 or
            any(type(n) not in (int, float) or not math.isfinite(n) or abs(n) > limit for n in value)):
        raise ValueError(f'{name} must contain three bounded finite coordinates')
    return tuple(float(n) for n in value)


def _yaw(value):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 180:
        raise ValueError('Scene yaw must be between -180 and 180 degrees')
    return float(value)


def rotate_offset(offset, yaw):
    """Rotate a scene-relative offset about the vertical Z axis in degrees."""
    x, y, z = _vector(offset, 'Offset')
    radians = math.radians(_yaw(yaw))
    c, s = math.cos(radians), math.sin(radians)
    return x*c-y*s, x*s+y*c, z


def origin_translation(source_anchor, destination, yaw=0.):
    """Translation T such that R * source_anchor + T == destination."""
    source = _vector(source_anchor, 'Source anchor')
    destination = _vector(destination, 'Destination')
    rotated = rotate_offset(source, yaw)
    return tuple(destination[i]-rotated[i] for i in range(3))


def actor_placement(anchor, offset, actor_yaw, scene_yaw=0.):
    """Apply the scene rotation to a Blueprint offset and its local yaw."""
    anchor = _vector(anchor, 'Scene anchor')
    rotated = rotate_offset(offset, scene_yaw)
    actor_yaw = _yaw(actor_yaw)
    scene_yaw = _yaw(scene_yaw)
    yaw = math.remainder(actor_yaw+scene_yaw, 360.)
    return tuple(anchor[i]+rotated[i] for i in range(3)), yaw
