from types import SimpleNamespace
from unittest.mock import patch
import unittest

from expedition33.tracing import prepare_trace
from expedition33.invocation import PARM, OUT, RETURN, REFERENCE
import test_invocation


class TraceSchemaTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_invocation.InvocationTests()
        self.fixture.setUp()

    def plan(self, rows, size, returned=65535, flags=0x400):
        descriptor = SimpleNamespace(owners=({'index': 7, 'size': size},), properties=rows,
            function={'params_size': size, 'return_offset': returned, 'flags': flags, 'entry_rva': '0x1234'})
        with patch('expedition33.tracing.describe', return_value={7: descriptor}):
            return prepare_trace(self.fixture.catalog, self.fixture.function)

    def test_separate_local_out_reference_and_return_routes(self):
        f = self.fixture.field
        plan = self.plan([f('Input', 'IntProperty', 0, 4),
                          f('Out', 'IntProperty', 4, 4, PARM | OUT),
                          f('Ref', 'IntProperty', 8, 4, PARM | OUT | REFERENCE),
                          f('Return', 'IntProperty', 12, 4, PARM | RETURN)], 16, 12)
        self.assertEqual([v.source for v in plan.fields], ['locals', 'out', 'out', 'return'])
        self.assertEqual([v.source_offset for v in plan.fields], [0, 0, 0, 0])
        self.assertEqual([v.destination_offset for v in plan.fields], [0, 4, 8, 12])

    def test_packed_bool_inputs_are_separate_normalized_destinations(self):
        f = self.fixture.field
        plan = self.plan([f('A', 'BoolProperty', 0, 1, bool_encoding='0x01010001'),
                          f('B', 'BoolProperty', 0, 1, bool_encoding='0x02020001')], 1)
        self.assertEqual([v.source_offset for v in plan.fields], [0, 0])
        self.assertEqual([v.destination_offset for v in plan.fields], [0, 1])
        self.assertEqual([v.boolean_mask for v in plan.fields], [1, 2])
        self.assertEqual(plan.capture_size, 2)

    def test_fixed_array_out_offsets_and_bad_layout_rejection(self):
        f = self.fixture.field
        plan = self.plan([f('Values', 'IntProperty', 8, 4, PARM | OUT, dimension=3)], 20)
        self.assertEqual([v.source_offset for v in plan.fields], [0, 4, 8])
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            self.plan([f('A', 'IntProperty', 0, 4), f('B', 'IntProperty', 0, 4)], 4)
        with self.assertRaisesRegex(ValueError, 'Return property'):
            self.plan([f('R', 'IntProperty', 0, 4, PARM | RETURN)], 8, 4)
        with self.assertRaisesRegex(ValueError, 'frame validation'):
            self.plan([], 0, flags=0)

    def test_pointer_bearing_fields_do_not_become_raw_trace_bytes(self):
        cls = self.fixture.catalog.by_index[2]
        row = self.fixture.field('Object', 'ObjectProperty', 0, 8, property_class_index=2,
            property_class_serial=cls.serial, property_class_name=cls.name, property_class_address=hex(cls.address))
        with self.assertRaisesRegex(ValueError, 'trace-specific'):
            self.plan([row], 8)
