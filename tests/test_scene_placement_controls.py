import unittest,copy
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from test_runtime_scene_editor import package
from scene_editor_tests.sequence_viewport import nudge_scene
from scene_editor_tests.timeline import TimelineMenu
from scene_editor_tests.authored_preview import AuthoredPreview
class PlacementControlsTests(unittest.TestCase):
 def test_visibility_action_hides_visible_overlay_and_restores_hidden_overlay(self):
  for hidden in (False,True):
   p=object.__new__(AuthoredPreview);p.closed=False;p.pending='visibility';p.ready=True;p.editing_only=False
   p.scope=N(_session=N(_transport=N(sequence_placement_input_protocol=0)))
   p.menu=Mock(hidden=hidden)
   self.assertFalse(p.poll());p.menu.set_sequence_shown.assert_called_once_with(hidden)
 def test_nudge_moves_all_owners_without_rebuilding_flight(self):
  doc={'source':{},'scene_position':[10,20,30]};work=Mock(document=copy.deepcopy(doc))
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(10,20,30),profile=N(anchor=(1,2,3)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0))),sequence=Mock(),npcs=Mock(),flight=Mock(),menu=Mock(),frame=100,subframe=.25,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy):nudge_scene(p,(.1,-.2,.3))
  p.sequence.move_origin.assert_called_once_with((9.1,17.8,27.3));p.npcs.reanchor.assert_called_once_with([10.1,19.8,30.3],0.)
  p.sequence.seek_frame.assert_called_once_with(100,.25);p.flight.restore_pose.assert_called_once()
  p.flight.stop.assert_not_called();p.sequence.close.assert_not_called();work.place_scene.assert_called_once_with([10.1,19.8,30.3])
 def test_nudge_retains_rotation_and_rotates_npc_around_anchor(self):
  doc={'source':{},'scene_position':[10,20,30],'scene_yaw':90.};work=Mock(document=copy.deepcopy(doc))
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(10,20,30),scene_yaw=90.,profile=N(anchor=(1,2,3)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=1))),sequence=Mock(),npcs=Mock(),flight=Mock(),menu=Mock(),frame=10,subframe=0.,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy):nudge_scene(p,(1,0,0))
  translation,yaw=p.sequence.move_origin_transform.call_args.args
  self.assertAlmostEqual(translation[0],13.);self.assertAlmostEqual(translation[1],19.);self.assertEqual(translation[2],27.);self.assertEqual(yaw,90.)
  p.npcs.reanchor.assert_called_once_with([11,20,30],90.)
 def test_unapplied_cast_edit_cannot_be_silently_overwritten(self):
  p=N(document={'cast_edits':[]},editor=N(workspace=Mock(document={'cast_edits':['staged']})),sequence=Mock())
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),self.assertRaisesRegex(ValueError,'Apply'):nudge_scene(p,(1,0,0))
  p.sequence.move_origin.assert_not_called()
 def test_npc_destination_is_checked_before_the_sequence_moves(self):
  from expedition33.cinematics.blueprint_npc_tracks import BlueprintNpcTracks
  doc={'source':{},'scene_position':[10,20,30]};work=Mock(document=copy.deepcopy(doc))
  npc=BlueprintNpcTracks.__new__(BlueprintNpcTracks)
  npc._initialize(object(),[{'id':'npc','placement':{'offset':[200.,0.,0.],'yaw':0.}}],(10,20,30),0.)
  actor=Mock();npc.actors['npc']=actor
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(9_999_850,0,0),profile=N(anchor=(0,0,0)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0))),sequence=Mock(),npcs=npc,flight=Mock(),menu=Mock(),frame=0,subframe=0.,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),self.assertRaisesRegex(ValueError,'NPC destination'):
   nudge_scene(p,(0,0,0))
  p.sequence.move_origin.assert_not_called();actor.move.assert_not_called();work.place_scene.assert_not_called()
  self.assertFalse(npc.failed)
 def test_staged_placement_checks_npcs_before_moving_sequence(self):
  from contextlib import nullcontext
  original={'scene_position':[0,0,0],'scene_yaw':0.,'cast_edits':[],'npc_tracks':[]}
  candidate=dict(original,scene_position=[100,0,0])
  p=object.__new__(AuthoredPreview);p.closed=False;p.pending='apply';p.ready=True;p.playing=False
  p.editing_only=False;p.document=original;p.editor=N(document=candidate);p.menu=Mock()
  p.scope=N(pid=1,_session=N(_transport=N(_executable='reader',sequence_origin_update_protocol=1,sequence_origin_transform_protocol=0)))
  p.sequence=Mock();p.sequence._call.return_value={'Time':{'FrameNumber':{'Value':42},'SubFrame':.25}}
  p.profile=N(anchor=(0,0,0));p.replacements=();p.npcs=Mock();p.npcs.validate_reanchor.side_effect=ValueError('NPC destination exceeds placement bounds')
  p._sync_media=Mock(return_value=True)
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),\
       patch('expedition33._timeline_actor_channel.validate_count'),\
       patch('expedition33.cinematics.authored_copy.require_key_edit_support'),\
       patch('scene_editor_tests.authored_preview.shared_operation',return_value=nullcontext()),\
       self.assertRaisesRegex(ValueError,'NPC destination'):
   p.poll()
  p.sequence.move_origin.assert_not_called();p.npcs.reanchor.assert_not_called()
 def test_replacement_destination_is_checked_before_sequence_or_other_actors_move(self):
  edits=[{'placement':{'offset':[20.,0.,0.],'yaw':0.}}, {'placement':{'offset':[200.,0.,0.],'yaw':0.}}]
  doc={'source':{},'scene_position':[0,0,0],'cast_edits':edits};work=Mock(document=copy.deepcopy(doc))
  first,second=Mock(),Mock()
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(9_999_850,0,0),profile=N(anchor=(0,0,0)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0))),sequence=Mock(),replacements=(first,second),npcs=None,flight=Mock(),menu=Mock(),frame=0,subframe=0.,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),self.assertRaisesRegex(ValueError,'Replacement destination'):
   nudge_scene(p,(0,0,0))
  p.sequence.move_origin.assert_not_called();first.move.assert_not_called();second.move.assert_not_called()
 def test_nudge_actor_failure_after_origin_move_is_not_recoverable_input_error(self):
  doc={'source':{},'scene_position':[10,20,30]};work=Mock(document=copy.deepcopy(doc))
  npc=Mock();npc.reanchor.side_effect=ValueError('Actor position exceeds bound')
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(10,20,30),profile=N(anchor=(1,2,3)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0))),sequence=Mock(),npcs=npc,flight=Mock(),menu=Mock(),frame=100,subframe=0.,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),self.assertRaisesRegex(RuntimeError,'closing preview'):
   nudge_scene(p,(1,0,0))
  p.sequence.move_origin.assert_called_once()
  npc.reanchor.assert_called_once()
  p.sequence.seek_frame.assert_not_called();p.flight.restore_pose.assert_not_called();work.place_scene.assert_not_called()
  self.assertIs(p.document,doc);self.assertEqual(p.scene_anchor,(10,20,30))
 def test_nudge_origin_value_error_does_not_retry_or_publish_destination(self):
  doc={'source':{},'scene_position':[10,20,30]};work=Mock(document=copy.deepcopy(doc))
  sequence=Mock();sequence.move_origin.side_effect=ValueError('Native placement failed')
  p=N(editor=N(workspace=work),document=doc,scene_anchor=(10,20,30),profile=N(anchor=(1,2,3)),scope=N(_session=N(_transport=N(sequence_origin_transform_protocol=0))),sequence=sequence,npcs=Mock(),flight=Mock(),menu=Mock(),frame=100,subframe=0.,detail=lambda:'detail')
  with patch('expedition33.cinematics.authored_timeline.validate',side_effect=copy.deepcopy),self.assertRaisesRegex(RuntimeError,'closing preview'):
   nudge_scene(p,(1,0,0))
  sequence.move_origin.assert_called_once();p.npcs.reanchor.assert_not_called();work.place_scene.assert_not_called()
  self.assertIs(p.document,doc);self.assertEqual(p.scene_anchor,(10,20,30))
 def test_placement_failure_queues_owned_preview_cleanup(self):
  model=package.Mod();model.session=object()
  preview=N(poll=Mock(side_effect=RuntimeError('Scene placement failed; closing preview')),queue=Mock(),error=None)
  model.authored_preview=preview;model.poll()
  self.assertIs(model.authored_preview,preview)
  self.assertIn('Scene placement failed',preview.error)
  preview.queue.assert_called_once_with('close')
 def test_hiding_keeps_owner_and_disables_invisible_hit_targets(self):
  menu=object.__new__(TimelineMenu);menu.model=N(media=None);menu.panel=Mock(canvas='canvas',visible=0,invisible=4);menu.hidden=False
  menu.set_sequence_shown(False);self.assertTrue(menu.hidden)
  menu.panel.hide.assert_not_called();menu.panel._render_call.assert_any_call('canvas','Widget','SetVisibility',InVisibility=4)
  menu.set_sequence_shown(True);self.assertFalse(menu.hidden)
