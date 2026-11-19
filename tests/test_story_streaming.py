from contextlib import nullcontext
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch
import struct

from expedition33.story_streaming import StoryStreamingSource


class StoryStreamingTests(unittest.TestCase):
    def setUp(self):
        self.actor = N(index=1, serial=2, address=300)
        self.component = N(index=4, serial=5, address=600)
        self.enable_fn, self.ready_fn = object(), object()
        self.catalog = N(by_index={1: self.actor}, find_path=lambda path:
                         self.enable_fn if path.endswith(':EnableStreamingSource') else self.ready_fn)
        self.catalog.with_observations = Mock(return_value=self.catalog)
        self.enable = N(invoke=Mock(side_effect=lambda: nullcontext(N())))
        self.query = N(invoke=Mock(side_effect=lambda: nullcontext(N(return_value=True))))
        self.planner = N(prepare=Mock(side_effect=[self.query, self.enable]), close=Mock())
        self.construction = N(catalog=Mock(return_value=self.catalog),
                              movement_planner=Mock(return_value=self.planner))
        self.session = N(_story_construction_resources=self.construction)
        self.scope = N(pid=7, _session=self.session,
                       invocation_planner=Mock(return_value=self.planner))
        self.source = StoryStreamingSource.__new__(StoryStreamingSource)
        self.source.scope = self.scope
        self.source.actor = N(state='prepared', identity=(1, 2, 300))
        self.source.closed = self.source.unknown = False
        self.source.query = self.source.planner = None
        self.capture = self.enterContext(patch('expedition33.story_streaming.capture_selected', return_value=self.catalog))
        self.values = N(values={(1, 'WorldPartitionStreamingSource'): self.component}, errors={})
        self.read = self.enterContext(patch('expedition33.story_streaming.read_values_with_references',
                                           return_value=(self.values, self.catalog)))

    def test_prepared_schemas_still_read_current_owned_component_and_fresh_metadata(self):
        with patch('expedition33.story_streaming.prepare_metadata', side_effect=AssertionError('No rediscovery')):
            self.source.configure()
        self.capture.assert_called_once_with(7, ((1, 2, 300),))
        self.read.assert_called_once_with(self.catalog, self.actor, fields=('WorldPartitionStreamingSource',))
        self.construction.catalog.assert_called_once_with(self.scope, ('EnableStreamingSource', 'IsStreamingCompleted'))
        self.construction.movement_planner.assert_called_once_with(self.scope, self.catalog)
        self.scope.invocation_planner.assert_not_called()
        self.planner.prepare.assert_any_call(self.component, self.ready_fn)
        self.planner.prepare.assert_any_call(self.component, self.enable_fn)
        self.enable.invoke.assert_called_once_with()
        self.assertFalse(self.source.unknown)

    def test_streaming_readiness_is_never_cached(self):
        self.source.configure()
        self.query.invoke.side_effect = [nullcontext(N(return_value=False)), nullcontext(N(return_value=True))]
        self.assertFalse(self.source.ready())
        self.assertTrue(self.source.ready())
        self.assertEqual(self.query.invoke.call_count, 2)

    def test_failed_component_read_cannot_enable_or_prepare_a_plan(self):
        self.values.errors = {'WorldPartitionStreamingSource': 'stale'}
        with self.assertRaisesRegex(RuntimeError, 'component missing'):
            self.source.configure()
        self.construction.movement_planner.assert_not_called()
        self.enable.invoke.assert_not_called()

    def test_missing_enable_ack_preserves_uncertain_owner_without_replay(self):
        self.enable.invoke.side_effect = RuntimeError('ACK lost')
        with self.assertRaisesRegex(RuntimeError, 'ACK lost'):
            self.source.configure()
        self.assertTrue(self.source.unknown)
        self.assertFalse(self.source.ready())
        self.assertFalse(self.source.retire_world())
        with self.assertRaisesRegex(RuntimeError, 'undispatched'):
            self.source.configure()
        self.enable.invoke.assert_called_once_with()
        self.planner.close.assert_not_called()

    def test_no_prepared_resources_keeps_original_metadata_route(self):
        del self.session._story_construction_resources
        metadata = (N(index=8, serial=9, address=1000),)
        with patch('expedition33.story_streaming.prepare_metadata', return_value=metadata) as prepare:
            self.source.configure()
        prepare.assert_called_once_with(self.session)
        self.scope.invocation_planner.assert_called_once_with(catalog=self.catalog, selected_results=True)
        self.capture.assert_any_call(7, ((8, 9, 1000),))
        self.enable.invoke.assert_called_once_with()

    def radius_transport(self,*,fail=False):
        self.source.actor.identity=(1,2,0x10000);self.component.address=0x20000
        self.source.actor.owner=N(_owner=99)
        def command(name,packet):
            self.assertEqual(name,'mesh');self.enable.invoke.assert_not_called()
            if fail:raise RuntimeError('radius ACK lost')
            ack=bytearray(packet);struct.pack_into('<I',ack,12,1)
            return dict(mesh_packet=ack.hex())
        self.session._transport=N(story_streaming_radius_protocol=1,command=Mock(side_effect=command))
        return self.session._transport

    def test_radius_is_instance_configured_before_enable_and_readiness_still_required(self):
        transport=self.radius_transport();self.source.configure(radius=8000)
        transport.command.assert_called_once();self.enable.invoke.assert_called_once()
        self.query.invoke.side_effect=lambda:nullcontext(N(return_value=False))
        self.assertFalse(self.source.ready());self.assertFalse(self.source.unknown)

    def test_unknown_radius_cannot_enable_replay_or_lose_ownership(self):
        transport=self.radius_transport(fail=True)
        with self.assertRaisesRegex(RuntimeError,'ACK lost'):self.source.configure(radius=8000)
        self.assertTrue(self.source.unknown);self.assertFalse(self.source.ready());self.assertFalse(self.source.retire_world())
        with self.assertRaisesRegex(RuntimeError,'undispatched'):self.source.configure(radius=8000)
        self.enable.invoke.assert_not_called();transport.command.assert_called_once()

    def test_bad_radius_or_unsupported_runtime_is_rejected_before_actor_creation(self):
        self.source.actor.state='new';self.source.actor.prepare_streaming_source=Mock()
        self.session._transport=N(story_streaming_radius_protocol=0)
        with self.assertRaisesRegex(RuntimeError,'runtime required'):self.source.prepare((1.,2.,3.),radius=8000)
        with self.assertRaises(ValueError):self.source.prepare((1.,2.,3.),radius=999)
        self.source.actor.prepare_streaming_source.assert_not_called()


if __name__ == '__main__':
    unittest.main()
