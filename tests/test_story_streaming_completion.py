import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch

from expedition33.story_streaming import StoryStreamingCompletion,COMPLETION_CDO,COMPLETION_FUNCTION


class StreamingCompletionTests(unittest.TestCase):
    def fixture(self):
        token=((1,2,3,4),'save')
        ctx=dict(world='Lumiere',visit=[2,3,4],pawn=[5,6,7],controller=[8,9,10],ready=True)
        session=N(_transport=N(loading_dispatch_reentrancy_protocol=1))
        scope=N(_session=session,_world_binding_token=token,pid=1,_check=Mock(),close=Mock())
        gate=N(session=session,closed=False,owner=99,status=Mock(side_effect=lambda:
            dict(state=2,world=[2,3,4],pawn=[5,6,7],hold_sequence=11)))
        obj=StoryStreamingCompletion.__new__(StoryStreamingCompletion)
        obj._scope=obj.scope=scope;obj.ctx=ctx;obj.gate=gate;obj.token=token
        obj.state='new';obj.planner=obj.call=None;obj.closed=False;obj.sequence=None;obj.gate_owner=99
        call=N(invoke=Mock(side_effect=lambda:nullcontext(N(outcome='dispatch_returned'))))
        planner=N(prepare=Mock(return_value=call),close=Mock())
        world,cdo,fn=object(),object(),object()
        catalog=N(by_index={2:world},find_path=lambda path:{COMPLETION_CDO:cdo,COMPLETION_FUNCTION:fn}[path])
        catalog.with_observations=Mock(return_value=catalog)
        construction=N(catalog=Mock(return_value=catalog),movement_planner=Mock(return_value=planner))
        session._story_construction_resources=construction
        source=lambda:N(scope=scope,closed=False,unknown=False,actor=N(state='prepared'),query=object(),planner=object())
        self.enterContext(patch('expedition33.story_streaming.capture_selected',return_value=catalog))
        self.current=self.enterContext(patch('expedition33.map_runtime.context',return_value=ctx))
        return obj,[source(),source()],call,planner

    def test_original_request_is_once_and_does_not_mark_sources_or_release_hold(self):
        obj,sources,call,planner=self.fixture()
        for source in sources:source.ready=Mock(return_value=False)
        obj.gate.release=Mock()
        self.assertTrue(obj.complete(sources));self.assertTrue(obj.complete(sources))
        call.invoke.assert_called_once();obj.gate.release.assert_not_called()
        self.assertEqual(obj.gate.status.call_count,3)
        self.assertEqual(obj.state,'complete')
        for source in sources:source.ready.assert_not_called()
        self.assertEqual(len(obj.gate._story_streaming_completions),1)
        self.assertTrue(obj.close());planner.close.assert_called_once()

    def test_missing_protocol_prevents_any_preparation_or_dispatch(self):
        for capability in (0,True,2,None):
            obj,sources,call,planner=self.fixture()
            obj.scope._session._transport.loading_dispatch_reentrancy_protocol=capability
            with self.subTest(capability=capability),self.assertRaisesRegex(RuntimeError,'protection'):
                obj.complete(sources)
            planner.prepare.assert_not_called();call.invoke.assert_not_called()

    def test_every_source_must_be_acknowledged_same_world_and_session(self):
        for change in ('unknown','closed','actor','query','session','world','duplicate'):
            obj,sources,call,_=self.fixture()
            source=sources[1]
            if change in ('unknown','closed'):setattr(source,change,True)
            elif change=='actor':source.actor.state='unknown'
            elif change=='query':source.query=None
            elif change=='session':source.scope=N(_session=object())
            elif change=='world':source.scope=N(_session=obj.scope._session,_world_binding_token='another')
            else:sources[1]=sources[0]
            with self.subTest(change=change),self.assertRaises(RuntimeError):obj.complete(sources)
            call.invoke.assert_not_called()

    def test_context_or_hold_changes_between_planning_and_dispatch_prevent_call(self):
        for change in ('context','world','pawn','sequence','released','owner','token'):
            obj,sources,call,planner=self.fixture()
            def alter(*args,**kwargs):
                if change=='context':self.current.return_value=dict(obj.ctx,ready=False)
                elif change=='owner':obj.gate.owner=100
                elif change=='token':obj._scope._world_binding_token='another'
                else:
                    held=dict(state=2,world=[2,3,4],pawn=[5,6,7],hold_sequence=11)
                    if change=='world':held['world']=[9,9,9]
                    elif change=='pawn':held['pawn']=[9,9,9]
                    elif change=='sequence':held['hold_sequence']=12
                    else:held['state']=4
                    obj.gate.status.side_effect=lambda:held
                return call
            planner.prepare.side_effect=alter
            with self.subTest(change=change),self.assertRaises(RuntimeError):obj.complete(sources)
            call.invoke.assert_not_called()

    def test_lost_ack_cannot_be_replayed_or_closed(self):
        obj,sources,call,planner=self.fixture()
        call.invoke.side_effect=RuntimeError('lost ACK')
        with self.assertRaisesRegex(RuntimeError,'lost ACK'):obj.complete(sources)
        self.assertEqual(obj.state,'unknown');self.assertFalse(obj.close())
        with self.assertRaisesRegex(RuntimeError,'not replayed'):obj.complete(sources)
        call.invoke.assert_called_once();planner.close.assert_not_called()

    def test_nonreturned_outcome_retains_attempt_and_never_replays(self):
        obj,sources,call,planner=self.fixture()
        call.invoke.side_effect=lambda:nullcontext(N(outcome='unknown'))
        with self.assertRaisesRegex(RuntimeError,'did not return'):obj.complete(sources)
        self.assertEqual(obj.state,'unknown');self.assertFalse(obj.close())
        with self.assertRaisesRegex(RuntimeError,'not replayed'):obj.complete(sources)
        call.invoke.assert_called_once();planner.close.assert_not_called()

    def test_second_owner_cannot_repeat_same_gate_request(self):
        obj,sources,call,_=self.fixture();obj.complete(sources)
        # Model a reconstructed owner with the same exact held gate after the
        # first owner was misplaced. The gate journal survives that mistake.
        obj.state='prepared'
        with self.assertRaisesRegex(RuntimeError,'already requested'):obj.complete(sources)
        call.invoke.assert_called_once()

    def test_post_call_changed_hold_quarantines_instead_of_repeating(self):
        obj,sources,call,planner=self.fixture()
        def invoke():
            obj.gate.status.side_effect=lambda:dict(state=2,world=[2,3,4],pawn=[5,6,7],hold_sequence=12)
            return nullcontext(N(outcome='dispatch_returned'))
        call.invoke.side_effect=invoke
        with self.assertRaisesRegex(RuntimeError,'same active'):obj.complete(sources)
        self.assertEqual(obj.state,'unknown');self.assertFalse(obj.close())
        with self.assertRaisesRegex(RuntimeError,'not replayed'):obj.complete(sources)
        call.invoke.assert_called_once();planner.close.assert_not_called()


if __name__=='__main__':unittest.main()
