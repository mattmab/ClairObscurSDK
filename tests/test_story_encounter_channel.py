import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.story_encounter_channel import StoryEncounterChannel

class Tests(unittest.TestCase):
    def setup_channel(self,previous=None):
        transport=N(_enemy_spawn_owner=previous)
        scope=N(_check=Mock(),_session=N(_transport=transport))
        owner=N(close=Mock(return_value=True))
        def reserve(scope):transport._enemy_spawn_owner=owner;return owner
        return transport,scope,owner,reserve
    def test_idle_editor_owner_restored_only_after_ack(self):
        previous=N(has_native_work=False,_closed=False,phase='ready')
        transport,scope,owner,reserve=self.setup_channel(previous)
        with patch('expedition33.story_encounter_channel.EnemySpawnOwner',side_effect=reserve):
            channel=StoryEncounterChannel(scope);self.assertIs(channel.acquire(),owner)
            owner.close.return_value=False
            self.assertFalse(channel.close());self.assertIs(transport._enemy_spawn_owner,owner)
            def ack():transport._enemy_spawn_owner=None;return True
            owner.close.side_effect=ack
            self.assertTrue(channel.close());self.assertIs(transport._enemy_spawn_owner,previous)
    def test_active_or_uncertain_encounter_cannot_be_displaced(self):
        for previous in (N(has_native_work=True,_closed=False,phase='ready'),N(has_native_work=False,_closed=False,phase='unknown')):
            transport,scope,_,reserve=self.setup_channel(previous)
            with patch('expedition33.story_encounter_channel.EnemySpawnOwner',side_effect=reserve) as ctor:
                with self.assertRaises(RuntimeError):StoryEncounterChannel(scope).acquire()
                ctor.assert_not_called();self.assertIs(transport._enemy_spawn_owner,previous)
    def test_constructor_failure_restores_dormant_owner(self):
        previous=N(has_native_work=False,_closed=False,phase='ready')
        transport,scope,_,_=self.setup_channel(previous)
        with patch('expedition33.story_encounter_channel.EnemySpawnOwner',side_effect=RuntimeError('rejected')):
            with self.assertRaises(RuntimeError):StoryEncounterChannel(scope).acquire()
        self.assertIs(transport._enemy_spawn_owner,previous)
        self.assertIsNone(transport._story_encounter_channel)
    def test_disabled_editor_is_not_resurrected(self):
        previous=N(has_native_work=False,_closed=False,phase='ready')
        transport,scope,owner,reserve=self.setup_channel(previous)
        with patch('expedition33.story_encounter_channel.EnemySpawnOwner',side_effect=reserve):
            channel=StoryEncounterChannel(scope);channel.acquire();previous._closed=True
            def ack():transport._enemy_spawn_owner=None;return True
            owner.close.side_effect=ack;self.assertTrue(channel.close())
            self.assertIsNone(transport._enemy_spawn_owner)
if __name__=='__main__':unittest.main()
