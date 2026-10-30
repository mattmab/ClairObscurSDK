import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock, patch
from expedition33._scope import SessionScope
from expedition33._retired_tracking import close_lease_only_scope
from expedition33.cinematics.adapters import PreviewAdapter, OriginalActionAdapter
from expedition33.cinematics.controller import CleanupRequest, BackendState
from expedition33.values import StoredArray
from expedition33 import TargetExitedError


class Lease:
    def __init__(self, replies):self.replies=list(replies);self.calls=0
    def release(self):
        self.calls+=1
        reply=self.replies.pop(0)
        if isinstance(reply,Exception):raise reply
        return reply


def scope():
    session=N(_check=lambda:None,_transport=N(lease_policy_protocol=0),console=N(),_abort_ownership=Mock())
    return SessionScope(session),session


class RetiredTrackingTests(unittest.TestCase):
    def test_confirmed_target_exit_is_terminal_not_release_ack(self):
        s,session=scope();session._transport.target_exit_code=0
        lease=Lease((False,));s._leases.append(lease)
        for _ in range(2):
            with self.assertRaises(TargetExitedError) as error:close_lease_only_scope(s)
            self.assertEqual(error.exception.exit_code,0)
        self.assertFalse(s._closed);self.assertEqual(s._leases,[lease]);self.assertEqual(lease.calls,0)
        session._abort_ownership.assert_not_called()

    def test_target_exit_during_batch_release_never_becomes_pending(self):
        s,session=scope();session._transport.lease_release_batch_protocol=1
        session._transport.target_exit_code=None;lease=N(_state='active');s._leases.append(lease)
        def release(_):session._transport.target_exit_code=7;lease._state='target_exited';return False
        session._release_leases=Mock(side_effect=release)
        with self.assertRaises(TargetExitedError) as error:close_lease_only_scope(s)
        self.assertEqual(error.exception.exit_code,7);self.assertEqual(lease._state,'target_exited')
        self.assertEqual(s._leases,[lease]);self.assertFalse(s._closed)
        with self.assertRaises(TargetExitedError):close_lease_only_scope(s)
        session._release_leases.assert_called_once()

    def test_closed_session_preserves_confirmed_exit_cause(self):
        s,session=scope();session._transport.target_exit_code=7
        session._check=Mock(side_effect=RuntimeError('SDK session is closed'))
        with self.assertRaises(TargetExitedError):close_lease_only_scope(s)
        session._check.assert_not_called();self.assertFalse(s._closed)

    def test_target_exit_during_individual_release_never_becomes_pending(self):
        s,session=scope();session._transport.target_exit_code=None
        lease=N(release=Mock(side_effect=lambda:setattr(session._transport,'target_exit_code',7)))
        s._leases.append(lease)
        with self.assertRaises(TargetExitedError):close_lease_only_scope(s)
        self.assertEqual(s._leases,[lease]);self.assertFalse(s._closed);lease.release.assert_called_once()

    def test_native_batch_keeps_deferred_tracking_and_never_releases_individually(self):
        s,session=scope();session._transport.lease_release_batch_protocol=1
        first=N(_state='active',release=Mock());second=N(_state='active',release=Mock())
        s._leases[:]=[first,second]
        def release(leases):
            first._state='released'
            second._state='pending_release' if len(leases)==2 else 'released'
        session._release_leases=Mock(side_effect=release)
        self.assertFalse(close_lease_only_scope(s));self.assertEqual(s._leases,[second]);self.assertFalse(s._closed)
        self.assertTrue(close_lease_only_scope(s));self.assertTrue(s._closed)
        first.release.assert_not_called();second.release.assert_not_called()
        self.assertEqual(session._release_leases.call_args_list[1].args[0],(second,))

    def test_deferred_lease_does_not_close_scope_or_abort_sdk(self):
        s,session=scope();lease=Lease((False,True));s._leases.append(lease)
        self.assertFalse(close_lease_only_scope(s));self.assertFalse(s._closed)
        self.assertIn(lease,s._leases);session._abort_ownership.assert_not_called()
        self.assertTrue(close_lease_only_scope(s));self.assertTrue(s._closed)
        self.assertEqual(lease.calls,2)

    def test_unknown_release_retains_tracking_without_blanket_abort(self):
        s,session=scope();lease=Lease((RuntimeError('unknown'),));s._leases.append(lease)
        with self.assertRaises(RuntimeError):close_lease_only_scope(s)
        self.assertIn(lease,s._leases);self.assertFalse(s._closed)
        session._abort_ownership.assert_not_called()

    def test_unresolved_native_domain_is_never_closed_by_helper(self):
        s,session=scope();owner=Mock();s._audio_owners.append(owner)
        with self.assertRaisesRegex(RuntimeError,'unresolved native domain'):close_lease_only_scope(s)
        owner.close.assert_not_called();session._abort_ownership.assert_not_called()

    def test_preview_retirement_waits_and_never_uses_normal_close(self):
        p=PreviewAdapter(None,{})
        sequence=N(retire_world=Mock(side_effect=(False,True)),close=Mock())
        panel=N(retire_world=Mock(return_value='ack'),close=Mock())
        p.sequence,p.panel=sequence,panel
        request=CleanupRequest(False,'epoch_replaced',1)
        self.assertFalse(p.close(request));self.assertIs(p.sequence,sequence)
        panel.retire_world.assert_not_called()
        self.assertTrue(p.close(request));self.assertIsNone(p.sequence);self.assertIsNone(p.panel)
        sequence.close.assert_not_called();panel.close.assert_not_called()

    def test_original_tracking_close_defers_without_touching_original_playback(self):
        s,session=scope();s._leases.append(Lease((False,True)))
        adapter=OriginalActionAdapter(None,{},{});prepared=N(scope=s,planner=N(close=Mock()),close=Mock(),play=Mock())
        adapter.prepared=prepared
        request=CleanupRequest(False,'epoch_replaced',1)
        self.assertFalse(adapter.close(request));self.assertIs(adapter.prepared,prepared)
        self.assertTrue(adapter.close(request));self.assertIsNone(adapter.prepared)
        prepared.close.assert_not_called();prepared.play.assert_not_called();session._abort_ownership.assert_not_called()

    def test_original_unrelated_activity_cannot_complete_selected_action(self):
        source=N(pid=1,index=10,serial=20,address=0x10000)
        other=N(pid=1,index=11,serial=21,address=0x11000)
        executor=N(index=1,serial=2,address=0x20000)
        component=N(index=2,serial=3,address=0x30000)
        instance=N(index=3,serial=4,address=0x40000)
        catalog=N(by_index={1:executor,2:component,3:instance})
        catalog.with_observations=lambda observed:catalog
        adapter=OriginalActionAdapter(N(pid=1,_session=N(_transport=N(_executable='unused'))),{},{})
        adapter.prepared=N(executor=executor,component=component);adapter.source=source
        adapter.dispatch_acknowledged=True
        def observed(actions, action=None):
            result=[({'GameActionInstancesInExecution':StoredArray(tuple(actions),len(actions))},catalog)]
            if actions:result.append(({'GameAction':action},catalog))
            result.append(({'LevelSequencePlayer':None,'LoadCinematicAssetRequest':None},catalog))
            return result
        with patch('expedition33._reader.ReadBatch'),patch('expedition33.catalog.capture_selected',return_value=catalog),\
             patch('expedition33.cinematics.history.field',side_effect=lambda value,name,kind:value[name]),\
             patch('expedition33.values.read_values_with_references') as reads:
            reads.side_effect=observed((instance,),other)
            self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
            reads.side_effect=observed(())
            self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
            self.assertFalse(adapter.seen)
            reads.side_effect=observed((instance,),source)
            self.assertEqual(adapter.poll().state,BackendState.ACTIVE)
            reads.side_effect=observed(())
            result=adapter.poll();self.assertEqual(result.state,BackendState.COMPLETE)
            self.assertIn('visual completion is unverified',result.detail)
