import contextlib
import struct
import unittest
from unittest.mock import patch
from types import SimpleNamespace as N

from expedition33.map_readiness import NativeMapReadiness, Receipt, RevealDecision, ReadinessPending, SIZE, validate_request, prepare_readiness_metadata


class ReadinessTests(unittest.TestCase):
    def test_title_prepares_stable_metadata_once_without_world_objects(self):
        root = N(pid=123)
        discovered = [N(index=i, serial=0, address=100*i) for i in range(1, 7)]
        stable = {obj.index: N(index=obj.index, serial=1000+obj.index, address=obj.address)
                  for obj in discovered}
        catalog = N(find_path=lambda path: discovered.pop(0))
        owner = N(prepare=lambda c, objects: N(by_index=stable))
        with patch('expedition33._reader.ReadBatch', return_value=contextlib.nullcontext()), \
                patch('expedition33.catalog.capture_matching', return_value=catalog) as capture, \
                patch('expedition33._metadata_stabilization.process_preparation', return_value=owner):
            first = prepare_readiness_metadata(root)
            self.assertTrue(all(obj.serial > 0 for obj in first))
            self.assertIs(prepare_readiness_metadata(root), first)
            self.assertEqual(capture.call_count, 1)

    def test_gameplay_reuses_root_metadata_without_discovery(self):
        query = self.query()
        query.runtime.scope._session._map_readiness_metadata = query.ids
        expected = query.ids
        query.ids = None
        with patch('expedition33.catalog.capture_matching', side_effect=AssertionError('late discovery')):
            self.assertIs(query.prepare().ids, expected)

    def query(self, mutate=None, *, owned=False):
        def command(name, packet):
            self.assertEqual(name, 'mesh')
            validate_request(packet)
            self.packet = packet
            result = bytearray(packet)
            struct.pack_into('<I', result, 12, 1)
            struct.pack_into('<I', result, 3564, 2)
            struct.pack_into('<13I4x5d', result, 4096, 2, 2, 1, 2, 5, 5, 5, 31, 1, 2, 0, 5, 5, *([100.]*5))
            if mutate:
                mutate(result)
            return {'mesh_packet': result.hex()}
        runtime = N(owner=9, started=True, uncertain=False, _closed=False,
                    objects={'a': None, 'b': None}, scope=N(pid=123,
                        _lease_context=contextlib.nullcontext,
                        _session=N(_transport=N(command=command))))
        query = NativeMapReadiness(runtime, {'visit': [8, 18, 800], 'pawn': [9, 19, 900]},
                                   expected_token=((123, 8, 18, 800), (123, 10, 20, 1000), (123, 11, 21, 1100), 2),
                                   require_owned_support=owned)
        query.ids = tuple((i, i+10, 100*i) for i in range(1, 7))
        return query

    def test_copied_collision_receipt_and_exact_expected_target(self):
        receipt = self.query(owned=True).query()
        self.assertTrue(receipt.spawn_complete and receipt.collision_ready and receipt.scene_visible)
        self.assertEqual(receipt.owned_support_hits, 5)
        self.assertTrue(receipt.visual_ready)
        self.assertEqual(struct.unpack_from('<iiQ', self.packet, 184), (8, 18, 800))
        self.assertEqual(struct.unpack_from('<iiQ', self.packet, 216), (10, 20, 1000))
        self.assertEqual(struct.unpack_from('<iiQ', self.packet, 232), (11, 21, 1100))
        self.assertEqual(struct.unpack_from('<I', self.packet, 2004), (2,))

    def test_missing_or_wrong_saved_world_token_cannot_query(self):
        query = self.query()
        query.expected_token = None
        with self.assertRaisesRegex(RuntimeError, 'saved-world token'):
            query.query()
        for token in (((999, 8, 18, 800), (10, 20, 1000), (11, 21, 1100), 2),
                      ((8, 18, 801), (10, 20, 1000), (11, 21, 1100), 2),
                      ((8, 18, 800), (10, 20, 1000), (11, 21, 1100), -1)):
            with self.subTest(token=token), self.assertRaises(ValueError):
                NativeMapReadiness(query.runtime, query.expected, expected_token=token)

    def test_ack_rejects_changes_outside_output_region(self):
        for at in (16, 88, 152, 184, 2000, 3560, 4192, SIZE-1):
            with self.subTest(at=at), self.assertRaisesRegex(RuntimeError, 'acknowledgement mismatch'):
                self.query(lambda data: data.__setitem__(at, data[at] ^ 1)).query()

    def test_report_rejects_inconsistent_counts_or_flags(self):
        for at, value in ((4096, 6001), (4100, 3), (4104, 3), (4108, 3),
                          (4112, 6), (4116, 6), (4120, 6), (4124, 63), (3564, 1),
                          (4128, 3), (4132, 4097), (4136, 3), (4140, 6), (4144, 6), (4148, 1)):
            with self.subTest(at=at), self.assertRaisesRegex(RuntimeError, 'report malformed'):
                self.query(lambda data: struct.pack_into('<I', data, at, value)).query()

    def test_native_rejection_is_read_only_and_does_not_latch_mutation_uncertainty(self):
        query = self.query(lambda data: struct.pack_into('<I', data, 8, 2115))
        with self.assertRaises(ReadinessPending):
            query.query()
        self.assertFalse(query.runtime.uncertain)

    def test_missing_owned_floor_cannot_claim_collision_ready_when_required(self):
        with self.assertRaisesRegex(RuntimeError, 'report malformed'):
            self.query(lambda data: struct.pack_into('<I', data, 4120, 4), owned=True).query()

    def test_render_and_streaming_pending_are_observed_separately_from_collision(self):
        def pending(data):
            struct.pack_into('<I', data, 4124, 15)
            struct.pack_into('<I', data, 4136, 1)
        receipt = self.query(pending).query()
        self.assertTrue(receipt.collision_ready)
        self.assertFalse(receipt.visual_ready)
        self.assertEqual(receipt.streaming_pending, 1)

    def test_vanilla_support_is_valid_without_owned_floor_requirement(self):
        def vanilla(data):
            struct.pack_into('<I', data, 4120, 0)
            struct.pack_into('<I', data, 4140, 0)
            struct.pack_into('<I', data, 4144, 0)
        receipt = self.query(vanilla).query()
        self.assertTrue(receipt.collision_ready and receipt.visual_ready)
        self.assertEqual(receipt.owned_rendered_support_hits, 0)

    def test_owned_custom_floor_still_requires_recent_render_evidence(self):
        def pending(data):
            struct.pack_into('<I', data, 4124, 15)
            struct.pack_into('<I', data, 4140, 4)
            struct.pack_into('<I', data, 4144, 4)
        receipt = self.query(pending).query()
        self.assertTrue(receipt.collision_ready)
        self.assertFalse(receipt.visual_ready)

    def test_nonfinite_floor_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'report malformed'):
            self.query(lambda data: struct.pack_into('<d', data, 4152, float('nan'))).query()

    def test_wrong_owner_lifecycle_blocks_query(self):
        query = self.query()
        query.runtime.uncertain = True
        with self.assertRaisesRegex(RuntimeError, 'unavailable'):
            query.query()

    def test_request_rejects_padding_and_invalid_target(self):
        self.query().query()
        for at in (0, 24, 248, 1999, 2008, 4096):
            packet = bytearray(self.packet)
            packet[at] ^= 255
            with self.subTest(at=at), self.assertRaises(ValueError):
                validate_request(bytes(packet))
        packet = bytearray(self.packet)
        struct.pack_into('<Q', packet, 208, 0)
        with self.assertRaisesRegex(ValueError, 'identity'):
            validate_request(bytes(packet))
        packet = bytearray(self.packet)
        struct.pack_into('<I', packet, 2004, 2**31)
        with self.assertRaisesRegex(ValueError, 'padding or support policy'):
            validate_request(bytes(packet))


class RevealTests(unittest.TestCase):
    def setUp(self):
        self.cleaned = []
        self.token = ((1, 11, 111), (2, 22, 222), (3, 33, 333), 1)
        self.gate = RevealDecision(self.token, started=10., timeout=20., cleanup=self.cleaned.append)
        self.receipt = Receipt(2, 2, 1, 2, 5, 5, 5, 31, 1, 2, 0, 5, 5, (100.,)*5)

    def observe(self, **kwargs):
        args = dict(token=self.token, now=11., visual_ready=True, restoration_ready=True)
        args.update(kwargs)
        return self.gate.observe(self.receipt, **args)

    def test_spawn_ack_never_releases_without_collision_and_visual_observations(self):
        self.assertEqual(self.observe(visual_ready=False), 'visual_pending')
        self.assertEqual(self.observe(restoration_ready=False), 'player_pending')
        self.assertEqual(self.observe(), 'ready')
        self.assertEqual(self.cleaned, [])

    def test_no_elapsed_wait_required_once_all_real_conditions_hold(self):
        self.assertEqual(self.observe(now=10.), 'ready')

    def test_same_world_different_save_slot_cancels_once(self):
        changed = self.token[:-1] + (2,)
        self.assertEqual(self.observe(token=changed), 'failed')
        self.gate.cancel('again')
        self.assertEqual(self.cleaned, ['load_generation_changed'])

    def test_incomplete_observation_defers_then_times_out_and_releases(self):
        self.assertEqual(self.observe(token=None, now=29.9), 'observation_pending')
        self.assertEqual(self.observe(token=None, now=30.), 'failed')
        self.assertEqual(self.cleaned, ['readiness_timeout'])

    def test_early_collision_failure_waits_only_for_observed_recovery(self):
        self.receipt = Receipt(2, 2, 1, 2, 5, 4, 4, 11, 1, 2, 0, 4, 4, (100.,)*5)
        self.assertEqual(self.observe(), 'collision_pending')
        self.assertEqual(self.observe(now=30.), 'failed')

    def test_cleanup_failure_is_not_replayed(self):
        def fail(reason):
            self.cleaned.append(reason)
            raise RuntimeError('cleanup pending')
        self.gate.cleanup = fail
        with self.assertRaisesRegex(RuntimeError, 'cleanup pending'):
            self.gate.cancel()
        self.assertEqual(self.gate.cancel(), 'failed')
        self.assertEqual(self.cleaned, ['cancelled'])
