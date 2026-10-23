from contextlib import nullcontext
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
from expedition33._enemy_arenas import ARENA_CLASS,_arena_candidates,observe_battle_arenas


class ArenaObservationTests(unittest.TestCase):
    def catalog(self):
        world=NS(index=1,serial=2,address=100,class_name='World')
        other=NS(index=2,serial=3,address=200,class_name='World')
        original=NS(index=10,serial=1,address=1000,class_index=90,object_flags=0x10)
        child=NS(index=11,serial=1,address=1100,class_index=90,object_flags=0x10)
        actors=[NS(index=i,serial=1,address=i*100,class_index=11 if i==21 else 10,object_flags=flags)
                for i,flags in ((20,0),(21,0),(22,0x10),(23,0x40000000),(24,0),(25,0x8000),(26,0x10000))]
        objects=[original,child,*actors]
        paths={10:ARENA_CLASS,11:'/Game/Maps/BP_Derived.BP_Derived_C'}
        return NS(objects=objects,classes={10:original,11:child},by_index={o.index:o for o in objects},
                  path_name=lambda o:paths.get(o.index,'arena'+str(o.index)),
                  ancestors=lambda i:(11,10) if i==11 else (i,),
                  outer_chain=lambda o:(other if o.index==24 else world,),
                  with_observations=lambda _:self.catalog())
    def test_exact_world_ancestry_and_lifetime_filter(self):
        rows=_arena_candidates(self.catalog(),(1,2,100))
        self.assertEqual([r['identity'][0] for r in rows],[20,21])
        self.assertEqual(rows[1]['class_path'],'/Game/Maps/BP_Derived.BP_Derived_C')
    def test_reused_world_index_is_not_same_world(self):
        self.assertEqual(_arena_candidates(self.catalog(),(1,99,100)),[])
    def test_missing_or_ambiguous_original_class_is_rejected(self):
        c=self.catalog();c.path_name=lambda _: 'impostor'
        with self.assertRaisesRegex(RuntimeError,'unavailable or ambiguous'):_arena_candidates(c,(1,2,100))
        c=self.catalog();c.path_name=lambda _:ARENA_CLASS
        with self.assertRaisesRegex(RuntimeError,'unavailable or ambiguous'):_arena_candidates(c,(1,2,100))
    def test_missing_original_class_descriptor_is_rejected(self):
        c=self.catalog();c.classes={}
        with self.assertRaisesRegex(RuntimeError,'descriptor'):_arena_candidates(c,(1,2,100))
    def test_observation_checks_context_again_without_mutation(self):
        c=self.catalog();context=dict(world=(7,1,2,100),controller=(7,3,4,300),world_path='world')
        with (patch('expedition33._enemy_arenas.ReadBatch',return_value=nullcontext()),
              patch('expedition33._enemy_arenas.controller_context',side_effect=[context,context]) as read_context,
              patch('expedition33._enemy_arenas.capture_matching',return_value=c),
              patch('expedition33._enemy_arenas.capture_selected') as selected):
            result=observe_battle_arenas(NS(pid=7,_transport=NS(_executable=None)))
            self.assertEqual(result['candidate_count'],2)
            self.assertEqual(result['readiness'],'unverified')
            self.assertEqual(read_context.call_count,2)
            selected.assert_called_once_with(7,((1,2,100),))
    def test_world_change_discards_observation(self):
        context=dict(world=(7,1,2,100),controller=(7,3,4,300),world_path='world')
        with (patch('expedition33._enemy_arenas.ReadBatch',return_value=nullcontext()),
              patch('expedition33._enemy_arenas.controller_context',side_effect=[context,dict(context,world_path='changed')]),
              patch('expedition33._enemy_arenas.capture_matching',return_value=self.catalog()),
              patch('expedition33._enemy_arenas.capture_selected')):
            with self.assertRaisesRegex(RuntimeError,'World/controller changed'):observe_battle_arenas(NS(pid=7,_transport=NS(_executable=None)))
