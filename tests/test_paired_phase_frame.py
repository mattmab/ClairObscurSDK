import unittest
import json
from pathlib import Path
from expedition33 import _paired_phase_frame as frame


class PairPhaseFrameTests(unittest.TestCase):
    def test_constants_match_exact_pinned_original_recipe(self):
        data = json.loads((Path(__file__).resolve().parents[1] / 'src/expedition33/_original_trigger_recipes.json').read_text())
        recipe = next(row for row in data['recipes'] if row['id'] == 'duolliste-pair')
        self.assertEqual(recipe['arena']['source_world'], frame.WORLD)
        self.assertEqual(recipe['arena']['source_actor'], frame.ARENA)
        self.assertEqual(recipe['arena']['class_path'], frame.CLASS)
        root = recipe['arena']['frames']['DefaultSceneRoot']
        self.assertEqual(tuple(root['location'][axis] for axis in 'XYZ'), frame.LOCATION)
        self.assertEqual(root['rotation']['Yaw'], frame.YAW)

    def test_exact_original_pose_and_equivalent_quaternion(self):
        pose = frame.original_pose(frame.WORLD)
        self.assertEqual(pose[4:7], frame.LOCATION)
        self.assertEqual(frame.require_original_frame(frame.WORLD,pose),pose)
        inverted = tuple(-value for value in pose[:4]) + pose[4:]
        self.assertEqual(frame.require_original_frame(frame.WORLD,inverted),inverted)

    def test_arbitrary_map_and_relocated_or_invalid_pose_rejected(self):
        with self.assertRaisesRegex(ValueError,'CleasTower'):
            frame.original_pose('/Game/WorldMap.WorldMap')
        original = frame.original_pose(frame.WORLD)
        for index, value in ((4, 0.), (2, 0.), (8, 2.), (7, 1.), (11, 1.), (1,float('nan')), (4,True)):
            pose = list(original);pose[index]=value
            with self.assertRaises(ValueError):
                frame.require_original_frame(frame.WORLD, pose)
        with self.assertRaises(ValueError):
            frame.require_original_frame(frame.WORLD, original[:-1])


if __name__ == '__main__':
    unittest.main()
