"""Read-only definition metadata for Picto browsing, using SDK value readers.

Call once on a reader worker and cache the returned plain records for the menu
session. No inventory instance is fabricated and no game function is invoked.
Definition multipliers are deliberately separate from level-dependent stats.
"""
import math

from .values import read_table_rows, read_values_many
from .picto_inventory import STATIC_TABLE, DEFINITION_TABLE
from .picto_restore import field

PASSIVE_TABLE = '/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects'
METADATA_NAMES = ('DT_PassiveEffects', 'FPassiveEffectDataTableRow', 'DataTableRowHandle')
ITEM_ID = 'ItemID_8_0C609E93404384CE551651849CB4CA43'
STATIC_ID = 'Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA'
STATIC_ASSET = 'Pictos_Data_103_EE44D66B4E4F16A7FD44FF9F25777CF4'
MULTIPLIERS = 'BaseStatMultipliers_14_BEEE70774FB9CCD9F9FD999535F779AC'
PASSIVE_ROW = 'Row_2_8FD54A69441F52BAEE473DB8C91D1621'
COST = 'LuminaCost_15_BC10A93D48987A14F96279AC521E94CF'
DESCRIPTION = 'Description_12_EEFC7EED42F5C4FA14BBD7B356617893'
STAT_NAMES = {1: 'health', 6: 'defense', 8: 'speed', 9: 'critical_rate'}


def _struct_member(value, name):
    if getattr(value, 'truncated', False) or name in value.errors:
        raise ValueError('Incomplete definition member: ' + name)
    return value.fields[name]


def _table(catalog, path):
    matches = [obj for obj in catalog.objects if
               obj.class_name in ('DataTable', 'CompositeDataTable') and catalog.path_name(obj) == path]
    if len(matches) != 1:
        raise ValueError('Definition table unavailable: ' + path)
    return read_table_rows(catalog, matches[0])


def definition_details(catalog, rows):
    """Return verified per-definition details, with explicit unavailable fields.

    ``catalog`` must include the three canonical tables, Picto data assets,
    and nested schemas in METADATA_NAMES (otherwise references fail closed).
    ``rows`` is PictoOwnership.rows, whose normal-gameplay eligibility remains
    authoritative. The caller owns the ReadBatch and any catalogue refresh.
    Field-level unsupported data is recorded in ``unavailable``; failed native
    reads and stale object identities propagate to the worker's error handler.
    The existing decoder cannot resolve FText history/string-table indirection,
    so descriptions stay unavailable unless that decoder returns a real string.
    """
    definitions = _table(catalog, DEFINITION_TABLE)
    static = _table(catalog, STATIC_TABLE)
    passive = _table(catalog, PASSIVE_TABLE)
    assets = {row['asset'].index: row['asset'] for row in rows.values() if row.get('asset') is not None}
    observed = read_values_many(catalog, assets.values(), fields=('PassiveEffects',))
    result = {}
    for identity, row in rows.items():
        data = {'identity': identity, 'name': row['name'], 'normal': row['normal'],
                'effect': None, 'cost': None, 'acquisition': None,
                'health': None, 'defense': None, 'speed': None, 'critical_rate': None,
                'base_stat_multipliers': {}, 'effect_references': [],
                'unavailable': {'acquisition': 'No verified acquisition mapping',
                                'stats': 'Inventory level required for numerical stat values'}}
        result[identity] = data
        try:
            definition = definitions[identity]
            if field(definition, ITEM_ID) != identity:
                raise ValueError('Definition identity mismatch')
            multipliers = field(definition, MULTIPLIERS).items
            for key, name in STAT_NAMES.items():
                number = multipliers.get(key)
                if type(number) in (int, float) and math.isfinite(number) and number >= 0:
                    data['base_stat_multipliers'][name] = number
        except (KeyError, RuntimeError, ValueError, AttributeError) as error:
            data['unavailable']['definition'] = str(error)
            continue
        try:
            asset = row.get('asset')
            if asset is None:
                raise ValueError('No verified Picto asset')
            inventory_definition = static[identity]
            if field(inventory_definition, STATIC_ID) != identity or field(inventory_definition, STATIC_ASSET) != asset:
                raise ValueError('Static definition asset identity mismatch')
            references = field(observed[asset.index], 'PassiveEffects')
            if len(references.items) != len(references):
                raise ValueError('Incomplete passive effect references')
            costs, descriptions = [], []
            for reference in references:
                handle = _struct_member(reference, PASSIVE_ROW)
                table = _struct_member(handle, 'DataTable')
                key = _struct_member(handle, 'RowName')
                if table is None or catalog.path_name(table) != PASSIVE_TABLE or type(key) is not str:
                    raise ValueError('Unverified passive effect reference')
                data['effect_references'].append({'table': PASSIVE_TABLE, 'row': key})
                definition = passive[key]
                cost = field(definition, COST)
                if type(cost) is not int or cost < 0:
                    raise ValueError('Invalid passive cost')
                costs.append(cost)
                try:
                    description = field(definition, DESCRIPTION)
                    if type(description) is not str or not description.strip():
                        raise ValueError('Effect text is not decoded')
                    descriptions.append(description)
                except (RuntimeError, ValueError):
                    data['unavailable']['effect'] = 'Reflected FText description is not supported by the stored-value reader'
            # A Picto with multiple passives has no verified aggregate-cost rule.
            if len(costs) == 1:
                data['cost'] = costs[0]
            else:
                data['unavailable']['cost'] = 'No verified single passive cost'
            if descriptions and len(descriptions) == len(costs):
                data['effect'] = '\n'.join(descriptions)
        except (KeyError, RuntimeError, ValueError, AttributeError) as error:
            data['unavailable']['passive'] = str(error)
    return result
