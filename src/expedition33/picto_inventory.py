"""Identity-validated Picto ownership from the game's authoritative item map."""
from .catalog import capture_matching
from .values import read_values_with_references, read_values_many
from .picto_restore import field
from .picto_gameplay import GAMEPLAY_PICTOS

STATIC_TABLE = '/Game/jRPGTemplate/Datatables/DT_jRPG_Items_Composite.DT_jRPG_Items_Composite'
DEFINITION_TABLE = '/Game/Gameplay/Pictos/DT_PictosDefinitions.DT_PictosDefinitions'


def one(rows):
    rows = tuple(rows)
    if len(rows) != 1:
        raise RuntimeError('Ambiguous Picto inventory dependency')
    return rows[0]


def discover_inventory(pid):
    return capture_matching(pid, names=('DT_jRPG_Items_Composite', 'DT_PictosDefinitions',
        'AddItemToInventory', 'RemoveItemFromInventory', 'LoadCharacter', 'FPassiveEffectProgression'), classes=(
        'BP_ItemUpgradeSystem_C', 'AC_jRPG_InventoryManager_C', 'BP_DataAsset_Item_Pictos_C',
        'BP_jRPG_GI_Custom_C', 'BP_CharacterData_C', 'WBP_Panel_Pictos_C'))


def definitions(catalog):
    """Read both canonical tables; unknown IDs are always experimental.

    Normal eligibility is an audited allowlist intersected with live definition
    and static inventory rows, with a unique nonhidden Picto asset per ID.
    """
    from .values import read_table_rows
    static = one(o for o in catalog.objects if catalog.path_name(o) == STATIC_TABLE)
    definition = one(o for o in catalog.objects if catalog.path_name(o) == DEFINITION_TABLE)
    rows = read_table_rows(catalog, static)
    result = {}
    for identity, row in read_table_rows(catalog, definition).items():
        if field(row, 'ItemID_8_0C609E93404384CE551651849CB4CA43') != identity:
            raise RuntimeError('Picto definition row identity mismatch')
        data = rows.get(identity)
        asset = None
        if data is not None and field(data, 'Item_HardcodedName_90_C7F763B74AAB28EF890A66854D7D95AA') == identity and field(data, 'Item_Type_88_2F24F8FB4235429B4DE1399DBA533C78') == 2 and not field(data, 'HideInInventory_105_28F500C94EA8D5C6632F7E8E4A85586E'):
            asset = field(data, 'Pictos_Data_103_EE44D66B4E4F16A7FD44FF9F25777CF4')
            if asset is not None and asset.class_name != 'BP_DataAsset_Item_Pictos_C':
                raise RuntimeError('Invalid Picto asset class')
        result[identity] = {'id': identity, 'name': GAMEPLAY_PICTOS.get(identity, identity),
                            'asset': asset, 'normal': identity in GAMEPLAY_PICTOS and asset is not None}
    assets = {}
    for entry in result.values():
        asset = entry['asset']
        if asset is not None:
            assets.setdefault((asset.index, asset.serial, asset.address), []).append(entry)
    for entries in assets.values():
        if len(entries) > 1:
            for entry in entries:
                entry['normal'] = False
    return result


def prepare_ownership(pid, catalog=None):
    """Read a detached ownership snapshot without touching an owner-thread scope.

    Run under the caller's pinned read-only reader. Native mutation dependencies
    retain their captured identities and are revalidated by the native API.
    """
    if type(pid) is not int or pid <= 0:
        raise ValueError('Expected a positive game process ID')
    catalog = catalog or discover_inventory(pid)
    rows = definitions(catalog)
    table = one(o for o in catalog.objects if catalog.path_name(o) == STATIC_TABLE)
    manager = one(o for o in catalog.select('AC_jRPG_InventoryManager_C') if not o.object_flags & 0x30)
    gi = one(o for o in catalog.select('BP_jRPG_GI_Custom_C') if not o.object_flags & 0x30)
    catalog, owned = owned_pictos(pid, catalog=catalog)
    return dict(pid=pid, catalog=catalog, rows=rows, table=table,
                manager=manager, gi=gi, owned=owned)


class PictoOwnership:
    """Explicit ownership changes using guarded stock inventory operations."""
    def __init__(self, scope, catalog=None, *, snapshot=None):
        self.scope = scope
        # Access the scope only on its owner thread, including construction.
        self.pid = scope.pid
        if snapshot is not None and catalog is not None:
            raise ValueError('Supply either a catalog or a prepared snapshot')
        if snapshot is None:
            snapshot = prepare_ownership(self.pid, catalog)
        if type(snapshot.get('pid')) is not int or snapshot['pid'] != self.pid:
            raise ValueError('Picto ownership snapshot belongs to a different process')
        self.catalog = snapshot['catalog']
        self.rows = {key: dict(row) for key, row in snapshot['rows'].items()}
        self.table, self.manager, self.gi = (snapshot[key] for key in ('table', 'manager', 'gi'))
        self.owned = dict(snapshot['owned'])

    def refresh(self):
        # Removal/addition can recycle UObject slots held by the old catalog.
        # Refresh identities, including dispatch dependencies, before reading
        # new ItemInstances; never merge recycled objects into old observations.
        self.catalog, self.owned = owned_pictos(self.pid, catalog=discover_inventory(self.pid))
        return self.owned

    def function(self, owner, name):
        cls = self.catalog.find_class(owner)
        return one(o for o in self.catalog.objects if o.outer_index == cls.index and o.name == name)

    def set_owned(self, identity, value, *, expected=None):
        from .picto_progression import change
        if type(value) is not bool or (expected is not None and type(expected) is not bool):
            raise ValueError('Picto ownership must be boolean')
        row = self.rows.get(identity)
        if row is None or not row['normal']:
            raise ValueError('Experimental/unverified Picto is excluded from gameplay unlock operations')
        self.refresh()
        before = identity in self.owned
        if expected is not None and before != expected:
            raise RuntimeError('Picto ownership changed; review before applying')
        if before == value:
            return False
        try:
            observed = change(self.scope, 10, self.manager, self.function('AC_jRPG_InventoryManager_C',
                'AddItemToInventory' if value else 'RemoveItemFromInventory'), row['asset'], self.table, self.gi, int(before), int(value))
        except RuntimeError as error:
            if 'error=1759,' in str(error):
                raise RuntimeError('Unequip this Picto from every expeditioner before removing it') from error
            raise
        self.refresh()
        if observed != int(value) or (identity in self.owned) != value:
            raise RuntimeError('Picto ownership readback mismatch; no automatic retry')
        return True

    def refresh_panel(self, panel, character):
        from .picto_progression import change
        change(self.scope, 11, panel, self.function('WBP_Panel_Pictos_C', 'LoadCharacter'), character, None, None, 0, 0)


class PictoUnlockJob:
    """Add missing gameplay Pictos incrementally; never alter existing levels."""
    mode = 'unlock'
    def __init__(self, ownership, preferences):
        self.ownership, self.preferences = ownership, preferences
        self.queue = sorted(k for k, row in ownership.rows.items() if row['normal'])
        self.total, self.completed = len(self.queue), 0
        self.confirmed, self.done, self.error = [], False, None

    def tick(self):
        if self.done:
            return
        if not self.queue:
            self.done = True
            return
        identity = self.queue[0]
        try:
            created = self.ownership.set_owned(identity, True)
            self.preferences.remember(identity, 'owned', True)
            if created:
                # A previously removed Picto may have a saved custom profile.
                # Restore it immediately, rather than waiting for another load.
                saved = {k: v for k, v in self.preferences.profiles.get(identity, {}).items()
                         if k != 'owned'}
                if saved:
                    from .picto_restore import restore
                    restore(self.ownership.scope, {identity: saved})
            self.confirmed.append(identity)
            self.queue.pop(0)
            self.completed += 1
        except Exception as error:
            self.done, self.error = True, str(error)
            raise


def owned_pictos(pid, *, catalog=None):
    """Return (catalog, definition -> (object, level)) for currently owned Pictos.

    Loaded transient item objects are deliberately not treated as inventory.
    Null, mismatched, duplicate and nonpositive-quantity entries fail closed.
    """
    if catalog is None:
        catalog = capture_matching(pid, classes=('BP_ItemUpgradeSystem_C',))
    systems = [o for o in catalog.select('BP_ItemUpgradeSystem_C')
               if o.class_name == 'BP_ItemUpgradeSystem_C' and not o.object_flags & 0x30]
    if len(systems) != 1:
        raise RuntimeError('Expected one live Picto inventory system')
    values, catalog = read_values_with_references(catalog, systems[0], fields=('ItemInstances',))
    entries = field(values, 'ItemInstances').items
    candidates = {key: obj for key, obj in entries.items()
                  if obj is not None and obj.class_name == 'BP_ItemInstance_Gear_Pictos_C'}
    if len({o.index for o in candidates.values()}) != len(candidates):
        raise RuntimeError('Duplicate Picto object in inventory')
    values = read_values_many(catalog, candidates.values(), fields=('ItemDefinitionID', 'Quantity', 'CurrentLevel'))
    owned = {}
    for key, obj in candidates.items():
        row = values[obj.index]
        if obj.object_flags & 0x30 or field(row, 'ItemDefinitionID') != key:
            raise RuntimeError('Owned Picto definition identity mismatch')
        quantity, level = field(row, 'Quantity'), field(row, 'CurrentLevel')
        if type(quantity) is not int or quantity < 0 or type(level) is not int or not 1 <= level <= 33:
            raise RuntimeError('Invalid owned Picto quantity or level')
        if quantity:
            owned[key] = (obj, level)
    return catalog, owned
