import copy,tempfile,unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.authored_timeline import set_npc,remove_npc,validate,TimelineStore
from expedition33.cinematics.blueprint_npc_tracks import BlueprintNpcTracks
from test_authored_timeline import fixture

KEY='a'*32


def document():
    return set_npc(fixture(),KEY,name='Sciel NPC',profile='sciel',start=10,end=20,offset=[120.,-50.,25.],yaw=90.)


class NpcTrackTests(unittest.TestCase):
    def test_preview_snapshot_avoids_revalidating_graph_and_copies_tracks(self):
        snapshot=validate(document())
        with patch('expedition33.cinematics.blueprint_npc_tracks.validate',side_effect=AssertionError('unexpected validation')):
            tracks=BlueprintNpcTracks._from_snapshot(object(),snapshot,(0,0,0))
        snapshot['npc_tracks'][0]['placement']['offset'][0]=999
        self.assertEqual(tracks.tracks[0]['placement']['offset'][0],120.)

    def test_saved_intervals_preserve_source_and_legacy_documents(self):
        source=fixture();before=copy.deepcopy(source)
        edited=document()
        self.assertEqual(edited['source'],source['source']);self.assertEqual(source,before)
        with tempfile.TemporaryDirectory() as folder:
            store=TimelineStore(folder);self.assertEqual(store.read(store.save(edited)),edited)
        legacy=fixture();legacy.pop('npc_tracks');self.assertEqual(validate(legacy)['npc_tracks'],[])
        self.assertEqual(remove_npc(edited,KEY),source)
        for field,value in (('start',True),('end',10),('profile','unknown'),('id','bad')):
            invalid=copy.deepcopy(edited);invalid['npc_tracks'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate(invalid)
        invalid=copy.deepcopy(edited);invalid['npc_tracks']*=2
        with self.assertRaisesRegex(ValueError,'duplicate'):validate(invalid)

    def test_interval_edges_and_backward_seek_construct_new_owners(self):
        first=Mock();first.close.return_value=True
        second=Mock();second.close.return_value=True
        tracks=BlueprintNpcTracks(object(),document(),(100,200,300))
        with patch('expedition33.cinematics.blueprint_npc_tracks.BlueprintActor',side_effect=(first,second)) as construct:
            self.assertTrue(tracks.sync(9.99));construct.assert_not_called()
            self.assertTrue(tracks.sync(10));self.assertTrue(tracks.sync(19.99))
            first.prepare.assert_called_once();first.reveal.assert_called_once()
            self.assertEqual(first.prepare.call_args.args[0],'sciel')
            self.assertEqual(first.prepare.call_args.args[1][4:7],(220.,150.,325.))
            self.assertFalse(tracks.needs_sync(15));self.assertTrue(tracks.needs_sync(20))
            self.assertTrue(tracks.sync(20));first.close.assert_called_once()
            self.assertTrue(tracks.sync(15));self.assertEqual(construct.call_count,2)
            self.assertTrue(tracks.close());second.close.assert_called_once()
        self.assertTrue(tracks.closed)

    def test_deferred_retirement_blocks_slot_reuse_and_unknown_spawn_is_never_replayed(self):
        first=Mock();first.close.side_effect=(False,True)
        second=Mock();second.prepare.side_effect=RuntimeError('unknown dispatch')
        tracks=BlueprintNpcTracks(object(),document(),(0,0,0))
        with patch('expedition33.cinematics.blueprint_npc_tracks.BlueprintActor',side_effect=(first,second)) as construct:
            tracks.sync(15)
            self.assertFalse(tracks.sync(20));self.assertIs(tracks.actors[KEY],first)
            self.assertTrue(tracks.sync(20))
            with self.assertRaisesRegex(RuntimeError,'unknown dispatch'):tracks.sync(15)
            self.assertIs(tracks.actors[KEY],second)
            with self.assertRaisesRegex(RuntimeError,'uncertain'):tracks.sync(15)
            self.assertEqual(construct.call_count,2)
        second.prepare.assert_called_once();second.reveal.assert_not_called()

    def test_world_retirement_uses_only_actor_retirement_and_retains_deferral(self):
        tracks=BlueprintNpcTracks(object(),document(),(0,0,0));actor=Mock()
        actor.retire_world.side_effect=(False,True);tracks.actors[KEY]=actor
        self.assertFalse(tracks.retire_world());self.assertIs(tracks.actors[KEY],actor)
        self.assertTrue(tracks.retire_world());actor.close.assert_not_called()
        self.assertFalse(tracks.actors)

    def test_reanchor_preserves_interval_owners_and_new_spawns_use_new_anchor(self):
        tracks=BlueprintNpcTracks(object(),document(),(0,0,0));actor=Mock()
        tracks.actors[KEY]=actor
        tracks.reanchor((1000,2000,3000))
        actor.move.assert_called_once_with((1120.,1950.,3025.),90.)
        self.assertIs(tracks.actors[KEY],actor)
        self.assertEqual(tracks.anchor,(1000,2000,3000))
        actor.move.side_effect=RuntimeError('unknown dispatch')
        with self.assertRaisesRegex(RuntimeError,'unknown'):tracks.reanchor((0,0,0))
        with self.assertRaisesRegex(RuntimeError,'uncertain'):tracks.reanchor((0,0,0))
        self.assertEqual(actor.move.call_count,2)

    def test_reanchor_preflights_all_destinations_before_moving_any_actor(self):
        other='b'*32
        edited=set_npc(document(),other,name='Second NPC',profile='lune',start=10,end=20,
                       offset=[200.,0.,0.],yaw=0.)
        tracks=BlueprintNpcTracks(object(),edited,(0,0,0))
        first,second=Mock(),Mock();tracks.actors={KEY:first,other:second}
        # First destination is valid, but the second would exceed the actor
        # placement limit. Neither actor may move and the old anchor remains.
        with self.assertRaisesRegex(ValueError,'destination'):
            tracks.reanchor((9_999_850,0,0))
        first.move.assert_not_called();second.move.assert_not_called()
        self.assertEqual(tracks.anchor,(0,0,0));self.assertFalse(tracks.failed)
        tracks.reanchor((100,0,0))
        first.move.assert_called_once();second.move.assert_called_once()

    def test_rotated_scene_keeps_active_and_new_npcs_in_same_local_frame(self):
        tracks=BlueprintNpcTracks(object(),document(),(1000,2000,3000),scene_yaw=90.)
        actor=Mock();actor.close.return_value=True
        with patch('expedition33.cinematics.blueprint_npc_tracks.BlueprintActor',return_value=actor):
            self.assertTrue(tracks.sync(15))
        pose=actor.prepare.call_args.args[1]
        for actual,expected in zip(pose[4:7],(1050.,2120.,3025.)):
            self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(abs(pose[2]),1.)
        tracks.reanchor((2000,3000,4000),scene_yaw=-90.)
        location,yaw=actor.move.call_args.args
        for actual,expected in zip(location,(1950.,2880.,4025.)):
            self.assertAlmostEqual(actual,expected)
        self.assertAlmostEqual(yaw,0.)
        self.assertIs(tracks.actors[KEY],actor)
        self.assertEqual(tracks.scene_yaw,-90.)
