from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33.story_npc import StoryNpc, visual_pose


class StoryNpcFallbackTests(unittest.TestCase):
    def owner(self):
        npc=StoryNpc.__new__(StoryNpc)
        npc.scope=object();npc.state='visible';npc.visual=None
        npc._visual_transform=(0.,0.,0.,1.,100.,200.,300.,0.,1.,1.,1.,0.)
        return npc

    def test_lazy_visual_is_published_before_construction_and_stays_hidden(self):
        npc=self.owner()
        visual=N(profile='sophie',state='new',reveal=Mock())
        def prepare(profile,pose):
            self.assertIs(npc.visual,visual)
            self.assertEqual(profile,'sophie')
            self.assertEqual(pose,visual_pose(npc._visual_transform,'sophie'))
            visual.state='prepared'
        visual.prepare=Mock(side_effect=prepare)
        with patch('expedition33.cinematics.blueprint_actor.BlueprintActor',return_value=visual) as create:
            self.assertIs(npc.ensure_visual('sophie'),visual)
            self.assertIs(npc.ensure_visual('sophie'),visual)
        create.assert_called_once_with(npc.scope);visual.prepare.assert_called_once()
        visual.reveal.assert_not_called();self.assertEqual(npc.state,'visible')

    def test_failed_construction_stays_owned_and_cannot_be_replayed(self):
        npc=self.owner()
        visual=N(profile='gustave',state='failed',prepare=Mock(side_effect=RuntimeError('ACK lost')))
        with patch('expedition33.cinematics.blueprint_actor.BlueprintActor',return_value=visual) as create:
            with self.assertRaisesRegex(RuntimeError,'ACK lost'):npc.ensure_visual('gustave')
            with self.assertRaisesRegex(RuntimeError,'Prepared story carrier'):npc.ensure_visual('gustave')
        self.assertIs(npc.visual,visual);self.assertEqual(npc.state,'failed')
        create.assert_called_once();visual.prepare.assert_called_once()

    def test_different_profile_or_unfinished_visual_is_not_replaced(self):
        for profile,state in (('sophie','prepared'),('gustave','failed'),('gustave','preparing')):
            with self.subTest(profile=profile,state=state):
                npc=self.owner();visual=N(profile=profile,state=state);npc.visual=visual
                with patch('expedition33.cinematics.blueprint_actor.BlueprintActor') as create:
                    with self.assertRaisesRegex(RuntimeError,'not replayed'):npc.ensure_visual('gustave')
                self.assertIs(npc.visual,visual);create.assert_not_called()

    def test_failed_visual_owner_construction_cannot_be_retried(self):
        npc=self.owner()
        with patch('expedition33.cinematics.blueprint_actor.BlueprintActor',side_effect=RuntimeError('owner unavailable')) as create:
            with self.assertRaisesRegex(RuntimeError,'owner unavailable'):npc.ensure_visual('gustave')
            with self.assertRaisesRegex(RuntimeError,'Prepared story carrier'):npc.ensure_visual('gustave')
        create.assert_called_once();self.assertEqual(npc.state,'failed')

    def test_cleanup_waits_for_the_lazy_visual_before_retiring_carrier(self):
        npc=self.owner();npc.visual=N(retire_world=Mock(return_value=False))
        npc.actor=N(retire_world=Mock(return_value=True))
        self.assertFalse(npc.retire_world());npc.actor.retire_world.assert_not_called()
        npc.visual.retire_world.return_value=True
        self.assertTrue(npc.retire_world());npc.actor.retire_world.assert_called_once()
        self.assertEqual(npc.state,'closed')


if __name__=='__main__':unittest.main()
