import unittest
from expedition33.cinematics.authored_position import player_position


class AuthoredPositionTests(unittest.TestCase):
    def test_actual_simon_ticks_and_non_integer_player_rates(self):
        self.assertEqual(player_position(74400,(24000,1),(30,1)),(93,0.0))
        frame,sub=player_position(24000,(24000,1),(30000,1001))
        self.assertEqual(frame,29);self.assertAlmostEqual(sub,0.970029970,places=6)
        self.assertEqual(player_position(24000,(24000,1),(24,1)),(24,0.0))

    def test_negative_positions_floor_rather_than_truncate(self):
        self.assertEqual(player_position(-400,(24000,1),(30,1)),(-1,0.5))
        self.assertEqual(player_position(-800,(24000,1),(30,1)),(-1,0.0))

    def test_rounding_carry_and_int32_limits(self):
        self.assertEqual(player_position(2147483646,(2147483647,1),(1,1)),(1,0.0))
        self.assertEqual(player_position(-(1<<31),(1,1),(1,1)),(-(1<<31),0.0))
        with self.assertRaises(ValueError):player_position((1<<31)-1,(1,1),(2,1))

    def test_invalid_rates_and_ticks(self):
        for rate in ((0,1),(1,0),(-1,1),(True,1),(1,1.0),(1,),None,(1<<31,1)):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):player_position(1,rate,(30,1))
                with self.assertRaises(ValueError):player_position(1,(24000,1),rate)
        for tick in (True,1.0,None,1<<31,-(1<<31)-1):
            with self.assertRaises(ValueError):player_position(tick,(24000,1),(30,1))
