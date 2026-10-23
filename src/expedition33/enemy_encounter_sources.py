"""Exact cached authored encounter links, not visual identity aliases.

No asset discovery, loading, catalog promotion, or encounter-table changes.
The selected battle enemy can be one member of a full original encounter whose
world representation is different. Ambiguous/multiple encounter defaults remain
in the catalog's audit metadata and are not offered as deterministic choices.
"""


def authored_encounter_sources(catalog, recipe_id):
    entries=catalog['entries']
    selected=[row for row in entries if row.get('id')==recipe_id]
    if len(selected)!=1:raise ValueError('Missing or ambiguous enemy recipe ID')
    relationships=selected[0].get('authored_relationships',{})
    links=relationships.get('authored_world_blueprint_sources',[])
    by_path={}
    for row in entries:by_path.setdefault(row['class_path'],[]).append(row)
    result=[];seen=set()
    for link in links:
        candidates=by_path.get(link.get('world_class'),[])
        if len(candidates)!=1:continue
        world=candidates[0]
        encounter=link.get('encounter')
        defaults=world.get('authored_relationships',{}).get('authored_world_encounters',[])
        if (world.get('spawn_available') is not True or
            world.get('recipe')!='original_world_blueprint_v1' or
            type(encounter) is not str or not encounter or
            type(defaults) is not list or not defaults or
            any(type(row) is not str for row in defaults) or set(defaults)!={encounter}):continue
        key=(world['id'],encounter)
        if key in seen:continue
        seen.add(key)
        result.append(dict(recipe_id=world['id'],class_path=world['class_path'],
            encounter=encounter,variant=world.get('variant',world['class_path'].rsplit('.',1)[-1]),
            validation=world.get('validation','pattern-derived'),
            meaning='Full original encounter; exploration appearance and other enemies may differ.'))
    return tuple(sorted(result,key=lambda row:(row['encounter'],row['class_path'])))
