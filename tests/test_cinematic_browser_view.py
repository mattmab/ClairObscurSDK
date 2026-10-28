import unittest
from dataclasses import dataclass
from types import SimpleNamespace as NS
from unittest.mock import Mock

from expedition33.cinematics.browser_view import BrowserView, availability_label
from expedition33.management import ManagementError


def scene(identity='a', **changes):
    row = dict(id=identity,title='Scene '+identity,reason='Current location preview.',
               supported=True,unlocked=True,replay_kind='preview',
               controls=(11,2,3,4,5),validation='live_partial')
    row.update(changes)
    return row


class BrowserViewTests(unittest.TestCase):
    def test_original_story_alternative_is_independent_of_movie_unlock_and_runtime(self):
        self.model.library=[scene(replay_kind='movie',supported=False,unlocked=None,
                                  original_supported=True)]
        frame=self.select()
        self.assertEqual([c.token for c in frame.controls if c.token in (1,4,13)],[13])
        self.assertIn('save effects',next(c.label for c in frame.controls if c.token==13))
        self.view.activate(frame.revision,13)
        self.model.control.assert_called_once_with('a',13)

    def setUp(self):
        self.registry = NS(_check=Mock())
        self.model = NS(library=[scene()],discovery={},show_all=True,reason='',
                        playback_status='Stopped',discover=Mock(),control=Mock(),
                        stop=Mock(return_value=True))
        self.view = BrowserView(self.registry,self.model)

    def select(self, identity='a'):
        self.view.selected = identity
        return self.view.render()

    def test_render_is_snapshot_only_and_never_discovers_or_controls_playback(self):
        self.view.render()
        self.select()
        self.model.discover.assert_not_called()
        self.model.control.assert_not_called()
        self.model.stop.assert_not_called()

    def test_stable_id_selection_survives_row_reordering(self):
        self.model.library = [scene('a'),scene('b')]
        frame = self.view.render()
        self.model.library.reverse()
        self.view.activate(frame.revision,100)
        self.assertEqual(self.view.selected,'a')

    def test_changed_selected_capability_is_rejected_before_model_control(self):
        frame = self.select()
        self.model.library[0]['supported'] = False
        with self.assertRaisesRegex(ManagementError,'selection changed'):
            self.view.activate(frame.revision,11)
        self.model.control.assert_not_called()

    def test_removed_scene_does_not_redirect_old_row_to_another_scene(self):
        frame = self.view.render()
        self.model.library = [scene('b')]
        with self.assertRaisesRegex(ManagementError,'selection changed'):
            self.view.activate(frame.revision,100)

    def test_changed_original_destination_revokes_old_play_control(self):
        self.model.library = [scene(replay_kind='original_action',original_destination='/Game/First')]
        frame = self.select()
        self.model.library[0]['original_destination'] = '/Game/Second'
        with self.assertRaisesRegex(ManagementError,'selection changed'):
            self.view.activate(frame.revision,1)
        self.model.control.assert_not_called()

    def test_revision_and_token_types_reject_stale_or_boolean_inputs(self):
        old = self.view.render()
        current = self.view.render()
        for revision,token in ((old.revision,100),(True,100),(current.revision,True)):
            with self.subTest(revision=revision,token=token), self.assertRaises(ManagementError):
                self.view.activate(revision,token)

    def test_title_and_media_do_not_offer_forged_pause_restart_or_rate(self):
        self.model.library = [scene(replay_kind='title',controls=(1,2,3,4,5))]
        frame = self.select()
        self.assertEqual([c.token for c in frame.controls if c.token in (1,2,3,4,5,11)],[1,4])
        for token in (2,3,5):
            with self.assertRaisesRegex(ManagementError,'only Play and Stop'):
                self.view.activate(frame.revision,token)

    def test_preview_and_story_routes_are_separate_and_story_effects_explicit(self):
        self.model.library[0]['original_supported'] = True
        frame = self.select()
        labels = {c.token:c.label for c in frame.controls}
        self.assertIn('current location',labels[11])
        self.assertEqual(labels[1],'Play original story action — save effects')
        self.assertNotIn('Travel',labels[1])
        self.view.activate(frame.revision,11)
        self.model.control.assert_called_once_with('a',11)

    def test_original_story_route_never_exposes_stop_even_if_bad_record_lists_it(self):
        self.model.library = [scene(replay_kind='original_action',controls=(1,4))]
        frame = self.select()
        self.assertEqual([c.token for c in frame.controls if c.token in (1,2,3,4,5)],[1])
        with self.assertRaises(ManagementError):
            self.view.activate(frame.revision,4)

    def test_filters_do_not_equate_unlock_with_playability(self):
        self.model.library = [scene('playable'), scene('unlocked',supported=False),
                              scene('locked',supported=False,unlocked=False)]
        frame = self.view.render()
        self.view.activate(frame.revision,10,value='playable')
        self.assertEqual([s['id'] for s in self.view.scenes()],['playable'])
        self.view.activate(self.view.revision,10,value='unlocked')
        self.assertEqual([s['id'] for s in self.view.scenes()],['playable','unlocked'])
        self.view.activate(self.view.revision,10,value='all')
        self.assertEqual(len(self.view.scenes()),3)

    def test_search_is_local_and_unsupported_text_editor_is_not_exposed(self):
        self.model.library = [scene('a',title='Simon intro'),scene('b',title='Paintress')]
        frame = self.view.search('simon')
        self.assertEqual([s['id'] for s in self.view.scenes()],['a'])
        self.assertFalse(any(c.token==12 for c in frame.controls))
        self.model.discover.assert_not_called()

    def test_pending_cleanup_preserves_selected_view_and_can_retry_close(self):
        self.model.stop.return_value = False
        frame = self.select()
        with self.assertRaisesRegex(ManagementError,'cleanup'):
            self.view.activate(frame.revision,6)
        self.assertFalse(self.view.closed)
        self.assertEqual(self.view.selected,'a')
        self.model.stop.return_value = True
        self.assertTrue(self.view.activate(frame.revision,6).closed)

    def test_back_waits_for_cleanup_and_does_not_drop_selection(self):
        self.model.stop.return_value = False
        frame = self.select()
        pending = self.view.activate(frame.revision,9)
        self.assertEqual(self.view.selected,'a')
        self.assertIn('cleanup',pending.status)
        self.model.stop.return_value = True
        self.view.activate(pending.revision,9)
        self.assertIsNone(self.view.selected)

    def test_duplicate_scene_ids_and_unknown_records_fail_before_controls(self):
        self.model.library = [scene(),scene()]
        with self.assertRaisesRegex(ManagementError,'duplicated'):
            self.view.render()
        self.model.control.assert_not_called()

    def test_unlocked_is_strict_boolean_for_preview(self):
        for unlock in (False,None,1,'true'):
            self.model.library = [scene(unlocked=unlock)]
            with self.subTest(unlock=unlock):
                self.assertEqual(availability_label(self.model.library[0]),'Unavailable')

    def test_immutable_record_snapshots_are_supported(self):
        @dataclass(frozen=True)
        class Record:
            id:str='a'
            title:str='A'
            supported:bool=True
            unlocked:bool=True
            replay_kind:str='movie'
        self.model.library = [Record()]
        frame = self.select()
        self.assertEqual([c.token for c in frame.controls if c.token in (1,4)],[1,4])

    def test_legacy_confirmed_display_without_unlock_does_not_grant_playback(self):
        del self.model.library
        self.model.discovery = {'confirmed':[{'id':'a','title':'A','supported':True,'replay_kind':'movie'}],
                                'all':[]}
        self.view.filter = 'unlocked'
        frame = self.view.render()
        self.assertTrue(any(control.token==100 for control in frame.controls))
        detail = self.view.activate(frame.revision,100)
        self.assertFalse(next(control for control in detail.controls if control.token==1).enabled)


if __name__ == '__main__':
    unittest.main()
