"""Compact four-stat equipped cards using verified native widget references."""
import time
from collections import Counter
from .catalog import capture_matching, capture_selected
from . import values, RuntimeQueryError


def get(result, name):
    keys = [key for key in result.values if key[1] == name]
    if len(keys) != 1:
        raise RuntimeQueryError('Missing Picto card field: ' + name)
    return result.values[keys[0]]


class PictoCardLayout:
    def __init__(self, editor):
        self.e = editor
        self.next_scan = 0
        self.pending = None
        self.saved = {}
        self.labels_reset = False
        self.planner = None

    def adopt(self, catalog):
        # Card widgets belong to the game and can be rebuilt independently of
        # our owned editor buttons. Keep their observations out of that planner.
        if self.planner is None:
            metadata = catalog.subset(o for o in catalog.objects if o.index in catalog.classes or
                o.class_name in ('Function', 'Enum', 'UserDefinedEnum', 'ScriptStruct', 'UserDefinedStruct'))
            self.e.planner.adopt_observations(metadata)
            self.planner = self.e.scope.invocation_planner(selected_results=True, catalog=catalog)
        else:
            self.planner.refresh_from(catalog)

    def call(self, obj, owner, name, **arguments):
        with self.planner.prepare(obj, self.e.fn(owner, name), **arguments).invoke() as result:
            return result.return_value

    def observe(self, catalog):
        # Called on the editor's existing read-only worker, not the UI thread.
        if time.monotonic() < self.next_scan:
            return
        self.next_scan = time.monotonic() + 1.
        e = self.e
        fresh = capture_matching(e.pid, classes=('WBP_PictoCombatStat_C',),
            names=('WBP_WrappingText_C', 'SizeBox', 'SetWidthOverride',
                   'ClearWidthOverride', 'DynamicEntryBoxBase',
                   'GetNumEntries', 'WBP_PictoCartridge_C'))
        prefix = catalog.path_name(e.panel) + '.'
        rows = [o for o in fresh.select('WBP_PictoCombatStat_C')
                if not o.object_flags & 0x30 and fresh.path_name(o).startswith(prefix)
                and any('.WBP_PictoSlot' + str(i) + '.' in fresh.path_name(o) for i in range(3))]
        # Exact-name discovery also matches transient SizeBox instances. Never
        # retain unrelated widget slots in the editor's long-lived planner.
        keep = {o.index for o in rows}
        fresh = fresh.subset(o for o in fresh.objects if o.index in keep or
            o.index in fresh.classes or o.class_name == 'Function')
        c = catalog.with_observations(fresh)
        counts = Counter(o.outer_index for o in rows)
        result = []
        def ref(obj, owner, name):
            nonlocal c
            found, c = values.read_object_reference(c, obj,
                c.by_index[c.find_class(owner).index], name, project=True)
            if found is None:
                raise RuntimeQueryError('Missing Picto card widget: ' + name)
            return found
        entry_lists = {}
        for outer, count in counts.items():
            if count >= 4:
                tree = c.by_index[outer]
                cartridge = c.by_index[tree.outer_index]
                if cartridge.class_name != 'WBP_PictoCartridge_C':
                    raise RuntimeQueryError('Unexpected Picto stat owner')
                entry_lists[outer] = ref(cartridge, 'WBP_PictoCartridge_C', 'StatsList')
        for row in rows:
            rv = values.read_values_many(c, (row,), fields=('StatType',))[row.index]
            wrapper = ref(row, 'WBP_PictoCombatStat_C', 'StatLabel')
            label = ref(wrapper, 'WBP_WrappingText_C', 'Text')
            box = ref(wrapper, 'WBP_WrappingText_C', 'TextSizeBox')
            bv = values.read_values_many(c, (box,), fields=('WidthOverride','bOverride_WidthOverride'))[box.index]
            lv = values.read_values_many(c, (label,), fields=('RenderTransform',))[label.index]
            scale = dict(get(lv,'RenderTransform').fields['Scale'].fields)
            result.append((wrapper, label, box, get(rv,'StatType'), row.outer_index,
                           get(bv,'WidthOverride'), get(bv,'bOverride_WidthOverride'), scale))
        self.pending = c, result, counts, entry_lists

    def apply(self):
        if self.pending is None:
            return
        c, rows, counts, entry_lists = self.pending
        self.pending = None
        e = self.e
        self.adopt(c)
        if not self.labels_reset:
            # Clear display-only labels left by earlier editor versions using
            # the verified game-owned refresh, preserving localized names.
            for slot in range(3):
                self.call(e.panel, 'WBP_Panel_Pictos_C', 'RefreshSlotData', InSlotIndex=slot)
            self.labels_reset = True
            return  # Observe the refreshed widget pool before formatting it.
        # DynamicEntryBox retains inactive pooled widgets. Count active entries,
        # not every still-live UObject, when a character changes equipment.
        for outer, entries in entry_lists.items():
            counts[outer] = self.call(entries, 'DynamicEntryBoxBase', 'GetNumEntries')
        for wrapper, label, box, stat, outer, width, enabled, scale in rows:
            count = counts[outer]
            key = (box.index, box.address)
            previous = self.saved.get(key)
            if previous is not None:
                # Initially unassigned UObject serials become assigned when
                # native calls retain references. Preserve the original layout
                # across that promotion, but never across a recycled serial.
                if previous[1].serial not in (0, box.serial):
                    self.saved.pop(key)
                else:
                    self.saved[key] = (wrapper, box, previous[2], previous[3], label, previous[5])
            if count < 4:
                if key in self.saved:
                    self.restore(self.saved.pop(key))
                continue
            if key not in self.saved:
                # Recover this mod's exact layout signature after an older
                # controller failed cleanup. Stock defaults were captured live:
                # no width override and unit render scale.
                leftover = enabled and width == 64. and any(all(abs(scale[k]-size)<1e-6 for k in ('X','Y')) for size in (.8,.68))
                self.saved[key] = (wrapper, box, width, False if leftover else enabled,
                                   label, {'X':1.,'Y':1.} if leftover else scale)
            # 4 * 64 + 3 * 5 spacing + the 42-unit level column fits 330.
            if not enabled or width != 64.:
                self.call(box, 'SizeBox', 'SetWidthOverride', InWidthOverride=64.)
            if any(abs(scale[k] - .68) > 1e-6 for k in ('X','Y')):
                self.call(label, 'Widget', 'SetRenderScale', Scale={'X':.68,'Y':.68})

    def restore(self, saved):
        wrapper, box, width, enabled, label, scale = saved
        e = self.e
        if enabled:
            self.call(box, 'SizeBox', 'SetWidthOverride', InWidthOverride=width)
        else:
            self.call(box, 'SizeBox', 'ClearWidthOverride')
        self.call(label, 'Widget', 'SetRenderScale', Scale=scale)

    def close(self):
        e = self.e
        for saved in self.saved.values():
            try:
                fresh = capture_selected(e.pid, tuple((o.index,o.serial,o.address) for o in (saved[0],saved[1],saved[4])))
            except RuntimeQueryError:
                continue  # Destroyed menu objects have no layout to restore.
            self.adopt(e.planner._catalog.with_observations(fresh))
            self.restore(saved)
        changed = bool(self.saved)
        self.saved.clear()
        if changed and e.panel is not None:
            try:
                fresh = capture_selected(e.pid, ((e.panel.index,e.panel.serial,e.panel.address),))
            except RuntimeQueryError:
                return
            self.adopt(e.planner._catalog.with_observations(fresh))
            for slot in range(3):
                self.call(e.panel, 'WBP_Panel_Pictos_C', 'RefreshSlotData', InSlotIndex=slot)
        if self.planner is not None:
            self.planner.close()
