import unittest
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33.values import read_values_many
import test_values


class ValueBatchTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_values.ValueTests()
        self.fixture.setUp()
        self.fixture.property('CurrentLevel', 'IntProperty')
        self.fixture.value('CurrentLevel', 33)

    def test_projection_uses_validated_identity_and_one_query(self):
        f = self.fixture
        with patch('expedition33.values._query', return_value=({'pid': 123}, f.rows)) as query:
            result = read_values_many(f.catalog, [f.obj], fields=('CurrentLevel',))
        self.assertEqual(result[f.obj.index].values[2, 'CurrentLevel'], 33)
        query.assert_called_once_with(['--read-values', '123',
            f'{f.obj.index}:{f.obj.serial}:{f.obj.address:x};CurrentLevel'])

    def test_missing_duplicate_and_recycled_responses_fail(self):
        f = self.fixture
        for rows in ([], f.rows + f.rows, [dict(f.rows[0], serial=999), *f.rows[1:]]):
            with self.subTest(rows=rows), patch('expedition33.values._query', return_value=({'pid':123}, rows)):
                with self.assertRaises(RuntimeQueryError):
                    read_values_many(f.catalog, [f.obj])

    def test_invalid_projection_and_duplicate_targets_never_query(self):
        f = self.fixture
        with patch('expedition33.values._query', side_effect=AssertionError('must not query')):
            for fields in ((), ('A', 'A'), ('A|B',), ('A\n',)):
                with self.assertRaises(ValueError):
                    read_values_many(f.catalog, [f.obj], fields=fields)
            with self.assertRaises(ValueError):
                read_values_many(f.catalog, [f.obj, f.obj])
