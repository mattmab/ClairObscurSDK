"""Copied spatial observations through the existing validated invocation transport.

The caller supplies a catalog containing the target and Engine function closure.
Construction never scans the registry. Queries require the same runtime opt-ins
as ordinary reflected calls; discovery of a function does not authorize it.
Native dispatch still checks the live identity, schema, recipient and context.
"""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Bounds:
    """World-space axis-aligned bounds; extent is a half-size, in game units."""
    origin: tuple
    extent: tuple


@dataclass(frozen=True)
class WorldRay:
    origin: tuple
    direction: tuple


def _numbers(value, count):
    try:
        result = tuple(value)
    except TypeError:
        raise ValueError('Expected finite numeric coordinates') from None
    if len(result) != count or any(type(x) not in (int, float) for x in result):
        raise ValueError('Expected finite numeric coordinates')
    try:
        result = tuple(float(x) for x in result)
    except OverflowError:
        raise ValueError('Expected finite numeric coordinates') from None
    if not all(math.isfinite(x) for x in result):
        raise ValueError('Expected finite numeric coordinates')
    return result


def _vector(value, names):
    return _numbers((value[name] for name in names), len(names))


class SpatialQueries:
    """Scope-bound read-only queries; close releases planning observations only.

    Returned tuples own no UObjects and remain usable after close. Actor and
    controller observations are not retained by this facade. Recreate it with a
    fresh catalog after travel; stale identities fail through the normal planner.
    Screen positions use Unreal viewport pixels, without a UMG DPI conversion.
    """
    def __init__(self, scope, *, catalog):
        self._catalog = catalog
        self._planner = scope.invocation_planner(catalog=catalog, selected_results=True)

    def close(self):
        self._planner.close()
        self._catalog = None

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()

    def _call(self, target, owner, name, **arguments):
        self._planner._check()
        function = self._catalog.find_path(f'/Script/Engine.{owner}:{name}', 'Function')
        return self._planner.prepare(target, function, **arguments).invoke()

    def actor_bounds(self, actor, *, only_colliding=False, include_children=True):
        if type(only_colliding) is not bool or type(include_children) is not bool:
            raise ValueError('Bounds switches must be bool')
        with self._call(actor, 'Actor', 'GetActorBounds',
                        bOnlyCollidingComponents=only_colliding,
                        bIncludeFromChildActors=include_children) as result:
            origin = _vector(result.outputs['Origin'], 'XYZ')
            extent = _vector(result.outputs['BoxExtent'], 'XYZ')
            if any(x < 0 for x in extent):
                raise ValueError('Engine returned a negative bounds extent')
            return Bounds(origin, extent)

    def viewport_size(self, controller):
        with self._call(controller, 'PlayerController', 'GetViewportSize') as result:
            size = result.outputs['SizeX'], result.outputs['SizeY']
            if any(type(x) is not int or x < 0 for x in size):
                raise ValueError('Engine returned an invalid viewport size')
            return size

    def project(self, controller, world_position, *, viewport_relative=False):
        """Return pixel coordinates, or None if Unreal reports projection failure.

        Successful projection does not prove visibility or absence of occlusion.
        """
        position = _numbers(world_position, 3)
        if type(viewport_relative) is not bool:
            raise ValueError('viewport_relative must be bool')
        with self._call(controller, 'PlayerController', 'ProjectWorldLocationToScreen',
                        WorldLocation=dict(zip('XYZ', position)),
                        bPlayerViewportRelative=viewport_relative) as result:
            if type(result.return_value) is not bool:
                raise ValueError('Engine returned an invalid projection status')
            return _vector(result.outputs['ScreenLocation'], 'XY') if result.return_value else None

    def deproject(self, controller, screen_position):
        """Return a world ray, or None on failure; this performs no collision trace."""
        x, y = _numbers(screen_position, 2)
        with self._call(controller, 'PlayerController', 'DeprojectScreenPositionToWorld',
                        ScreenX=x, ScreenY=y) as result:
            if type(result.return_value) is not bool:
                raise ValueError('Engine returned an invalid deprojection status')
            if not result.return_value:
                return None
            return WorldRay(_vector(result.outputs['WorldLocation'], 'XYZ'),
                            _vector(result.outputs['WorldDirection'], 'XYZ'))
