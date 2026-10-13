"""Incremental bulk level/mastery edits over an explicit owned-inventory snapshot."""
from .picto_inventory import owned_pictos
from .picto_restore import field
from .values import read_values_many
from .picto_progression import change


class PictoBulkJob:
    def __init__(self, scope, catalog, mode, value, preferences):
        if mode not in ('level', 'mastery'):
            raise ValueError('Unsupported Picto bulk operation')
        if mode == 'level' and (type(value) is not int or not 1 <= value <= 33):
            raise ValueError('Picto level must be 1–33')
        if mode == 'mastery' and type(value) is not bool:
            raise ValueError('Bulk mastery requires a boolean')
        self.scope, self.mode, self.value, self.preferences = scope, mode, value, preferences
        self.catalog, self.owned = owned_pictos(scope.pid, catalog=catalog)
        self.queue = list(sorted(self.owned))
        self.total = len(self.queue)
        self.completed = 0
        self.error = None
        self.done = False
        self.confirmed = []
        self.planner = scope.invocation_planner(selected_results=True, catalog=self.catalog)
        self.characters = [o for o in self.catalog.select('BP_CharacterData_C') if not o.object_flags & 0x30]
        self.gi = self.one(o for o in self.catalog.select('BP_jRPG_GI_Custom_C') if not o.object_flags & 0x30)
        self.table = self.one(o for o in self.catalog.objects if o.class_name == 'DataTable' and
            self.catalog.path_name(o) == '/Game/Gameplay/Lumina/DT_PassiveEffects.DT_PassiveEffects')
        if not self.characters:
            raise RuntimeError('No live characters for bulk Picto editing')

    @staticmethod
    def one(rows):
        rows = tuple(rows)
        if len(rows) != 1:
            raise RuntimeError('Ambiguous bulk Picto dependency')
        return rows[0]

    def fn(self, owner, name):
        cls = self.catalog.find_class(owner)
        return self.one(o for o in self.catalog.objects if o.outer_index == cls.index and o.name == name)

    def read(self, obj, *names):
        return read_values_many(self.catalog, (obj,), fields=names)[obj.index]

    def tick(self):
        """Process one Picto. A failure terminates the job and is never retried."""
        if self.done:
            return
        try:
            if not self.queue:
                if self.mode == 'level':
                    for character in self.characters:
                        with self.planner.prepare(character, self.fn('BP_CharacterData_C', 'UpdateEquipmentStats')).invoke():
                            pass
                self.done = True
                return
            identity = self.queue[0]
            item, _ = self.owned[identity]
            # Re-read membership so removal/replacement during a running job
            # cannot turn a loaded stale object into a bulk-edit target.
            fresh, owned = owned_pictos(self.scope.pid, catalog=self.catalog)
            current = owned.get(identity)
            if current is None or (current[0].index, current[0].serial, current[0].address) != (item.index, item.serial, item.address):
                raise RuntimeError('Picto ownership changed during bulk edit: ' + identity)
            self.catalog = fresh
            self.planner.adopt_observations(fresh)
            if self.mode == 'level':
                if current[1] != self.value:
                    change(self.scope, 4, item, self.fn('BP_ItemInstance_Gear_C', 'ChangeLevel'),
                           None, None, None, current[1], self.value)
            else:
                shared = field(self.read(self.gi, 'SharedPassiveEffectProgression'), 'SharedPassiveEffectProgression').items
                progress = shared.get(identity)
                mastered = progress.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if progress else False
                steps = progress.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F'] if progress else 0
                if mastered!=self.value or (not self.value and steps!=0):
                    target = change(self.scope, 8, self.table, self.fn('BP_CharacterData_C', 'RefreshUsedLuminaPointsInternal'),
                                    item, None, self.characters[0], 0, 0) if self.value else 0
                    change(self.scope, 5, self.characters[0], self.fn('BP_CharacterData_C', 'SetPassiveEffectSharedProgression'),
                           item, None, self.gi, steps, target)
                    after = field(self.read(self.gi, 'SharedPassiveEffectProgression'), 'SharedPassiveEffectProgression').items.get(identity)
                    if (after.fields['IsLearnt_9_2561000E49D90653437DE9A45BE2A86D'] if after else False)!=self.value or (not self.value and after and after.fields['LearntSteps_6_A14D681549E830249C77BD95F2B4CF3F']!=0):
                        raise RuntimeError('Bulk mastery did not read back as requested: ' + identity)
            self.preferences.remember(identity, self.mode, self.value)
            self.confirmed.append(identity)
            self.queue.pop(0)
            self.completed += 1
        except Exception as error:
            self.error = str(error)
            self.done = True
            raise
