import math
import unittest

from expedition33.cinematics.scene_transform import actor_placement, origin_translation, rotate_offset


class SceneTransformTests(unittest.TestCase):
    def assertVectorClose(self, actual, expected):
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=7)

    def test_origin_keeps_authored_anchor_at_destination(self):
        source=(100.,200.,300.);destination=(-400.,1000.,25.)
        for yaw in (-180.,-90.,0.,45.,90.,180.):
            with self.subTest(yaw=yaw):
                rotated=rotate_offset(source,yaw)
                translation=origin_translation(source,destination,yaw)
                self.assertVectorClose(tuple(rotated[i]+translation[i] for i in range(3)),destination)
        self.assertVectorClose(origin_translation(source,destination,0.),(-500.,800.,-275.))

    def test_blueprint_offset_and_orientation_rotate_about_scene_anchor(self):
        location,yaw=actor_placement((1000.,2000.,3000.),(120.,-50.,25.),90.,90.)
        self.assertVectorClose(location,(1050.,2120.,3025.))
        self.assertAlmostEqual(abs(yaw),180.)
        location,yaw=actor_placement((1000.,2000.,3000.),(120.,-50.,25.),170.,30.)
        self.assertAlmostEqual(yaw,-160.)
        self.assertAlmostEqual(location[2],3025.)

    def test_invalid_values_never_reach_transform_math(self):
        for yaw in (True,float('nan'),float('inf'),181.,-181.):
            with self.subTest(yaw=yaw),self.assertRaises(ValueError):rotate_offset((0,0,0),yaw)
        for value in ((0,0),[0,0,float('nan')],(0,0,10000001),('0',0,0)):
            with self.subTest(vector=value),self.assertRaises(ValueError):origin_translation(value,(0,0,0))


if __name__=='__main__':unittest.main()
