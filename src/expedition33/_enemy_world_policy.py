"""Candidate-only current-world preparation gate; not runtime verification."""
QA_WORLD='/Game/QA/Map_BattleTesting.Map_BattleTesting'


def validate_spawn_world(world_path,grounded,arena_identity,transport):
    if world_path==QA_WORLD:
        return
    capability=getattr(transport,'enemy_current_world_staging_protocol',0)
    if type(capability) is not int or capability!=1:
        raise RuntimeError('Enemy spawning currently supports the QA world only; current-world staging capability is unavailable')
    if not isinstance(world_path,str) or not world_path.startswith('/Game/') or ':' in world_path:
        raise RuntimeError('Expected a current gameplay world asset path')
    if grounded is not True or arena_identity is None:
        raise RuntimeError('Current-world enemy staging requires grounded placement and an observed arena')
