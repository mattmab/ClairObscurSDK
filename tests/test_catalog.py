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


if __name__ == '__main__': unittest.main()
