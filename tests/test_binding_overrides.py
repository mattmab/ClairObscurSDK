import unittest
from contextlib import nullcontext,ExitStack
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.binding_overrides import bind_actor
from expedition33.cinematics.blueprint_actor import BlueprintActor
from expedition33.sequences import OwnedLevelSequence
from expedition33.invocation import InvocationError


class BindingOverrideTests(unittest.TestCase):
    def test_metadata_reuse_keeps_fresh_target_descriptors_and_rejects_inactive_leases(self):
        case=self.setup_case();sequence,source,actor,catalog,fixed,values,prepare,invoke=case
        with self.mocks(case),patch('expedition33.cinematics.binding_overrides.capture_matching',return_value=catalog) as scan,\
             patch('expedition33.cinematics.binding_overrides.capture_selected',return_value=catalog) as selected:
            bind_actor(sequence,source,{},actor)
            second=BlueprintActor.__new__(BlueprintActor);second.scope=actor.scope;second.state='visible'
            second.owner=N(_timeline=True,_timeline_binding_owners=[],actor_identity=(6,7,1536))
            catalog.by_index[6]=N(index=6,serial=7,address=1536)
            other=dict(values,Guid=dict(A=9,B=2,C=3,D=4))
            with patch('expedition33.cinematics.binding_overrides.resolve',return_value=other):bind_actor(sequence,source,{},second)
            scan.assert_called_once();self.assertEqual(selected.call_count,4);self.assertEqual(prepare.call_count,2)
            self.assertEqual(set(scan.call_args.kwargs['names']),{'AddBinding','MovieSceneObjectBindingID','Guid',
                'MovieSceneSequenceExtensions','Default__MovieSceneSequenceExtensions','GetPortableBindingID'})
            self.assertEqual(len(sequence.scope._portable_binding_metadata),2)
            self.assertEqual(len(sequence.scope._authored_binding_metadata),3)
            sequence.scope._authored_binding_metadata[0].active=False
            second.owner._timeline_binding_owners=[]
            with patch('expedition33.cinematics.binding_overrides.resolve',return_value=dict(other,SequenceID=456)),self.assertRaisesRegex(RuntimeError,'inactive'):
                bind_actor(sequence,source,{},second)
            self.assertEqual(invoke.call_count,2)
    def test_combined_metadata_preparation_preserves_existing_portable_leases(self):
        from expedition33.cinematics.binding_overrides import _prepare_binding_metadata
        scope=N(pid=123)
        previous=(N(active=True),N(active=True));scope._portable_binding_metadata=previous
        held=[]
        catalog=N(find_path=Mock(side_effect=lambda path:path))
        def hold(owner,obj):
            lease=N(active=True,object=obj);held.append(lease);return lease
        with patch('expedition33.cinematics.binding_overrides.capture_matching',return_value=catalog) as scan, \
             patch('expedition33.cinematics.binding_overrides._hold',side_effect=hold):
            metadata=_prepare_binding_metadata(scope)
            self.assertIs(scope._portable_binding_metadata,previous)
            self.assertEqual(metadata,tuple(held));self.assertEqual(len(held),3)
            self.assertEqual(_prepare_binding_metadata(scope),metadata)
            scan.assert_called_once()
            previous[0].active=False
            with self.assertRaisesRegex(RuntimeError,'inactive'):_prepare_binding_metadata(scope)
            scan.assert_called_once()
    def setup_case(self):
        transport=N(sequence_binding_values_protocol=1,_executable='test')
        session=N(_transport=transport)
        scope=N(pid=123,_session=session,_check=Mock(),_close_before_descendants=Mock())
        sequence=OwnedLevelSequence.__new__(OwnedLevelSequence)
        sequence.scope=scope;sequence.owner=N(state='armed');sequence.state='ready';sequence.uncertain=False
        sequence._evaluation_attempted=False;sequence.actor=N(index=1,serial=2,address=256)
        sequence._asset=N(index=2,serial=3,address=512);sequence._actor_binding_attempts=set()
        actor=BlueprintActor.__new__(BlueprintActor)
        actor.scope=N(_check=Mock(),_session=session,_parent=lambda:scope)
        actor.state='visible';actor.owner=N(_timeline=True,_timeline_binding_owners=[],actor_identity=(3,4,768))
        source=N(index=4,serial=5,address=1024)
        replacement=N(index=3,serial=4,address=768)
        fixed=N(index=5,serial=6,address=1280)
        catalog=N(by_index={3:replacement},find_path=Mock(return_value=fixed))
        returned=Mock();returned.__enter__=Mock(return_value=N(outcome='dispatch_returned'));returned.__exit__=Mock(return_value=False)
        invoke=Mock(return_value=returned)
        prepare=Mock(return_value=N(invoke=invoke));scope.invocation_planner=Mock(return_value=N(prepare=prepare))
        values=dict(Guid=dict(A=1,B=2,C=3,D=4),SequenceID=123,ResolveParentIndex=0)
        return sequence,source,actor,catalog,fixed,values,prepare,invoke
    def mocks(self,case):
        sequence,source,actor,catalog,fixed,values,prepare,invoke=case
        stack=ExitStack();prefix='expedition33.cinematics.binding_overrides.'
        for name,value in [('shared_operation',lambda *a,**k:nullcontext()),('sequence_occurrences',Mock(return_value=1)),
                           ('_authored_actor',Mock()),('resolve',Mock(return_value=values)),
                           ('capture_matching',Mock(return_value=catalog)),('capture_selected',Mock(return_value=catalog)),
                           ('_hold',lambda *a:N(object=fixed,active=True))]:
            stack.enter_context(patch(prefix+name,value))
        return stack
    def test_binding_uses_engine_id_owned_actor_and_disables_original_asset_binding(self):
        case=self.setup_case();sequence,source,actor,_,_,values,prepare,invoke=case
        with self.mocks(case):result=bind_actor(sequence,source,dict(A=1,B=2,C=3,D=4),actor)
        self.assertEqual(result['outcome'],'dispatch_returned')
        self.assertFalse(result['component_binding_verified'])
        self.assertEqual(prepare.call_args.kwargs['Binding'],values)
        self.assertIs(prepare.call_args.kwargs['bAllowBindingsFromAsset'],False)
        self.assertEqual(actor.owner._timeline_binding_owners,[sequence.owner])
        sequence.scope._close_before_descendants.assert_called_once_with(sequence.owner)
        invoke.return_value.__exit__.assert_called_once()
        with self.mocks(case),self.assertRaisesRegex(RuntimeError,'binding consumer'):
            bind_actor(sequence,source,dict(A=1,B=2,C=3,D=4),actor)
        invoke.assert_called_once()
    def test_result_cleanup_failure_keeps_actor_dependency_and_prevents_replay(self):
        case=self.setup_case();sequence,source,actor,*_=case;invoke=case[-1]
        invoke.return_value.__exit__.side_effect=RuntimeError('Result cleanup failed')
        with self.mocks(case),self.assertRaisesRegex(RuntimeError,'cleanup failed'):
            bind_actor(sequence,source,{},actor)
        self.assertTrue(sequence.uncertain)
        self.assertEqual(actor.owner._timeline_binding_owners,[sequence.owner])
        with self.mocks(case),self.assertRaises(RuntimeError):bind_actor(sequence,source,{},actor)
        invoke.assert_called_once()
    def test_unknown_outcome_keeps_actor_dependency_and_never_replays(self):
        case=self.setup_case();sequence,source,actor,*_=case;invoke=case[-1]
        invoke.side_effect=InvocationError('timeout',outcome='unknown')
        with self.mocks(case),self.assertRaises(InvocationError):bind_actor(sequence,source,{},actor)
        self.assertTrue(sequence.uncertain);self.assertEqual(actor.owner._timeline_binding_owners,[sequence.owner])
        with self.mocks(case),self.assertRaises(RuntimeError):bind_actor(sequence,source,{},actor)
        invoke.assert_called_once()
    def test_known_rejection_releases_dependency_but_preserves_once_only_attempt(self):
        case=self.setup_case();sequence,source,actor,*_=case;invoke=case[-1]
        invoke.side_effect=InvocationError('rejected',outcome='not_dispatched')
        with self.mocks(case),self.assertRaises(InvocationError):bind_actor(sequence,source,{},actor)
        self.assertFalse(sequence.uncertain);self.assertFalse(actor.owner._timeline_binding_owners)
        with self.mocks(case),self.assertRaisesRegex(RuntimeError,'already attempted'):bind_actor(sequence,source,{},actor)
        invoke.assert_called_once()
    def test_unqualified_contexts_never_dispatch(self):
        for mutate in (lambda s,a:setattr(s,'_evaluation_attempted',True),
                       lambda s,a:setattr(a,'state','prepared'),
                       lambda s,a:setattr(a.scope,'_parent',lambda:None),
                       lambda s,a:setattr(s.scope._session._transport,'sequence_binding_values_protocol',True)):
            case=self.setup_case();sequence,source,actor,*_=case;mutate(sequence,actor)
            with self.mocks(case),self.assertRaises((RuntimeError,ValueError)):bind_actor(sequence,source,{},actor)
            case[-1].assert_not_called()
        case=self.setup_case();sequence,source,actor,*_=case
        with self.mocks(case),patch('expedition33.cinematics.binding_overrides.sequence_occurrences',return_value=2),self.assertRaises(ValueError):
            bind_actor(sequence,source,{},actor)
        case[-1].assert_not_called()
