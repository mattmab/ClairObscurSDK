"""Catalog identity/graph validation; real-game behavior has separate live proof."""
from dataclasses import replace
import unittest

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog, CatalogObject, ClassRelation


def fixture():
    classes = [ClassRelation(0, 1, 'Object', -1, 40),
               ClassRelation(1, 1, 'Class', 0, 128),
               ClassRelation(2, 1, 'Actor', 0, 160),
               ClassRelation(3, 1, 'BP_Actor_C', 2, 176)]
    def obj(index, name, cls, outer=-1):
        return CatalogObject(123, index, 1, 4096 + index * 256, name,
            classes[cls].name, 'Class', cls, outer, 1 if outer >= 0 else 0, 0, 0)
    objects = [obj(i, cls.name, 1) for i, cls in enumerate(classes)]
    objects += [obj(4, 'ActorInstance', 2), obj(5, 'ActorInstance', 3, 4)]
    return objects, classes


class CatalogTests(unittest.TestCase):
    def test_combined_closure_matches_full_revalidation_without_mutating_inputs(self):
        objects, classes = fixture()
        old = Catalog(123, objects[:-1], classes)
        observed = Catalog(123, objects, classes)
        merged = old.with_observations(observed)
        rebuilt = Catalog(123, merged.objects, tuple(merged.classes.values()))
        self.assertEqual(merged.objects, rebuilt.objects)
        self.assertEqual(merged.classes, rebuilt.classes)
        for cls in classes:
            self.assertEqual(merged.ancestors(cls.index), rebuilt.ancestors(cls.index))
            self.assertEqual(merged.select(cls.name), rebuilt.select(cls.name))
        self.assertEqual(merged.outer_chain(merged.by_index[5]), rebuilt.outer_chain(rebuilt.by_index[5]))
        self.assertNotIn(5, old.by_index)
        changed = Catalog(123, [replace(o, outer_index=-1, outer_serial=0) if o.index == 5 else o
                               for o in objects], classes)
        updated = merged.with_observations(changed)
        self.assertEqual(len(updated.outer_chain(updated.by_index[5])), 1)
        self.assertEqual(len(merged.outer_chain(merged.by_index[5])), 2)

    def test_combined_new_class_keeps_ambiguity_checks_and_old_name_index(self):
        objects, classes = fixture()
        old = Catalog(123, objects[:3] + [objects[4]], classes[:3])
        classes[3] = replace(classes[3], name='Actor')
        objects[3] = replace(objects[3], name='Actor')
        objects[5] = replace(objects[5], class_name='Actor')
        merged = old.with_observations(Catalog(123, objects, classes))
        with self.assertRaises(RuntimeQueryError): merged.find_class('Actor')
        self.assertEqual(old.find_class('Actor').index, 2)
        self.assertEqual(merged.ancestors(3), (3, 2, 0))

    def test_subclass_and_ownership(self):
        c = Catalog(123, *fixture())
        self.assertEqual([o.index for o in c.select('Actor')], [4, 5])
        self.assertEqual([o.index for o in c.select('Actor', exact=True)], [4])
        self.assertEqual([o.index for o in c.outer_chain(c.by_index[5])], [4, 5])
        self.assertEqual(len(c.select()), 6)

    def test_recycled_identity_and_pid(self):
        c = Catalog(123, *fixture()); old = c.by_index[5]
        for stale in (replace(old, serial=2), replace(old, pid=124),
                      replace(old, address=9999), replace(old, class_index=2)):
            with self.assertRaises(RuntimeQueryError): c.resolve(stale)

    def test_missing_or_recycled_outer_rejected(self):
        objects, classes = fixture()
        objects[-1] = replace(objects[-1], outer_serial=5)
        with self.assertRaises(RuntimeQueryError): Catalog(123, objects, classes)

    def test_inheritance_cycle_and_missing_parent(self):
        for parent in (3, 999):
            objects, classes = fixture()
            classes[2] = replace(classes[2], super_index=parent)
            with self.assertRaises(RuntimeQueryError): Catalog(123, objects, classes)

    def test_ownership_cycle_and_duplicate_class_name(self):
        objects, classes = fixture()
        objects[-2] = replace(objects[-2], outer_index=5, outer_serial=1)
        c = Catalog(123, objects, classes)
        with self.assertRaises(RuntimeQueryError): c.outer_chain(c.by_index[5])
        objects, classes = fixture()
        classes[3] = replace(classes[3], name='Actor')
        objects[3] = replace(objects[3], name='Actor')
        objects[5] = replace(objects[5], class_name='Actor')
        c = Catalog(123, objects, classes)
        with self.assertRaises(RuntimeQueryError): c.find_class('Actor')

    def test_package_and_subobject_path_separators(self):
        objects, classes = fixture()
        # Replace the fixture's spare derived class with Package.
        classes[3] = replace(classes[3], name='Package', super_index=0)
        objects[3] = replace(objects[3], name='Package')
        objects[4] = replace(objects[4], name='/Game/Test', class_index=3, class_name='Package')
        objects[5] = replace(objects[5], name='World', class_index=2, class_name='Actor')
        objects.append(replace(objects[5], index=6, address=6000, name='PersistentLevel', outer_index=5))
        objects.append(replace(objects[5], index=7, address=7000, name='Actor', outer_index=6))
        c = Catalog(123, objects, classes)
        self.assertEqual(c.path_name(objects[-1]), '/Game/Test.World:PersistentLevel.Actor')
        self.assertEqual(c.find_path('/Game/Test.World', 'Actor').index, 5)


if __name__ == '__main__': unittest.main()
