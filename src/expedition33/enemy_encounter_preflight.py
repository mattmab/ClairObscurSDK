"""Reject known unresolved original defaults before ownership changes.

This supported-build cache gate does not prove live encounter validity. Native
identity, construction and lifecycle checks remain authoritative and unchanged.
"""
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def _evidence():
    return json.loads(Path(__file__).with_name('_enemy_encounter_preflight.json').read_text(encoding='utf8'))


def validate_default_encounter(recipe, *, authored_instance_route=None):
    if recipe.get('recipe')!='original_world_blueprint_v1':return
    if authored_instance_route is not None:
        from .enemy_authored_routes import authored_spawn_profile
        profile=authored_spawn_profile(recipe,include_unverified=True)
        if (profile is None or type(authored_instance_route) is not int or
            profile['route']!=authored_instance_route):
            raise ValueError('No verified authored override for this recipe')
        return
    records=_evidence()['recipes']
    record=records.get(recipe['id'])
    handles=recipe.get('authored_relationships',{}).get('authored_world_encounters',[])
    if (record is None or record['class_path']!=recipe['class_path'] or
            record['default_handles']!=handles or
            record.get('default_table_handles')!=recipe.get('authored_relationships',{}).get('authored_default_table_handles')):
        raise ValueError('Original encounter defaults lack matching supported-build evidence; recipe retained for review')
    if record['status']!='structurally_resolved':
        detail=', '.join(handles) if handles else '(no default encounter evidence)'
        raise ValueError('Original encounter defaults unresolved: '+detail+
                         '. Spawn blocked to prevent an empty encounter; recipe retained for review.')
