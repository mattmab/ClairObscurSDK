"""Original core provenance and adapted request lifecycle, separate from live proof."""
import hashlib
from pathlib import Path
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from expedition33.introspection import Harness, UnsupportedCapability, core


class IntrospectionTests(unittest.TestCase):
    def test_enum_typed_roundtrip_budget_and_retained_value(self):
        from expedition33.introspection import _Backend, _Explorer
        from expedition33.enums import EnumDescriptor, EnumMember
        from expedition33.catalog import Catalog
        from test_catalog import fixture
        backend = _Backend(SimpleNamespace(supports_retained_invocation=True, supports_enum_values=True))
        backend.catalog = Catalog(123, *fixture())
        obj = backend.catalog.by_index[2]
        descriptor = EnumDescriptor(obj, (EnumMember('E::Visible', 0), EnumMember('E::MAX', 1)))
        explorer = _Explorer(backend)
        with patch.object(backend, 'find_object', return_value=SimpleNamespace(_observed=obj)) as lookup, \
                patch('expedition33.introspection.describe_enums', return_value={obj.index: descriptor}), \
                patch.object(backend.catalog, 'path_name', return_value='/Script/Test.E'):
            value = explorer.decode({'$enum': {'type': '/Script/Test.E', 'name': 'E::Visible'}})
            lookup.assert_called_with('/Script/CoreUObject.Enum', '/Script/Test.E')
            encoded = explorer.encode(value)
            self.assertEqual(explorer.decode(encoded), value)
            self.assertEqual(explorer.decode([encoded]), [value])
            self.assertEqual(explorer.encode(value, budget=[0]), {'$truncated': 'node budget'})
            self.assertEqual(explorer.encode(value, depth=0)['$truncated'], 'depth')
            explorer.values['enum'] = value
            self.assertIs(explorer.decode({'$value': {'name': 'enum'}}), value)
            for number in (1, False, '0'):
                with self.assertRaises(ValueError):
                    explorer.decode({'$enum': dict(encoded['$enum'], value=number)})
            with self.assertRaises(ValueError):
                explorer.decode({'$enum': {'type': '/Script/Test.E', 'name': 'E::MAX'}})
        explorer.close()
        self.assertFalse(explorer.values)

    def test_enum_invalid_specs_and_capability_gate(self):
        from expedition33.introspection import _Backend, _Explorer
        backend = _Backend()
        explorer = _Explorer(backend)
        for spec in (None, {}, {'type': 'E', 'name': 'N'},
                     {'type': '/E', 'name': ''}, {'type': '/E', 'name': 'N\0'},
                     {'type': '/E', 'name': 'N', 'other': 1}):
            with self.assertRaises(ValueError): explorer.decode({'$enum': spec})
        with self.assertRaises(ValueError):
            explorer.decode({'$enum': {'type': '/E', 'name': 'N'}, '$value': {'name': 'other'}})
        with self.assertRaises(UnsupportedCapability):
            explorer.decode({'$enum': {'type': '/E', 'name': 'N'}})

    def test_enum_schema_bounded_copies_and_request_cache(self):
        from expedition33.introspection import _Backend
        from expedition33.enums import EnumDescriptor, EnumMember
        from expedition33.catalog import Catalog
        from test_catalog import fixture
        backend = _Backend()
        backend.catalog = Catalog(123, *fixture())
        obj = backend.catalog.by_index[2]
        enum = SimpleNamespace(_observed=obj)
        descriptor = EnumDescriptor(obj, tuple(EnumMember(f'N{i}', i) for i in range(130)))
        with patch('expedition33.introspection.describe_enums', return_value={obj.index: descriptor}) as reader:
            first = backend.enum_schema(enum)
            self.assertEqual(first['member_count'], 130)
            self.assertEqual(len(first['members']), 128)
            self.assertTrue(first['members_truncated'])
            first['members'][0]['value'] = -1
            self.assertEqual(backend.enum_schema(enum)['members'][0]['value'], 0)
            reader.assert_called_once()
        backend.clear()
        self.assertFalse(backend.enum_descriptors)

    def test_enum_schema_explicit_unavailable_and_inner_members(self):
        from expedition33 import RuntimeQueryError
        from expedition33.introspection import _Backend, _Explorer
        from expedition33.catalog import Catalog
        from test_catalog import fixture
        backend = _Backend()
        backend.catalog = Catalog(123, *fixture())
        enum = SimpleNamespace(_observed=backend.catalog.by_index[2], Name='E', path='/E')
        with patch('expedition33.introspection.describe_enums', side_effect=RuntimeQueryError('unsupported subclass')):
            detail = backend.enum_schema(enum)
            self.assertEqual(detail, {'members_error': 'unsupported subclass'})
        explorer = _Explorer(backend)
        explorer.ref = lambda obj: {'$object': obj.path}
        prop = SimpleNamespace(Name='Value', Class=SimpleNamespace(Name='EnumProperty'),
            PropertyFlags=0, ArrayDim=1, Offset_Internal=100, Enum=enum,
            Inner=SimpleNamespace(Name='Element', Class=SimpleNamespace(Name='ByteProperty'),
                                 ElementSize=1, Enum=enum))
        schema = explorer.prop_schema(prop)
        self.assertEqual(schema['Enum']['members_error'], 'unsupported subclass')
        self.assertEqual(schema['Inner']['Enum']['members_error'], 'unsupported subclass')

    def test_inner_schema_preserves_verified_type_identity(self):
        from expedition33.introspection import _Explorer
        explorer = _Explorer(SimpleNamespace())
        explorer.ref = lambda obj: {'$object': obj.path}
        prop = SimpleNamespace(Name='ConsoleKeys', Class=SimpleNamespace(Name='ArrayProperty'),
            PropertyFlags=0, ArrayDim=1, Offset_Internal=100,
            Inner=SimpleNamespace(Name='ConsoleKeys', Class=SimpleNamespace(Name='StructProperty'),
                ElementSize=24, Struct=SimpleNamespace(path='/Script/InputCore.Key')))
        schema = explorer.prop_schema(prop)
        self.assertEqual(schema['Inner']['property_type'], 'StructProperty')
        self.assertEqual(schema['Inner']['element_size'], 24)
        self.assertEqual(schema['Inner']['Struct'], {'$object': '/Script/InputCore.Key'})

    def test_original_core_preserved(self):
        self.assertEqual(hashlib.sha256(Path(core.__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
            '6c043cb1664e71daa6a6b3a50f9d04f284854101d071ac0b21ce18b1469fe543')

    def test_capabilities_do_not_claim_parity(self):
        with Harness() as h:
            status = h.request({'op': 'status'})
            self.assertFalse(status['parity_complete'])
            self.assertIn('invoke', status['original_operations'])
            self.assertNotIn('invoke', status['operations'])
            with self.assertRaises(UnsupportedCapability): h.request({'op': 'invoke'})
        with self.assertRaises(RuntimeError): h.request({'op': 'status'})

    def test_request_failure_releases_catalog_and_recovers(self):
        with Harness() as h:
            with patch('expedition33.introspection.capture', side_effect=ValueError('broken observation')):
                with self.assertRaises(ValueError):
                    h.request({'op': 'search', 'offset': 'bad'})
            self.assertIsNone(h._backend.catalog)
            self.assertEqual(h.request({'op': 'status'})['retained_values'], [])

    def test_thread_ownership(self):
        with Harness() as h:
            errors = []
            def worker():
                try: h.request({'op': 'status'})
                except RuntimeError as exc: errors.append(str(exc))
            thread = threading.Thread(target=worker); thread.start(); thread.join()
            self.assertEqual(len(errors), 1)


if __name__ == '__main__': unittest.main()
