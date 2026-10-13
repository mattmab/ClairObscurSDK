import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from expedition33.picto_cards import PictoCardLayout

class CardLayoutTests(unittest.TestCase):
    def test_four_stats_fit_and_original_width_is_retained_for_cleanup(self):
        e=SimpleNamespace(planner=SimpleNamespace(adopt_observations=Mock()),call=Mock())
        n=PictoCardLayout(e);n.adopt=Mock();n.call=e.call;n.labels_reset=True;box=SimpleNamespace(index=1,serial=2,address=3)
        wrapper=object();label=object()
        n.pending=(object(),[(wrapper,label,box,9,4,151.,False,{'X':1.,'Y':1.})],{4:4,2:2},{})
        n.apply()
        self.assertEqual(e.call.call_args_list[0].kwargs,{'InWidthOverride':64.})
        e.call.reset_mock()
        n.pending=(object(),[(wrapper,label,box,9,4,64.,True,{'X':.68,'Y':.68})],{4:4,2:2},{})
        n.apply()
        self.assertEqual(e.call.call_count,0)
        e.call.reset_mock()
        n.pending=(object(),[(wrapper,label,box,9,2,64.,True,{'X':.68,'Y':.68})],{4:4,2:2},{})
        n.apply()
        self.assertEqual([c.args[2] for c in e.call.call_args_list],['ClearWidthOverride','SetRenderScale'])
        self.assertFalse(n.saved)

    def test_normal_two_stat_cards_unchanged(self):
        e=SimpleNamespace(planner=SimpleNamespace(adopt_observations=Mock()),call=Mock())
        n=PictoCardLayout(e);n.adopt=Mock();n.call=e.call;n.labels_reset=True;box=SimpleNamespace(index=1,serial=2,address=3)
        n.pending=(object(),[(object(),object(),box,9,2,151.,False,{'X':1.,'Y':1.})],{4:4,2:2},{})
        n.apply();e.call.assert_not_called()
    def test_serial_assignment_preserves_original_layout_baseline(self):
        e=SimpleNamespace(planner=SimpleNamespace(adopt_observations=Mock()),call=Mock())
        n=PictoCardLayout(e);n.adopt=Mock();n.call=e.call;n.labels_reset=True;wrapper=object();label=object()
        box=SimpleNamespace(index=1,serial=0,address=3)
        n.pending=(object(),[(wrapper,label,box,1,4,151.,False,{'X':1.,'Y':1.})],{4:4},{})
        n.apply()
        promoted=SimpleNamespace(index=1,serial=12,address=3)
        n.pending=(object(),[(wrapper,label,promoted,1,4,64.,True,{'X':.68,'Y':.68})],{4:4},{})
        n.apply()
        saved=n.saved[(1,3)]
        self.assertEqual(saved[2:4],(151.,False))
        self.assertEqual(saved[5],{'X':1.,'Y':1.})
        self.assertIs(saved[1],promoted)

    def test_inactive_pooled_widgets_do_not_force_compact_layout(self):
        e=SimpleNamespace(planner=SimpleNamespace(adopt_observations=Mock()),call=Mock(return_value=2))
        n=PictoCardLayout(e);n.adopt=Mock();n.call=e.call;n.labels_reset=True;box=SimpleNamespace(index=1,serial=2,address=3)
        n.pending=(object(),[(object(),object(),box,9,4,151.,False,{'X':1.,'Y':1.})],{4:4},{4:object()})
        n.apply()
        self.assertEqual([c.args[2] for c in e.call.call_args_list],['GetNumEntries'])
        self.assertFalse(n.saved)

