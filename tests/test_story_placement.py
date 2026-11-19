import copy,importlib,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import test_story_packs

placement=importlib.import_module('story_packs_test.placement')
PackEditor=importlib.import_module('story_packs_test.authoring').PackEditor
PackLibrary=importlib.import_module('story_packs_test.storage').PackLibrary

class FinePlacementTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        root=Path(self.folder.name);d=PackEditor(root).create(test_story_packs.sample())
        d.place('boy','/Game/Test.Test',[100.,200.,300.],20.,'boy','first-meeting')
        library=PackLibrary(root);library.refresh();self.key=d.document['id']
        self.actor=N(state='visible',move=Mock())
        self.runtime=N(document=copy.deepcopy(d.document),actors={'boy':self.actor},native_active=set(),visit=(1,2),errors={})
        self.model=N(library=library,session=N(),preview=None,live=N(runtime=self.runtime,conversations=N(flow=None)))
        self.ctx=dict(ready=True,world='/Game/Test.Test',visit=(1,2))
    def test_precise_move_saves_and_moves_existing_carrier_without_retiring_cast(self):
        with patch('expedition33.map_runtime.context',return_value=self.ctx):
            result=placement.nudge(self.model,self.key,'boy',0,1,1.)
        self.assertEqual(result,dict(position=[101.,200.,300.],yaw=20.))
        self.actor.move.assert_called_once_with([101.,200.,300.],20.)
        self.assertEqual(PackEditor(self.model.library.root).open(self.key).document['placements'][0]['position'],[101.,200.,300.])
        self.assertIs(self.runtime.actors['boy'],self.actor)
    def test_map_change_or_active_conversation_cannot_move_or_save(self):
        original=copy.deepcopy(self.model.library.get(self.key))
        with patch('expedition33.map_runtime.context',return_value=dict(self.ctx,visit=(9,))):
            with self.assertRaisesRegex(ValueError,'finish loading'):placement.nudge(self.model,self.key,'boy',2,-1,100.)
        self.model.live.conversations.flow=object()
        with self.assertRaisesRegex(ValueError,'Finish the conversation'):placement.nudge(self.model,self.key,'boy',0,1,10.)
        self.assertEqual(self.model.library.get(self.key),original);self.actor.move.assert_not_called()
    def test_off_map_edit_uses_world_units_and_tenth_degree_yaw(self):
        self.runtime.actors={}
        result=placement.nudge(self.model,self.key,'boy',3,-1,1.)
        self.assertAlmostEqual(result['yaw'],19.9)
        with self.assertRaises(ValueError):placement.nudge(self.model,self.key,'boy',0,1,float('nan'))

    def test_saved_location_authoring_preview_can_move_without_binding_story(self):
        preview=N(document=copy.deepcopy(self.runtime.document),placement={'id':'boy'},flow=N(stage=None),runtime=self.runtime)
        self.model.preview=preview
        self.model.live=N(runtime=N(document=None),conversations=N(flow=None))
        with patch('expedition33.map_runtime.context',return_value=self.ctx):
            placement.nudge(self.model,self.key,'boy',2,1,10.)
        self.actor.move.assert_called_once_with([100.,200.,310.],20.)
        self.assertEqual(preview.document['placements'][0]['position'],[100.,200.,310.])
        self.assertIsNone(self.model.live.runtime.document)
        preview.flow.stage='lines'
        with self.assertRaisesRegex(ValueError,'Finish or remove'):placement.nudge(self.model,self.key,'boy',0,1,1.)
    def test_uncertain_movement_is_recorded_and_cannot_be_replayed(self):
        self.actor.move.side_effect=RuntimeError('ACK unknown')
        with patch('expedition33.map_runtime.context',return_value=self.ctx):
            with self.assertRaisesRegex(RuntimeError,'ACK unknown'):placement.nudge(self.model,self.key,'boy',1,-1,10.)
        self.assertIn('boy',self.runtime.errors)
        with self.assertRaisesRegex(ValueError,'Reload this story'):placement.nudge(self.model,self.key,'boy',1,-1,10.)
        self.assertEqual(self.actor.move.call_count,1)
