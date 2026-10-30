"""Validated, world-free static-prop plans prepared before a save is loaded."""
from dataclasses import dataclass
from .worldbuilder_maps import validate


@dataclass(frozen=True)
class SpawnRow:
    id: str
    asset: str
    transform: tuple


@dataclass(frozen=True, init=False)
class SpawnPlan:
    world: str
    rows: tuple
    assets: tuple
    skipped_world_edits: int
    object_count: int

    def __init__(self, data):
        # Construction is the validation boundary. The plan contains no mutable
        # caller containers, engine objects, world identity, or authority to spawn.
        scene=validate(data)
        rows=tuple(SpawnRow(r['id'],r['asset'],tuple(r['transform']))
                   for r in scene['objects'] if r['kind']!='world_edit')
        if any(r['kind']!='mesh' or r.get('component_edits')
               for r in scene['objects'] if r['kind']!='world_edit'):
            raise ValueError('Version 1 supports static-mesh props without component edits; unsupported actor types were not spawned')
        object.__setattr__(self,'world',scene['world'])
        object.__setattr__(self,'rows',rows)
        object.__setattr__(self,'assets',tuple(dict.fromkeys(r.asset for r in rows)))
        object.__setattr__(self,'skipped_world_edits',len(scene['objects'])-len(rows))
        object.__setattr__(self,'object_count',len(scene['objects']))

    def for_world(self, world):
        if self.world!=world:
            raise ValueError('Load the same game level before loading this builder map')
        return self
