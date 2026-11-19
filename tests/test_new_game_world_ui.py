import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from contextlib import nullcontext
from expedition33.new_game_story import NewGameStories,_current_button_metadata
class WorldUiTests(unittest.TestCase):
    def test_title_rebuild_uses_fresh_qualified_metadata_and_style(self):
        old=N(class_name='Class',name='Button',serial=0)
        fresh=N(class_name='Class',name='Button',serial=42)
        cached=N(objects=[old,N(class_name='World',name='OldWorld')],path_name=lambda o:'/Script/Test.Button')
        current=N(find_path=Mock(return_value=fresh))
        metadata,source=_current_button_metadata(dict(catalog=cached,style=old),current)
        self.assertEqual(metadata,[fresh]);self.assertIs(source['style'],fresh)
        self.assertEqual(current.find_path.call_count,2)
    def owner(self,row):
        owner=NewGameStories.__new__(NewGameStories);owner.closed=False;owner.error=None;owner.next_poll=0.
        owner.session=N(pid=1,_process_ui=N(context=N(kind='world')));owner.row=row;owner.choice=N(events=Mock())
        return owner
    def test_gameplay_without_a_title_row_does_not_borrow_story_reader(self):
        owner=self.owner(None)
        with patch('expedition33.new_game_story.shared_operation') as operation:owner.poll()
        operation.assert_not_called()
    def test_departing_title_preserves_apply_receipt_without_hover_queries(self):
        row=N(drain=Mock(return_value=[(1,'apply')]),slot=Mock(return_value=5),close=Mock(),tooltip=Mock(),call=Mock())
        owner=self.owner(row)
        with patch('expedition33.new_game_story.shared_operation',return_value=nullcontext()):owner.poll()
        owner.choice.events.assert_called_once_with([(1,'apply')],5)
        row.close.assert_called_once();row.tooltip.assert_not_called();row.call.assert_not_called();self.assertIsNone(owner.row)
    def test_title_return_uses_fresh_observation_even_when_attached_frontend_is_held(self):
        owner=self.owner(None)
        owner.session._process_ui.observed_context=N(kind='title')
        owner.parent=object();owner.choice.label='Story: Custom'
        row=N(build=Mock(return_value=True),show_choice=Mock(),drain=Mock(return_value=[]),tooltip=Mock())
        with patch('expedition33.new_game_story.shared_operation',return_value=nullcontext()),patch('expedition33.new_game_story.StoryRow',return_value=row):owner.poll()
        row.build.assert_called_once();row.tooltip.assert_called_once();self.assertIs(owner.row,row)
    def test_no_fresh_context_does_not_reuse_stale_title_frontend(self):
        owner=self.owner(None);owner.session._process_ui.context=N(kind='title')
        owner.session._process_ui.observed_context=None
        with patch('expedition33.new_game_story.shared_operation') as operation:owner.poll()
        operation.assert_not_called()
