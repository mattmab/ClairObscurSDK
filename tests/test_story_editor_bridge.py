import importlib
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
import test_story_packs
Mod=importlib.import_module('story_packs_test.mod').Mod

class EditorBridgeTests(unittest.TestCase):
    def test_status_reports_actual_save_story_world_and_errors_instead_of_preview_readiness(self):
        model=Mod();pack=test_story_packs.sample()
        model.library=N(get=lambda key:pack,packs={pack['id']:pack})
        state=N(get=lambda key:dict(pack=pack['id']))
        model.live=N(world='/Game/Test.Test',resolved=True,error=None,
                     playthroughs=N(key='save',state=state),runtime=N(actors={'boy':object()}),choices=lambda:None)
        status=model.status()
        self.assertEqual(status['active_story'],pack['title'])
        self.assertEqual(status['world'],'/Game/Test.Test')
        self.assertIn('1 story NPC active',status['message'])
        model.live.error='Placement failed'
        self.assertIn('Placement failed',model.status()['message'])
        model.live.error=None;model.live.resolved=False
        self.assertIn('Waiting for',model.status()['message'])
        model.live.resolved=True;state.get=lambda key:dict(pack=None)
        self.assertIn('Original game selected',model.status()['message'])

    def test_flight_capture_uses_admitted_map_and_leaves_other_placements_untouched(self):
        model=Mod();capture=Mock(return_value=dict(world='/Game/Test.Test',position=[1,2,3],yaw=45))
        model.session=N(_session=N(console=N(dispatcher=N(namespace={'scene_editor':N(capture_story_location=capture)}))))
        model.edit_pack=Mock()
        with patch('expedition33.map_runtime.context',return_value=dict(ready=True,world='/Game/Test.Test')):
            model.move_placement_from_flight('story.one','npc-one')
        model.edit_pack.assert_called_once_with('story.one','move','npc-one','/Game/Test.Test',[1,2,3],45)
        model.edit_pack.reset_mock()
        with patch('expedition33.map_runtime.context',return_value=dict(ready=True,world='/Game/Other.Other')):
            with self.assertRaisesRegex(ValueError,'different maps'):model.move_placement_from_flight('story.one','npc-one')
        model.edit_pack.assert_not_called()
        capture.reset_mock()
        with patch('expedition33.map_runtime.context',return_value=dict(ready=False)):
            with self.assertRaises(ValueError):model.move_placement_from_flight('story.one','npc-one')
        capture.assert_not_called()

    def test_author_preview_copies_selected_character_dialogue_and_flags_without_binding(self):
        model=Mod();document=test_story_packs.sample()
        document['characters']['lune']=dict(name='Lune',profile='lune')
        document['placements']=[dict(id='custom',character='lune',dialogue='first-meeting',requires={'hidden':True})]
        model.library=N(get=lambda key:document)
        state=N(get=Mock(return_value={'pack':document['id'],'flags':{'heard-story':True}}))
        model.live=N(runtime=N(actors={}),playthroughs=N(key='save',state=state))
        model._placement=Mock(return_value=(dict(id='authoring-preview',world='/Game/Test.Test',position=[1,2,3],yaw=45,radius=200),('visit',)))
        module=importlib.import_module('story_packs_test.preview')
        with patch.object(module.Preview,'__init__',return_value=None) as prepare:
            model.preview_placement(document['id'],'custom')
        args=prepare.call_args
        self.assertEqual(args.args[3]['character'],'lune')
        self.assertEqual(args.args[3]['dialogue'],'first-meeting')
        self.assertEqual(args.args[3]['requires'],{})
        self.assertEqual(args.kwargs['initial_flags'],{'heard-story':True})
        self.assertEqual(document['placements'][0]['requires'],{'hidden':True})
        with self.assertRaises(RuntimeError):model.preview_placement(document['id'],'custom')

    def test_preview_flag_changes_are_session_only_and_copy_the_input(self):
        PreviewState=importlib.import_module('story_packs_test.preview').PreviewState
        initial={'accepted':False};state=PreviewState(test_story_packs.sample(),initial)
        state.update_flags(state.key,{'accepted':True})
        self.assertEqual(initial,{'accepted':False})
        self.assertEqual(state.get(state.key)['flags'],{'accepted':True})
