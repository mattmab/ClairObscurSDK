import math
import unittest
from expedition33._spawn_placement import AssemblyBounds, horizontal_candidate, grounded_translation


class SpawnPlacementTests(unittest.TestCase):
    def test_large_offset_assembly_preserves_root_and_clears_player(self):
        bounds = AssemblyBounds((300, -100, -2500), (4000, 3000, 10000))
        player = (20, 40, 192)
        center = horizontal_candidate(bounds, player, (1, 1, 0), 50, 250)
        self.assertAlmostEqual(math.hypot(center[0]-20, center[1]-40), 5300)
        origin, placed = grounded_translation(bounds, (0, 0, 342), center, 0, 10)
        self.assertEqual(placed.center[2]-placed.extent[2], 10)
        self.assertEqual(origin[2], 12852)
        for i in range(3):
            self.assertAlmostEqual(placed.center[i]-origin[i], bounds.center[i]-(0,0,342)[i])

    def test_ground_sample_uses_destination_height(self):
        bounds = AssemblyBounds((10, 20, 300), (10, 20, 30))
        origin, placed = grounded_translation(bounds, (0,0,0), (100,200,999), -150)
        self.assertEqual(origin, (90,180,-420))
        self.assertEqual(placed.center, (100,200,-120))

    def test_horizontal_clearance_is_conservative_for_all_directions(self):
        bounds = AssemblyBounds((0,0,0), (1200,25,400))
        for degrees in range(0,360,15):
            angle=math.radians(degrees)
            center=horizontal_candidate(bounds,(0,0,0),(math.cos(angle),math.sin(angle),10),75,125)
            dx=max(abs(center[0])-1200,0)
            dy=max(abs(center[1])-25,0)
            self.assertGreaterEqual(math.hypot(dx,dy),200-1e-8)

    def test_invalid_measurements_fail_before_placement(self):
        for center,extent in (((0,0,0),(0,0,0)), ((0,0,0),(-1,1,1)), ((0,0,float('nan')),(1,1,1))):
            with self.assertRaises(ValueError):AssemblyBounds(center,extent)
        bounds=AssemblyBounds((0,0,0),(1,1,1))
        for direction,radius,gap in (((0,0,1),1,1),((1,0,0),-1,1),((1,0,0),1,float('inf'))):
            with self.assertRaises(ValueError):horizontal_candidate(bounds,(0,0,0),direction,radius,gap)
        with self.assertRaises(ValueError):grounded_translation(bounds,(0,0,0),(1,1,1),float('nan'))
