import unittest
from types import SimpleNamespace
from expedition33.values import StoredArray, StoredMap
from expedition33.cinematics.title_adapters import require_empty_container


class EmptyContainerAdmissionTests(unittest.TestCase):
    def observation(self, value, *, error=None, truncated=False, kind='MapProperty'):
        key = (71, 'InteractiveMusicByContext')
        return SimpleNamespace(values={key: value}, errors={key: error} if error else {},
            types={key: kind}, truncated={key} if truncated else set())

    def test_complete_empty_map_is_accepted(self):
        require_empty_container(self.observation(StoredMap({})), 'InteractiveMusicByContext', StoredMap)

    def test_native_unsupported_error_is_visible_and_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'MAP_ELEMENT_TYPE_UNSUPPORTED'):
            require_empty_container(self.observation(None, error='MAP_ELEMENT_TYPE_UNSUPPORTED'),
                                    'InteractiveMusicByContext', StoredMap)

    def test_error_alongside_empty_value_still_rejects(self):
        with self.assertRaisesRegex(RuntimeError, 'stale'):
            require_empty_container(self.observation(StoredMap({}), error='stale'),
                                    'InteractiveMusicByContext', StoredMap)

    def test_truncated_nonempty_and_wrong_kind_reject(self):
        cases = (self.observation(StoredMap({}), truncated=True), self.observation(StoredMap({1: object()})),
                 self.observation(StoredArray((), 0), kind='ArrayProperty'))
        for case in cases:
            with self.assertRaises(RuntimeError):
                require_empty_container(case, 'InteractiveMusicByContext', StoredMap)

    def test_array_total_extent_must_be_zero_not_just_copied_items(self):
        require_empty_container(self.observation(StoredArray((), 0), kind='ArrayProperty'),
                                'InteractiveMusicByContext', StoredArray)
        with self.assertRaises(RuntimeError):
            require_empty_container(self.observation(StoredArray((), 3), kind='ArrayProperty'),
                                    'InteractiveMusicByContext', StoredArray)

    def test_ambiguous_owner_fields_reject(self):
        data = self.observation(StoredMap({}))
        data.types[(72, 'InteractiveMusicByContext')] = 'MapProperty'
        with self.assertRaisesRegex(RuntimeError, 'ambiguous'):
            require_empty_container(data, 'InteractiveMusicByContext', StoredMap)


if __name__ == '__main__':
    unittest.main()
