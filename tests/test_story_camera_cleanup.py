import unittest
from types import SimpleNamespace as N
from expedition33._story_dialogue_camera_cleanup import stale_cameras

class CameraCleanupTests(unittest.TestCase):
    def test_only_active_dialogue_camera_is_released(self):
        cams=[N(name=n,index=i) for i,n in enumerate(('Main_CineCamera','CineCamera_Dialogue_Main','CineCamera_Dialogue1','ShoulderCam'))]
        self.assertEqual(stale_cameras(cams,{0:True,1:True,2:False,3:True}),(cams[1],))
    def test_no_gameplay_camera_means_no_takeover(self):
        cams=[N(name='Main_CineCamera',index=0),N(name='CineCamera_Dialogue_Main',index=1)]
        self.assertEqual(stale_cameras(cams,{0:False,1:True}),())
