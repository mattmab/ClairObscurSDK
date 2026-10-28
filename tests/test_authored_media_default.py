import copy,unittest
from unittest.mock import patch
from expedition33.cinematics.authored_timeline import create
from expedition33.cinematics.authored_media import suppression_sections,playback_document,playback_window


class DefaultMovieTests(unittest.TestCase):
    def fixture(self):
        array=lambda rows:dict(complete=True,array=rows,length=len(rows))
        bounds=lambda lo,hi:dict(complete=True,errors={},frame_range=dict(lower=lo,upper=hi))
        root='/Game/Movie.Movie';scene=root+':MovieScene';track=scene+'.SpawnTrack';section=track+'.SpawnSection'
        curve=dict(struct='/Script/MovieScene.MovieSceneBoolChannel',complete=True,errors={},
            fields=dict(Times=array([]),Values=array([]),DefaultValue=True,bHasDefaultValue=True))
        graph=dict(sequence=root,pending=[],nodes={root:dict(class_name='LevelSequence',fields={}),
            scene:dict(class_name='MovieScene',fields=dict(
                TickResolution=dict(complete=True,errors={},fields=dict(Numerator=24000,Denominator=1)),
                PlaybackRange=bounds(dict(kind='inclusive',value=0),dict(kind='exclusive',value=5179200)))),
            track:dict(class_name='MovieSceneSpawnTrack',fields=dict(Sections=array([dict(object_path=section)]))),
            section:dict(class_name='MovieSceneSpawnSection',fields=dict(BoolCurve=curve,bIsActive=True,
                SectionRange=bounds(dict(kind='open',value=None),dict(kind='open',value=None))))})
        return create(graph,'Default-visible movie'),dict(sequence=root,scene=scene,tracks=[track]),section
    def test_keyless_default_movie_uses_private_activity_and_exact_range(self):
        doc,actor,section=self.fixture();before=copy.deepcopy(doc)
        with patch('expedition33.cinematics.authored_media.source',return_value='/Game/Film.Film'),\
             patch('expedition33.cinematics.authored_media._media_actor',return_value=actor):
            self.assertEqual(suppression_sections(doc),(section,))
            self.assertEqual(playback_window(doc,(30,1)),(0.,6474.))
            playback=playback_document(doc)
        self.assertEqual(playback['key_edits'],[]);self.assertEqual(doc,before)
    def test_inactive_and_partial_default_channels_are_rejected(self):
        for mutation in ('inactive','incomplete'):
            doc,actor,section=self.fixture()
            fields=doc['source']['nodes'][section]['fields']
            if mutation=='inactive':fields['bIsActive']=False
            else:fields['BoolCurve']['fields']['Times']['length']=1
            with patch('expedition33.cinematics.authored_media._media_actor',return_value=actor):
                with self.assertRaises(ValueError):suppression_sections(doc)
    def test_section_range_edit_replaces_original_range_within_scene_bounds(self):
        doc,actor,section=self.fixture()
        bounds=doc['source']['nodes'][section]['fields']['SectionRange']['frame_range']
        bounds.update(lower=dict(kind='inclusive',value=24000),upper=dict(kind='exclusive',value=48000))
        doc['section_edits'][section]=dict(start=0,end=72000)
        with patch('expedition33.cinematics.authored_media.source',return_value='/Game/Film.Film'),\
             patch('expedition33.cinematics.authored_media._media_actor',return_value=actor):
            self.assertEqual(playback_window(doc,(30,1)),(0.,90.))
