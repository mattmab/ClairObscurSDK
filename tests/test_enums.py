"""Enum observations reject stale identities and malformed/incomplete replies."""
import copy
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError
from expedition33.catalog import Catalog
from expedition33.enums import describe_enums
from test_catalog import fixture


class EnumTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog(123, *fixture())
        self.obj = self.catalog.by_index[2]
        self.rows = [dict(event='object', index=2, serial=self.obj.serial,
                          address=hex(self.obj.address), name=self.obj.name,
                          class_index=self.obj.class_index),
                     dict(event='enum_metadata', index=2, members=[
                         dict(name='Negative', value=-1), dict(name='Alias', value=-1),
                         dict(name='Large', value=(1 << 63) - 1)])]

    def read(self, rows, pid=123):
        with patch('expedition33.enums._query', return_value=({'pid': pid}, rows)):
            return describe_enums(self.catalog, [self.obj])

    def test_signed_values_aliases_and_immutable_result(self):
        result = self.read(self.rows)
        self.assertEqual([m.value for m in result[2].members], [-1, -1, (1 << 63) - 1])
        with self.assertRaises(TypeError):
            result[3] = result[2]

    def test_stale_process_and_identity(self):
        with self.assertRaises(RuntimeQueryError):
            self.read(self.rows, pid=124)
        for key, value in [('index', 999), ('serial', 99), ('address', '0x1'),
                           ('name', 'Recycled'), ('class_index', 999)]:
            rows = copy.deepcopy(self.rows)
            rows[0][key] = value
            with self.subTest(key=key), self.assertRaises(RuntimeQueryError):
                self.read(rows)

    def test_missing_duplicate_or_unowned_metadata(self):
        for rows in [[], self.rows[:1], self.rows[1:], self.rows * 2,
                     [self.rows[0], self.rows[0], self.rows[1]]]:
            with self.subTest(rows=rows), self.assertRaises(RuntimeQueryError):
                self.read(rows)

    def test_invalid_members(self):
        for member in [dict(name='', value=0), dict(name='Negative', value=0),
                       dict(name='Bad', value=True), dict(name='Bad', value=1 << 63),
                       dict(name='Bad', value=-(1 << 63) - 1)]:
            rows = copy.deepcopy(self.rows)
            rows[1]['members'].append(member)
            with self.subTest(member=member), self.assertRaises(RuntimeQueryError):
                self.read(rows)


if __name__ == '__main__':
    unittest.main()
