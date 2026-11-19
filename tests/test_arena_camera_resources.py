from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import unittest

from expedition33 import _owned_arena_camera as camera


class CameraResourceTests(unittest.TestCase):
    def setUp(self):
        self.objects=[N(index=i+1,serial=i+10,address=0x10000+i*256) for i in range(3)]
        self.catalog=N(find_path=lambda path:self.objects[camera.METADATA.index(path)])
        self.observed=object();self.descriptors={1:N(object=self.objects[0]),2:N(object=self.objects[1])}
        self.observations=object()
        self.planner=N(_metadata=N(read=Mock()),observations=Mock(return_value=self.observations))
        self.scope=N(pid=9,_check=Mock(),invocation_planner=Mock(return_value=nullcontext(self.planner)))
        self.resources=N(scope=self.scope,hold=Mock(side_effect=lambda obj:N(active=True,object=obj)))
        self.capture=self.enterContext(patch.object(camera,'capture_matching',return_value=self.catalog))
        self.describe=self.enterContext(patch('expedition33.reflection.describe_selected',return_value='snapshot'))
        self.closure=self.enterContext(patch('expedition33.story_performance_preflight._pod_closure',
                                            return_value=(self.observed,self.descriptors)))

    def test_title_warm_pins_only_static_metadata_and_reuses_valid_schema(self):
        journal=camera.warm(self.resources)
        self.assertIs(camera.warm(self.resources),journal)
        self.assertTrue(journal['ready']);self.assertIs(journal['observations'],self.observations)
        self.assertEqual(self.resources.hold.call_count,3);self.capture.assert_called_once()
        self.describe.assert_called_once_with(9,((1,10,0x10000),(2,11,0x10100)))
        self.closure.assert_called_once_with(9,'snapshot')
        self.scope.invocation_planner.assert_called_once_with(catalog=self.observed,selected_results=True)
        args=self.planner._metadata.read.call_args.args
        self.assertEqual(args[:3],('struct',self.observed,tuple(d.object for d in self.descriptors.values())))
        self.assertIs(args[3](None,None),self.descriptors)

    def test_lease_or_schema_failure_leaves_terminal_journal(self):
        for stage in ('lease','schema'):
            with self.subTest(stage=stage):
                if hasattr(self.resources,'_owned_arena_camera_inputs'):del self.resources._owned_arena_camera_inputs
                self.resources.hold.side_effect=(RuntimeError('lease unknown') if stage=='lease'
                    else lambda obj:N(active=True,object=obj))
                self.describe.side_effect=RuntimeError('schema failed') if stage=='schema' else None
                with self.assertRaises(RuntimeError):camera.warm(self.resources)
                count=self.capture.call_count
                with self.assertRaisesRegex(RuntimeError,'not replayed'):camera.warm(self.resources)
                self.assertEqual(self.capture.call_count,count)
                self.assertFalse(self.resources._owned_arena_camera_inputs['ready'])

    def test_expired_lease_cannot_return_cached_schema(self):
        journal=camera.warm(self.resources);journal['objects'][1].active=False
        with self.assertRaisesRegex(RuntimeError,'lease expired'):camera.warm(self.resources)
        self.capture.assert_called_once()


if __name__=='__main__':unittest.main()
