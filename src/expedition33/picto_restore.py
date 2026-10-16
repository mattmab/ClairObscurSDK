"""Restore explicit Picto overrides before any menu exists.

No saved pointers, no save writes, and no retries after an uncertain mutation.
The native startup operations retain the same schema, script and identity
guards as interactive edits, without requiring a UI selection.
"""
import time
from .catalog import capture_matching
from .values import read_values, read_values_many
from .picto_progression import change


def field(values, name):
    keys = [key for key in values.types if key[1] == name]
    if len(keys) != 1 or keys[0] in values.errors:
        raise RuntimeError('Unavailable Picto restore field: ' + name)
    return values.values[keys[0]]


def restore(scope, profiles, *, catalog=None):
    """Apply existing owned definitions and return measured, confirmed results.

    Caller binds an owned read worker. Missing inventory entries are reported,
    retained in configuration, and never created or granted.
    """
    started = time.perf_counter()
    if not profiles:
        return {'applied': [], 'missing': [], 'elapsed_ms': 0.0}
    if getattr(scope._session._transport, 'picto_startup_protocol', 0) != 1:
        raise RuntimeError('This runtime lacks menu-independent Picto restoration')
    if catalog is None:
        catalog = capture_matching(scope.pid, names=(
        'DT_PassiveEffects', 'SetBaseStatsMultiplier', 'SetCurrentStatValue', 'RefreshCurrentGearStats', 'Map_Remove',
        'ChangeLevel', 'SetPassiveEffectSharedProgression',
        'RefreshUsedLuminaPointsInternal', 'UpdateEquipmentStats',
        'FPassiveEffect', 'FPassiveEffectProgression', 'E_jRPG_StatType',
        'S_GearScalingLevel', 'S_LootContext', 'FormatArgumentData',
        'EAttributeScalingGrade', 'ECharacterAttribute', 'EWeaponQuality',
        'BP_DataAsset_Skill_C', 'BP_PictoViewItem_C', 'WBP_GM_SkillElementShort_C', 'WBP_PictoSlot_C',
        'S_WeaponDefinition', 'S_WeaponInstanceHandle', 'FEquipmentSlot',
        'S_jRPG_Item_DynamicData', 'S_jRPG_Item_StaticData'), classes=(
        'BP_ItemInstance_Gear_Pictos_C', 'BP_PassiveEffectInstance_C',
        'BP_CharacterData_C', 'BP_jRPG_GI_Custom_C', 'BP_ItemUpgradeSystem_C'))
    discovery_ms = (time.perf_counter() - started) * 1000
    ownership = None
    ownership_applied = []
    from .picto_inventory import owned_pictos
    catalog, owned = owned_pictos(scope.pid, catalog=catalog)
    if any('owned' in fields for fields in profiles.values()):
        from .picto_inventory import PictoOwnership
        needs_change=any((fields['owned']!=(identity in owned)) for identity,fields in profiles.items() if 'owned' in fields)
        if needs_change:
            ownership = PictoOwnership(scope)
        def restore_ownership(desired):
            if ownership is None:
                return []
            ids = [identity for identity, fields in profiles.items()
                   if fields.get('owned') is desired and (identity in ownership.owned) != desired]
            if not ids:
                return []
            if getattr(scope._session._transport, 'picto_batch_protocol', 0) == 1:
                from .picto_startup_batch import run
                # One guarded frame queue and final inventory readback. Never
                # fall back after dispatch: an uncertain mutation must not repeat.
                return run(ownership, ids, desired=desired)
            return [identity for identity in ids if ownership.set_owned(identity, desired)]
        ownership_applied.extend([identity, 'owned'] for identity in restore_ownership(True))
        if ownership is not None:
            catalog = catalog.with_observations(ownership.catalog)
            catalog, owned = owned_pictos(scope.pid, catalog=catalog)
    planner = scope.invocation_planner(selected_results=True, catalog=catalog)
    def one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise RuntimeError('Ambiguous Picto restore identity')
        return rows[0]
    def live(cls):
        return [o for o in catalog.select(cls) if o.class_name == cls and not o.object_flags & 0x30]
    functions = {}
    def fn(owner, name):
        key = owner, name
        if key not in functions:
            cls = catalog.find_class(owner)
            functions[key] = one(o for o in catalog.objects if o.outer_index == cls.index and o.name == name)
        return functions[key]
    def call(obj, owner, name, **args):
        with planner.prepare(obj, fn(owner, name), **args).invoke():
            pass
    inventory = {}
    for identity,(obj,_) in owned.items():
        # owned_pictos already compared each authoritative map key against
        # ItemDefinitionID, quantity, serial and level in one projected read.
        if identity not in profiles:
            continue
        if identity in inventory:
            raise RuntimeError('Ambiguous owned Picto definition: ' + identity)
        inventory[identity] = obj
    inventory_ms = (time.perf_counter() - started) * 1000 - discovery_ms
    characters = live('BP_CharacterData_C')
    gi = one(live('BP_jRPG_GI_Custom_C'))
    table = one(o for o in catalog.objects if o.class_name == 'DataTable' and
        catalog.path_name(o) == '/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
    if not characters:
        raise RuntimeError('No loaded character for Picto restoration')
    character = characters[0]
    resolve_ms = (time.perf_counter() - started) * 1000 - discovery_ms - inventory_ms
    applied = ownership_applied
    # One authoritative snapshot, not a full shared-map read per definition.
    shared = (field(read_values_many(catalog, (gi,), fields=('SharedPassiveEffectProgression',))[gi.index],
                    'SharedPassiveEffectProgression').items
              if any('mastered' in p for p in profiles.values()) else {})
    def progress(identity):
        row=shared.get(identity)
        return (row.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'],
                row.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F']) if row else (False,0)
    batched_levels=set();batched_mastery=set();batch_ms=0.
    transport=scope._session._transport
    groups={}
    for identity in inventory:
        fields=profiles[identity]
        if ('level' in fields and owned[identity][1]!=fields['level'] and
                getattr(transport,'picto_level_batch_protocol',0)==1):
            groups.setdefault(('level',fields['level']),[]).append(identity)
        # Baseline rollback may require exact partial steps: keep its existing
        # guarded operation, rather than replacing it with boolean mastery.
        if ('mastered' in fields and 'mastery_steps' not in fields and
                getattr(transport,'picto_mastery_batch_protocol',0)==1):
            learnt,steps=progress(identity)
            if learnt!=fields['mastered'] or (not learnt and steps!=0):
                groups.setdefault(('mastered',fields['mastered']),[]).append(identity)
    if groups:
        from .picto_startup_batch import run,ProgressionOwner
        batch_owner=ProgressionOwner(scope,catalog,owned,gi,table)
        batch_start=time.perf_counter()
        for (kind,target),ids in groups.items():
            if kind=='level':
                changed=run(batch_owner,ids,level=(target,one(live('BP_ItemUpgradeSystem_C')),
                            fn('BP_ItemInstance_Gear_C','ChangeLevel')))
                batched_levels.update(ids)
            else:
                changed=run(batch_owner,ids,mastery=(target,character,
                            fn('BP_CharacterData_C','SetPassiveEffectSharedProgression'),table))
                batched_mastery.update(ids)
            applied.extend([identity,kind] for identity in changed)
        batch_ms=(time.perf_counter()-batch_start)*1000
    for identity, item in inventory.items():
        fields = profiles[identity]
        # Level first, then explicit stat overrides, so rebuilding level stats
        # cannot overwrite a requested multiplier.
        # owned_pictos already validated each definition, serial and level.
        # Mutation APIs revalidate identities; avoid 210 redundant round trips.
        if 'level' in fields and identity not in batched_levels:
            current = owned[identity][1]
            if current != fields['level']:
                change(scope, 4, item, fn('BP_ItemInstance_Gear_C', 'ChangeLevel'),
                    None, None, None, current, fields['level'])
                applied.append([identity, 'level'])
        multipliers = fields.get('multipliers', {})
        if multipliers:
            current = dict(field(read_values(catalog, item), 'BaseStatsMultipliers').items)
            for key, value in multipliers.items():
                if current.get(int(key)) != value:
                    call(item, 'BP_ItemInstance_Gear_C', 'SetBaseStatsMultiplier', Stat=int(key), Value=value)
                    applied.append([identity, 'multipliers', key])
            call(item, 'BP_ItemInstance_Gear_C', 'RefreshCurrentGearStats')
            values=read_values(catalog,item)
            observed = dict(field(values, 'BaseStatsMultipliers').items)
            if any(abs(observed[int(k)] - v) > 1e-6 for k, v in multipliers.items()):
                raise RuntimeError('Restored Picto multiplier readback mismatch')
            stats=dict(field(values,'CurrentStats').items)
            for key,value in multipliers.items():
                if value==0 and stats.get(int(key),0)!=0:
                    change(scope,9,item,fn('BP_ItemInstance_Gear_C','SetCurrentStatValue'),
                        None,None,None,int(stats[int(key)]),int(key))
                    applied.append([identity,'multipliers',key])
            if 'stat_keys' in fields:
                remove_fn=fn('BlueprintMapLibrary','Map_Remove')
                for selector,name,keep in ((1,'CurrentStats',fields['stat_keys']),
                                           (2,'BaseStatsMultipliers',fields['multiplier_keys'])):
                    existing=dict(field(read_values(catalog,item),name).items)
                    for key in existing.keys()-set(keep):
                        change(scope,12,item,remove_fn,None,None,None,selector,key)
                        applied.append([identity,'multipliers',str(key)])
                    if set(field(read_values(catalog,item),name).items)!=set(keep):
                        raise RuntimeError('Restored Picto stat membership mismatch')
        if 'cost' in fields:
            cost_fn = fn('BP_CharacterData_C', 'RefreshUsedLuminaPointsInternal')
            current = change(scope, 7, table, cost_fn, item, None, character, 0, 0)
            if current != fields['cost']:
                change(scope, 6, table, cost_fn, item, None, character, current, fields['cost'])
                applied.append([identity, 'cost'])
        if 'mastered' in fields and identity not in batched_mastery:
            mastered,steps = progress(identity)
            if mastered != fields['mastered'] or ('mastery_steps' in fields and steps != fields['mastery_steps']):
                target = change(scope, 8, table, fn('BP_CharacterData_C', 'RefreshUsedLuminaPointsInternal'),
                    item, None, character, 0, 0) if fields['mastered'] else 0
                if 'mastery_steps' in fields:target=fields['mastery_steps']
                change(scope, 5, character, fn('BP_CharacterData_C', 'SetPassiveEffectSharedProgression'),
                    item, None, gi, steps, target)
                applied.append([identity, 'mastered'])
    if any(row[1] in ('multipliers', 'level') for row in applied):
        for character in characters:
            call(character, 'BP_CharacterData_C', 'UpdateEquipmentStats')
    if ownership is not None:
        applied.extend([identity, 'owned'] for identity in restore_ownership(False))
    intentionally_absent = {identity for identity, fields in profiles.items() if fields.get('owned') is False}
    return {'applied': applied, 'missing': sorted(set(profiles) - set(inventory) - intentionally_absent),
            'discovery_ms': round(discovery_ms, 1), 'inventory_ms': round(inventory_ms, 1),
            'resolve_ms': round(resolve_ms, 1),
            'batch_ms': round(batch_ms, 1), 'batch_groups': len(groups),
            'elapsed_ms': round((time.perf_counter() - started) * 1000, 1)}
