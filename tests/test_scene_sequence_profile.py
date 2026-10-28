import unittest
from unittest.mock import patch
from test_runtime_scene_editor import package
from scene_editor_tests.sequence_profile import channel_start,source_anchor,imported_profile


def channel(value):
    return dict(complete=True,errors={},fields=dict(bHasDefaultValue=True,DefaultValue=value))


class ImportedProfileTests(unittest.TestCase):
    def test_menu_eligibility_does_not_walk_cast_or_compute_anchor(self):
        from scene_editor_tests.authored_preview import preview_supported
        path='/Game/Cinematics/Example/MCS_Example.MCS_Example'
        document=dict(source=dict(sequence=path,nodes={path:dict(class_name='LevelSequence',fields={})}))
        with patch('scene_editor_tests.sequence_profile.source_anchor',side_effect=AssertionError('UI must not compute anchor')):
            self.assertTrue(preview_supported(document))
            document['source']['nodes'][path]['class_name']='Actor'
            self.assertFalse(preview_supported(document))
        self.assertFalse(preview_supported(None))
        self.assertFalse(preview_supported(dict(source={})))

    def test_root_actor_anchors_exclude_component_offsets_and_prefer_characters(self):
        nodes={};cast=[]
        for name,kind,cls,position in (('A','spawnable','BP_Cine_Lune_C',(10000,20000,300)),
                ('B','spawnable','BP_Cine_Verso_C',(10400,20400,500)),
                ('camera','spawnable','CineCameraActor',(15000,25000,1500)),
                ('component','possessable','SceneComponent',(0,0,0))):
            track=name+'.track';section=track+'.section'
            cast.append(dict(kind=kind,template=dict(class_name=cls,**{'class':cls}),tracks=[track]))
            nodes[track]=dict(class_name='MovieScene3DTransformTrack',fields=dict(Sections=dict(complete=True,array=[dict(object_path=section)])))
            nodes[section]=dict(class_name='MovieScene3DTransformSection',fields=dict(Translation=dict(static_array=[channel(v) for v in position])))
        with patch('scene_editor_tests.sequence_profile.bindings',return_value=cast):
            self.assertEqual(source_anchor(dict(nodes=nodes)),(10200,20200,400))

    def test_non_whitelisted_imported_sequence_can_use_the_owned_player(self):
        from scene_editor_tests.authored_preview import profile_for
        path='/Game/Cinematics/Example/MCS_Example.MCS_Example'
        document=dict(source=dict(sequence=path,nodes={path:dict(class_name='LevelSequence',fields={})}))
        profile=imported_profile(document)
        self.assertEqual(profile_for(document).sequence,path)
        self.assertEqual((profile.sequence,profile.saved_id,profile.anchor),(path,'Example',(0.,0.,0.)))
        document['source']['nodes'][path]['class_name']='Actor'
        self.assertIsNone(imported_profile(document))

    def test_incomplete_or_nonfinite_channel_cannot_set_a_scene_anchor(self):
        self.assertIsNone(channel_start(channel(float('nan'))))
        self.assertIsNone(channel_start(dict(complete=False,fields=dict(DefaultValue=20))))
        self.assertEqual(channel_start(channel(-400000)),-400000)
