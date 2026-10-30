import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33._scope import SessionScope
from expedition33._enemy_spawn_owner import EnemySpawnOwner
from test_timeline_blueprint_actor import TimelineTransport
from expedition33.cinematics.authored_references import _path_count


class BindingCleanupTests(unittest.TestCase):
    def setup_scope(self):
        transport=TimelineTransport();session=N(_transport=transport,_check=lambda:None,
            console=N(dispatcher=N(namespace={})),_abort_ownership=Mock())
        parent=SessionScope(session);child=SessionScope(parent);actor=EnemySpawnOwner(child)
        ids=tuple(N(index=i+1,serial=i+2,address=0x10000+i*256) for i in range(13))
        actor.spawn_timeline_prepared(ids,(0,0,0,1,0,0,0,0,1,1,1,0))
        return parent,actor,transport,session
    def test_consumer_closes_before_its_descendant_actor_and_only_once(self):
        parent,actor,transport,session=self.setup_scope();events=[]
        class Consumer:
            state='armed'
            def close(self):self.state='closed';events.append('sequence');return True
        consumer=Consumer();parent._sequence_owners.append(consumer);actor._timeline_binding_owners.append(consumer)
        self.assertFalse(actor.close());self.assertEqual(transport.calls,[120])
        command=transport.command
        def log(name,request):events.append('actor');return command(name,request)
        transport.command=log;parent._close_before_descendants(consumer);parent._close_before_descendants(consumer)
        parent.close();self.assertEqual(events,['sequence','actor']);self.assertEqual(transport.calls,[120,111])
        session._abort_ownership.assert_not_called()
    def test_deferred_consumer_prevents_actor_destruction_and_is_not_replayed(self):
        parent,actor,transport,session=self.setup_scope()
        consumer=N(state='armed',close=Mock(return_value=False));parent._sequence_owners.append(consumer)
        actor._timeline_binding_owners.append(consumer);parent._close_before_descendants(consumer)
        with self.assertRaises(RuntimeError):parent.close()
        consumer.close.assert_called_once();self.assertEqual(transport.calls,[120]);session._abort_ownership.assert_called()
    def test_nested_shot_occurrences_count_reused_ancestors_and_reject_cycles(self):
        self.assertEqual(_path_count({1:[2],2:[3]},1,3),1)
        self.assertEqual(_path_count({1:[2,2],2:[3]},1,3),2)
        self.assertEqual(_path_count({1:[2,4],2:[3],4:[3]},1,3),2)
        self.assertEqual(_path_count({1:[2]},1,3),0)
        with self.assertRaisesRegex(RuntimeError,'Cyclic'):_path_count({1:[2,2],2:[3],3:[2]},1,3)
