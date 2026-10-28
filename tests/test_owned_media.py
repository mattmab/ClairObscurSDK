import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33.media import OwnedVideoWidget
from expedition33._media_owner import NativeMediaOwner
from expedition33.invocation import CallPlan
from dataclasses import replace


class OwnedMediaTests(unittest.TestCase):
    def test_cleanup_mismatch_reports_mutable_flags_without_relaxing_guard(self):
        from expedition33.catalog import CatalogObject
        target = CatalogObject(1,2,3,4096,'Video','CommonVideoPlayer','Class',7,-1,0,8,0)
        lease = SimpleNamespace(active=True,object=target,_token=7)
        owner = NativeMediaOwner(SimpleNamespace(_leases=[lease]))
        owner._send = Mock()
        plan = CallPlan(target,object(),0,0,0,0,65535,(),b'',())
        changed = replace(plan,target=replace(target,object_flags=16))
        with self.assertRaisesRegex(ValueError, 'close: object_flags: lease=8, target=16'):
            owner.arm(lease,changed,plan)
        owner._send.assert_not_called()
        self.assertEqual(owner.state,'new')

    def test_cleanup_mismatch_reports_identity_and_snapshot_type(self):
        from expedition33 import ObjectSnapshot
        from expedition33.catalog import CatalogObject
        target = CatalogObject(1,2,3,4096,'Video','CommonVideoPlayer','Class',7,-1,0,8,0)
        lease = SimpleNamespace(active=True,object=target,_token=7)
        owner = NativeMediaOwner(SimpleNamespace(_leases=[lease]))
        owner._send = Mock()
        plan = CallPlan(target,object(),0,0,0,0,65535,(),b'',())
        changed = replace(plan,target=ObjectSnapshot(1,2,4,4096,'Video','CommonVideoPlayer','Class',7))
        with self.assertRaisesRegex(ValueError, 'Media cleanup targets differ') as error:
            owner.arm(lease,plan,changed)
        self.assertIn('remove: type: lease=CatalogObject, target=ObjectSnapshot',str(error.exception))
        self.assertIn('serial: lease=3, target=4',str(error.exception))
        self.assertIn('object_flags: lease=8, target=<missing>',str(error.exception))
        owner._send.assert_not_called()

    def test_cleanup_protocol_normalizes_only_empty_frames(self):
        target = object()
        lease = SimpleNamespace(active=True,object=target,_token=7)
        owner = NativeMediaOwner(SimpleNamespace(_leases=[lease]))
        owner._send = Mock(return_value=True)
        plan = CallPlan(target,object(),0,0,0,0,65535,(),b'',(),wire_version=2)
        owner.arm(lease,plan,plan)
        plans = owner._send.call_args.args[2]
        self.assertEqual([p.wire_version for p in plans],[1,1])
        self.assertEqual(plan.wire_version,2)
        owner._send.reset_mock()
        with self.assertRaisesRegex(ValueError,'empty parameter'):
            owner.arm(lease,replace(plan,parameter_size=4,data=bytes(4)),plan)
        owner._send.assert_not_called()

    def resource(self):
        resource = OwnedVideoWidget.__new__(OwnedVideoWidget)
        resource.state = 'opened'
        resource.native_owner = None
        resource.uncertain = False
        resource.attached = True
        resource.widget = object()
        resource.player = object()
        resource.parent = object()
        resource.scope = Mock()
        resource.planner = Mock()
        resource._read_planner = None
        resource._reads = {}
        return resource

    def test_close_confirms_player_before_detach_and_release(self):
        video = self.resource()
        order = []
        video._call = lambda target, owner, name: order.append(name) or True
        video.planner.close.side_effect = lambda: order.append('planner')
        video.scope.close.side_effect = lambda: order.append('leases')
        video.close()
        self.assertEqual(order, ['Close','IsClosed','RemoveFromParent','planner','leases'])
        self.assertEqual(video.state,'closed')
        video.close()
        self.assertEqual(len(order),5)

    def test_unconfirmed_close_preserves_owner(self):
        video = self.resource()
        video._call = Mock(return_value=False)
        with self.assertRaisesRegex(RuntimeError,'unconfirmed'): video.close()
        self.assertTrue(video.attached)
        video.scope.close.assert_not_called()
        self.assertEqual([c.args[2] for c in video._call.call_args_list],['Close','IsClosed'])

    def test_dispatch_exception_is_quarantined_without_retry(self):
        video = self.resource()
        video._function = Mock(return_value=object())
        prepared = Mock()
        prepared.invoke.side_effect = RuntimeError('lost response')
        video.planner.prepare.return_value = prepared
        with self.assertRaisesRegex(RuntimeError,'lost response'):
            video._invoke(video.player,'MediaPlayer','Play')
        self.assertTrue(video.uncertain)
        with self.assertRaises(RuntimeError): video._invoke(video.player,'MediaPlayer','Play')
        with self.assertRaises(RuntimeError): video.close()
        prepared.invoke.assert_called_once()
        video.scope.close.assert_not_called()

    def test_preflight_failure_does_not_quarantine(self):
        video = self.resource()
        video._function = Mock(return_value=object())
        video.planner.prepare.side_effect = ValueError('bad metadata')
        with self.assertRaises(ValueError): video._invoke(video.player,'MediaPlayer','Play')
        self.assertFalse(video.uncertain)

    def test_other_panel_and_invalid_rates_never_dispatch(self):
        video = self.resource()
        video.state = 'configured'
        video.attached = False
        video._call = Mock()
        with self.assertRaises(RuntimeError): video.attach(object())
        for rate in (True, 0, -1, 3, float('nan'), float('inf'), '1'):
            with self.assertRaises(ValueError): video.set_rate(rate)
        video._call.assert_not_called()

    def test_native_owner_closes_before_any_lease_release(self):
        video = self.resource()
        video.native_owner = Mock()
        video.native_owner.close.return_value = False
        with self.assertRaisesRegex(RuntimeError,'deferred'): video.close()
        video.scope.close.assert_not_called()
        video.native_owner.close.return_value = True
        video._call = Mock()
        video.close()
        video._call.assert_not_called()
        video.scope.close.assert_called_once()
        self.assertEqual(video.state,'closed')
