"""Fresh factory output discovery preserves leases and typed constraints."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from expedition33.sdk import Session


class FreshRetainedResultsTests(unittest.TestCase):
    def test_outputs_are_leased_before_fresh_discovery_without_stale_catalog_merge(self):
        class Fake:
            pid=42
            supports_retained_invocation=True
            _closed=False
            _check=Mock()
            _check_frame_time_plan=Mock()
            _abort_ownership=Mock()
        session=Fake();session._leases=set()
        session._transport=NS(command=Mock(return_value={'retained_packet':'reply'}))
        constraint=NS(index=2,serial=3,address=0x20000)
        plan=NS(target=NS(pid=42),wire_version=1,parameters=(NS(constraint=constraint),))
        stale=Mock(pid=42);stale.with_observations.side_effect=AssertionError('stale merge')
        obj=NS(index=8,serial=9,address=0x80000)
        fresh=NS(by_index={8:obj})
        reply=NS(outcome='dispatch_returned',error=0,objects=((0,8,9,0x80000),))
        def observe(pid,identities):
            self.assertEqual(len(session._leases),1)
            self.assertEqual((pid,identities),(42,((8,9,0x80000),(2,3,0x20000))))
            return fresh
        result=NS(return_value=obj,outputs={})
        with patch('expedition33._retained_wire.encode_plan',return_value=b'request'),\
             patch('expedition33._retained_wire.decode_reply',return_value=(reply,((0,1234),))),\
             patch('expedition33.catalog.capture_selected',side_effect=observe),\
             patch('expedition33.catalog.capture') as broad,\
             patch('expedition33.invocation.decode_result',return_value=result) as decode:
            owned,current=Session._invoke_retained_plan(session,plan,stale,
                _return_catalog=True,_selected_results=True,_fresh_results=True)
        broad.assert_not_called();stale.with_observations.assert_not_called()
        decode.assert_called_once_with(plan,reply,fresh,texts=())
        self.assertIs(current,fresh);self.assertIs(next(iter(session._leases))._object,obj)

    def test_fresh_discovery_without_selected_results_is_rejected_before_dispatch(self):
        session=NS(_check=Mock())
        with self.assertRaises(ValueError):
            Session._invoke_retained_plan(session,None,None,_fresh_results=True)
