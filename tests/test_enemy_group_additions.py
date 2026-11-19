import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch,MagicMock
from contextlib import nullcontext
from expedition33.enemy_combat_additions import add_combatants

class GroupAdditionTests(unittest.TestCase):
    def fixture(self):
        owner=N(phase='active',actor_identity=(1,2,3),arena_identity=(4,5,6))
        planner=Mock();plans=[Mock(),Mock()];planner.prepare_blueprint.side_effect=plans
        cm=MagicMock();cm.__enter__.return_value=planner
        session=N(invocation_planner=Mock(return_value=cm))
        service=N(_scope=N(_check=Mock(),pid=7,_session=session),_closed=False,_owner=owner,
            catalog={},_record={})
        function=N(index=10,serial=11,address=12)
        c=Mock();c.path_name.return_value='class';c.by_index={100:N(index=100),101:N(index=101),102:N(index=102)}
        actors=[N(index=20+i,class_index=100+i) for i in range(3)]
        before=dict(catalog=c,context='context',manager='manager',identities=((20,2,3),),actors=actors[:1])
        after=dict(before,actors=actors,identities=((20,2,3),(21,2,3),(22,2,3)))
        return service,planner,plans,function,before,after
    def run_batch(self,service,planner,plans,function,before,after):
        resolve=lambda catalog,recipe,definition:dict(recipe_id=recipe,definition_row=definition,class_path='class',validation='stored')
        with patch('expedition33.enemy_combat_additions.resolve_definition',side_effect=resolve), \
             patch('expedition33.enemy_combat_additions.ReadBatch',side_effect=lambda *a,**k:nullcontext()), \
             patch('expedition33.enemy_combat_additions._observe',side_effect=[before,after]) as observe, \
             patch('expedition33.enemy_combat_additions._query',return_value=(None,[])), \
             patch('expedition33.enemy_combat_additions.controller_context',return_value='context'), \
             patch('expedition33.enemy_spawning._exact',return_value=function), \
             patch('expedition33.enemy_spawning._fields',side_effect=lambda c,a,n:({'BattleSpotIndex':a.index-20},c)):
            # Match the expected class index on each final actor.
            for actor in after['actors'][1:]:actor.class_index=function.index
            result=add_combatants(service,[('a','A'),('b','B')],experimental=True)
        return result,observe.call_count
    def test_group_shares_planner_and_two_roster_observations(self):
        service,planner,plans,function,before,after=self.fixture()
        result,count=self.run_batch(service,planner,plans,function,before,after)
        self.assertEqual(count,2);self.assertEqual(len(result['members']),2)
        service._scope._session.invocation_planner.assert_called_once()
        for plan in plans:plan.invoke.assert_called_once()
        self.assertTrue(all(r['verified'] for r in service._record['combat_additions']))
    def test_failed_dispatch_retains_attempt_and_does_not_invoke_later_member(self):
        service,planner,plans,function,before,after=self.fixture()
        plans[0].invoke.side_effect=RuntimeError('unknown')
        with self.assertRaisesRegex(RuntimeError,'unknown'):self.run_batch(service,planner,plans,function,before,after)
        self.assertEqual(service._owner.phase,'unknown');plans[1].invoke.assert_not_called()
        self.assertTrue(service._record['combat_additions'][0]['attempted'])
        with self.assertRaises(RuntimeError):add_combatants(service,[('a','A')],experimental=True)
        plans[0].invoke.assert_called_once()
