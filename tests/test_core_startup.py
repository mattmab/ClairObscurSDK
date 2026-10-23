import importlib.util
from pathlib import Path
from types import SimpleNamespace as N
import unittest
from unittest.mock import patch

from expedition33 import RuntimeQueryError

SOURCE=Path(__file__).resolve().parents[1]/'src/expedition33/core_startup.py'
spec=importlib.util.spec_from_file_location('expedition33._core_startup_candidate',SOURCE)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def catalog(*, serial=1, function=True, owner_path='/Script/Engine.Actor'):
    owner=N(index=3,serial=1)
    actor=N(index=4,serial=serial,address=0x10400,name='Default__Actor',class_name='Actor',
            class_index=3,object_flags=0x10)
    fn=N(index=5,serial=1,address=0x10500,name='IsActorBeingDestroyed',class_name='Function',
         outer_index=3,outer_serial=1,object_flags=0)
    return N(objects=(actor,fn) if function else (actor,),by_index={3:owner},
             path_name=lambda obj:owner_path)


class CoreStartupTests(unittest.TestCase):
    def run_ready(self,first=None,second=None,starts=None):
        first=catalog() if first is None else first
        second=first if second is None else second
        starts=starts or (dict(pid=7,game_thread_id=9),dict(pid=7,game_thread_id=9))
        with patch.object(m,'ReadBatch') as batch, \
             patch.object(m,'_query',side_effect=((starts[0],[]),(starts[1],[]))) as query, \
             patch.object(m,'_decode_catalog',side_effect=(first,second)):
            result=m.core_bootstrap_ready(7)
            batch.assert_called_once_with(7)
            self.assertEqual(query.call_args_list[0].args[0],
                ['--catalog-match','7','n=Default__Actor,n=IsActorBeingDestroyed'])
            return result,query.call_args_list

    def test_core_admits_without_world_gi_controller_pawn_or_save(self):
        ready,calls=self.run_ready()
        self.assertTrue(ready)
        self.assertEqual(calls[1].args[0],['--catalog-select','7','4:1:10400,5:1:10500'])

    def test_missing_function_is_early_not_ready(self):
        ready,calls=self.run_ready(first=catalog(function=False))
        self.assertFalse(ready);self.assertEqual(len(calls),1)

    def test_identity_replacement_rejected(self):
        self.assertFalse(self.run_ready(second=catalog(serial=2))[0])

    def test_game_thread_nonzero_and_same_on_second_observation(self):
        for thread in (0,None,True,-1):
            with self.subTest(thread=thread):
                self.assertFalse(self.run_ready(starts=(dict(pid=7,game_thread_id=thread),dict(pid=7,game_thread_id=9)))[0])
        self.assertFalse(self.run_ready(starts=(dict(pid=7,game_thread_id=9),dict(pid=7,game_thread_id=10)))[0])

    def test_wrong_owner_is_visible_schema_failure(self):
        with self.assertRaisesRegex(RuntimeQueryError,'outside'):
            self.run_ready(first=catalog(owner_path='/Other.Actor'))

    def test_known_early_registry_missing_is_false_no_read_retry(self):
        for message in ('MATCH_RESULTS_EMPTY','GAME_THREAD_ID_NOT_OWNED_BY_TARGET','REGISTRY_COUNTS_INVALID'):
            with self.subTest(message=message),patch.object(m,'ReadBatch'), \
                 patch.object(m,'_query',side_effect=RuntimeQueryError(message)) as query:
                self.assertFalse(m.core_bootstrap_ready(7));self.assertEqual(query.call_count,1)

    def test_unknown_decoder_error_visible(self):
        with patch.object(m,'ReadBatch'),patch.object(m,'_query',return_value=(dict(pid=7,game_thread_id=9),[])), \
             patch.object(m,'_decode_catalog',side_effect=RuntimeQueryError('bad class schema')):
            with self.assertRaisesRegex(RuntimeQueryError,'bad class schema'):m.core_bootstrap_ready(7)

    def test_wrong_process_visible(self):
        with self.assertRaisesRegex(RuntimeQueryError,'process mismatch'):
            self.run_ready(starts=(dict(pid=8,game_thread_id=9),dict(pid=7,game_thread_id=9)))


if __name__=='__main__':unittest.main()
