import unittest
from expedition33.new_game_story import Choice,StoryRow
from expedition33._story_navigation import direction_events
from types import SimpleNamespace

class NewGameChoiceTests(unittest.TestCase):
    def choice(self):
        c=Choice();c.register('opera','Sample Story');return c
    def test_default_is_original_and_no_apply_is_not_committed(self):
        c=self.choice();self.assertEqual(c.label,'Story: Original game')
        c.events([(10,'cycle')],7)
        self.assertIsNone(c.consume(7,fresh=True))
    def test_native_event_order_carries_selected_story_once(self):
        c=self.choice();c.events([(12,'apply'),(11,'cycle')],7)
        self.assertEqual(c.consume(7,fresh=True),{'pack':'opera'})
        self.assertIsNone(c.consume(7,fresh=True))
    def test_later_choice_does_not_change_already_applied_story(self):
        c=self.choice();c.events([(10,'apply'),(11,'cycle')],7)
        self.assertEqual(c.consume(7,fresh=True),{'pack':None})
    def test_existing_save_or_another_slot_cannot_consume_choice(self):
        for slot,fresh in ((7,False),(8,True)):
            c=self.choice();c.events([(10,'cycle'),(11,'apply')],7)
            self.assertIsNone(c.consume(slot,fresh=fresh));self.assertIsNone(c.pending)
    def test_repeated_registration_does_not_duplicate_option(self):
        c=self.choice();c.register('opera','Sample Story')
        self.assertEqual(len(c.options),2)
    def test_horizontal_navigation_wraps_and_retains_apply_order(self):
        c=self.choice();c.register('second','Second Story')
        c.events([(12,'next'),(11,'apply'),(10,'previous')],7)
        self.assertEqual(c.consume(7,fresh=True),{'pack':'second'})
        self.assertEqual(c.label,'Story: Original game')
    def test_hover_and_focus_update_native_description_without_overwriting_other_rows(self):
        c=self.choice();c.register('opera','Sample Story','Sample description')
        writes=[];inputs={'IsHovered':False,'HasAnyUserFocus':False}
        def call(obj,owner,name,**args):
            if name in inputs:return inputs[name]
            writes.append((obj,args['InText']))
        row=SimpleNamespace(button='button',tip_name='title',tip_description='description',_tip_hover=False,_tip_focus=False,_navigation_focus=False,_direction_receiver=object(),call=call)
        StoryRow.tooltip(row,c);self.assertFalse(writes)
        inputs['IsHovered']=True;StoryRow.tooltip(row,c)
        self.assertIn(c.description,writes[-1][1])
        writes.clear();StoryRow.tooltip(row,c);self.assertFalse(writes)
        inputs['IsHovered']=False;StoryRow.tooltip(row,c);self.assertFalse(writes)
        row._navigation_focus=True;StoryRow.tooltip(row,c)
        self.assertEqual(len(writes),2)
        c.events([(1,'cycle')],7);StoryRow.tooltip(row,c,changed=True)
        self.assertEqual(writes[-1],('description','Sample description\n\nUse Left / Right to change story.'))


class StoryNavigationTests(unittest.TestCase):
    def test_only_horizontal_engine_receipts_cycle_the_story(self):
        events = tuple(SimpleNamespace(monotonic_ms=i, arguments={'UINavigation': direction})
                       for i, direction in enumerate((2, 1, 3, 0, 6)))
        self.assertEqual(direction_events(events), ((1, 'next'), (3, 'previous')))
