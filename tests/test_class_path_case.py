import unittest
from types import SimpleNamespace
from unittest.mock import patch
from expedition33.picto_class_load import load_class

class ResolverReached(Exception):pass

class ClassPathCaseTests(unittest.TestCase):
    def scope(self):
        return SimpleNamespace(_check=lambda:None,
            _session=SimpleNamespace(_transport=SimpleNamespace(picto_class_load_protocol=1,_executable="unused")),pid=1)

    def test_registered_package_and_class_case_variation_reaches_native_resolver(self):
        path='/Game/Characters/Enemies/Lumiere/ACTE_3/Creation/BP_EnemyWorld_Creation_ALPHA.BP_EnemyWorld_Creation_Alpha_C'
        with patch('expedition33._asset_names.resolve',side_effect=ResolverReached) as resolver:
            with self.assertRaises(ResolverReached):load_class(self.scope(),path)
            self.assertEqual(resolver.call_count,1)
            self.assertEqual(resolver.call_args.args[1],path)

    def test_existing_equal_case_paths_still_reach_resolver(self):
        with patch('expedition33._asset_names.resolve',side_effect=ResolverReached):
            with self.assertRaises(ResolverReached):load_class(self.scope(),'/Game/Test/BP_Test.BP_Test_C')

    def test_other_validation_constraints_remain_enforced(self):
        invalid=('/game/Test/BP_Test.BP_Test_C','/Game/Test/BP_Test.Other_C',
                 '/Game/Test/BP_Test.BP_Test_c','/Game/Test/BP-Test.BP-Test_C',
                 '/Game/Test/BP_Test.BP_Test_C:Nested','/Game/../BP_Test.BP_Test_C')
        with patch('expedition33._asset_names.resolve') as resolver:
            for path in invalid:
                with self.subTest(path=path),self.assertRaises(ValueError):load_class(self.scope(),path)
            resolver.assert_not_called()

if __name__=='__main__':unittest.main()
