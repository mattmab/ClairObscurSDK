import unittest
from unittest.mock import patch
from expedition33.cinematics.authored_media import source,movie_path

class AuthoredMediaTests(unittest.TestCase):
    def fixture(self):
        path='/Game/Film.Film';section=path+':MovieScene.Track.Section'
        channel=dict(complete=True,errors={},fields=dict(Times=dict(complete=True,length=0,array=[]),Values=dict(complete=True,length=0,array=[]),DefaultValue=dict(complete=True,errors={},fields=dict(HardPtr=dict(object_path='/Game/Movie.Movie',**{'class':'FileMediaSource'})))))
        return dict(source=dict(sequence='/Game/Film.Film',pending=[],nodes={'declaration':dict(class_name='MovieScene',fields=dict(Spawnables=dict(array=[dict(fields=dict(ObjectTemplate={'class':'BP_MediaPlayer_C'}))]))),'track':dict(class_name='MovieSceneObjectPropertyTrack',fields=dict(PropertyBinding=dict(complete=True,errors={},fields=dict(PropertyName='MediaSource',PropertyPath='MediaSource')),Sections=dict(complete=True,length=1,array=[dict(object_path=section)]))),section:dict(class_name='MovieSceneObjectPropertySection',fields=dict(ObjectChannel=channel))})),section
    def test_exact_constant_source_and_unchanged_nonmedia_route(self):
        d,_=self.fixture()
        with patch('expedition33.cinematics.authored_media.bindings',return_value=[dict(sequence='/Game/Film.Film',kind='spawnable',template={'class':'BP_MediaPlayer_C'},tracks=['track'])]):
            self.assertEqual(source(d),'/Game/Movie.Movie')
        with patch('expedition33.cinematics.authored_media.bindings',return_value=[]):self.assertIsNone(source(d))
    def test_null_spawn_template_does_not_break_nonmedia_or_mask_a_real_movie(self):
        d,_=self.fixture()
        declarations=d['source']['nodes']['declaration']['fields']['Spawnables']['array']
        movie=declarations.pop()
        declarations.append(dict(fields=dict(ObjectTemplate=None)))
        with patch('expedition33.cinematics.authored_media.bindings',side_effect=AssertionError('No movie declared')):
            self.assertIsNone(source(d))
        declarations.append(movie)
        actor=dict(sequence='/Game/Film.Film',kind='spawnable',template={'class':'BP_MediaPlayer_C'},tracks=['track'])
        with patch('expedition33.cinematics.authored_media.bindings',return_value=[actor]):
            self.assertEqual(source(d),'/Game/Movie.Movie')
    def test_keyed_or_incomplete_channel_is_explicit(self):
        d,key=self.fixture();channel=d['source']['nodes'][key]['fields']['ObjectChannel']
        with patch('expedition33.cinematics.authored_media.bindings',return_value=[dict(sequence='/Game/Film.Film',kind='spawnable',template={'class':'BP_MediaPlayer_C'},tracks=['track'])]):
            channel['fields']['Times']=dict(complete=True,length=1,array=[12])
            with self.assertRaisesRegex(ValueError,'Keyed'):source(d)
            channel['complete']=False
            with self.assertRaisesRegex(ValueError,'Complete'):source(d)
    def test_single_root_movie_can_coexist_with_scene_cast_and_camera(self):
        d,_=self.fixture();root=d['source']['sequence']
        d['source']['nodes']['camera']=dict(class_name='MovieSceneCameraCutTrack',fields={})
        actors=[dict(sequence=root,kind='spawnable',template={'class':'BP_Cine_Lune_C'},tracks=[]),
                dict(sequence=root,kind='spawnable',template={'class':'BP_MediaPlayer_C'},tracks=['track'])]
        with patch('expedition33.cinematics.authored_media.bindings',return_value=actors):
            self.assertEqual(source(d),'/Game/Movie.Movie')
        with patch('expedition33.cinematics.authored_media.bindings',return_value=actors+[actors[-1]]):
            with self.assertRaisesRegex(ValueError,'Multiple authored movies'):source(d)
        actors[-1]['sequence']='/Game/Child.Child'
        with patch('expedition33.cinematics.authored_media.bindings',return_value=actors):
            with self.assertRaisesRegex(ValueError,'Nested movie LevelSequence'):source(d)
    def test_redundant_movie_keys_preserve_the_constant_source(self):
        import copy
        from expedition33.cinematics.authored_media import _constant_source
        d,key=self.fixture();channel=d['source']['nodes'][key]['fields']['ObjectChannel']
        fields=channel['fields'];default=fields['DefaultValue']
        frame=lambda n:dict(struct='/Script/CoreUObject.FrameNumber',complete=True,errors={},fields=dict(Value=n))
        fields['Times']=dict(complete=True,length=2,array=[frame(0),frame(24000)])
        fields['Values']=dict(complete=True,length=2,array=[copy.deepcopy(default),copy.deepcopy(default)])
        before=copy.deepcopy(channel)
        self.assertEqual(_constant_source(channel),'/Game/Movie.Movie')
        self.assertEqual(channel,before)
        fields['Values']['array'][1]['fields']['HardPtr']['object_path']='/Game/Other.Other'
        with self.assertRaisesRegex(ValueError,'media timeline adapter'):_constant_source(channel)
    def test_redundant_movie_keys_require_complete_ordered_matching_data(self):
        import copy
        from expedition33.cinematics.authored_media import _constant_source
        d,key=self.fixture();base=d['source']['nodes'][key]['fields']['ObjectChannel']
        frame=lambda n:dict(struct='/Script/CoreUObject.FrameNumber',complete=True,errors={},fields=dict(Value=n))
        for times,values in (([frame(0)],[]),([frame(0),frame(0)],[base['fields']['DefaultValue']]*2),
                ([frame(True)],[base['fields']['DefaultValue']]),([frame(1<<31)],[base['fields']['DefaultValue']]),
                ([frame(0)],[None])):
            channel=copy.deepcopy(base)
            channel['fields']['Times']=dict(complete=True,length=len(times),array=times)
            channel['fields']['Values']=dict(complete=True,length=len(values),array=values)
            with self.assertRaises(ValueError):_constant_source(channel)
    def test_private_copy_hides_only_media_spawn_keys_and_keeps_saved_document(self):
        import copy
        from test_authored_cast import fixture,array,struct,guid
        from expedition33.cinematics.authored_timeline import create
        from expedition33.cinematics.authored_media import playback_document
        graph=fixture();root=graph['sequence'];scene=root+':MovieScene'
        media=scene+'.MediaTrack';section=media+'.MediaSection';spawn=scene+'.SpawnTrack';spawn_section=spawn+'.SpawnSection'
        fields=graph['nodes'][scene]['fields']
        fields['Spawnables']['array'][0]['fields']['ObjectTemplate']['class']='BP_MediaPlayer_C'
        fields['Possessables']=array([])
        fields['TickResolution']=dict(complete=True,errors={},fields=dict(Numerator=24000,Denominator=1))
        fields['ObjectBindings']=array([struct('MovieSceneBinding',ObjectGuid=guid(1),Tracks=array([dict(object_path=media,**{'class':'MovieSceneObjectPropertyTrack'}),dict(object_path=spawn,**{'class':'MovieSceneSpawnTrack'})]))])
        example,key=self.fixture();graph['nodes'][media]=copy.deepcopy(example['source']['nodes']['track'])
        graph['nodes'][media]['fields']['Sections']=array([dict(object_path=section)])
        graph['nodes'][section]=copy.deepcopy(example['source']['nodes'][key])
        graph['nodes'][spawn]=dict(class_name='MovieSceneSpawnTrack',fields=dict(Sections=array([dict(object_path=spawn_section)])))
        frame=lambda n:dict(struct='/Script/CoreUObject.FrameNumber',fields=dict(Value=n),complete=True,errors={})
        graph['nodes'][spawn_section]=dict(class_name='MovieSceneSpawnSection',fields=dict(BoolCurve=dict(struct='/Script/MovieScene.MovieSceneBoolChannel',complete=True,errors={},fields=dict(Times=array([frame(-10),frame(0)]),Values=array([False,True]),bHasDefaultValue=True,DefaultValue=False))))
        document=create(graph,'Movie fixture');before=copy.deepcopy(document)
        from expedition33.cinematics.authored_media import start_frame,playback_window
        self.assertEqual(start_frame(document,(30,1)),0.)
        self.assertEqual(playback_window(document,(30,1)),(0.,None))
        result=playback_document(document)
        self.assertEqual(document,before);self.assertEqual(result['source'],document['source'])
        self.assertEqual(len(result['key_edits']),2)
        self.assertTrue(all(row['section']==spawn_section and row['value'] is False for row in result['key_edits']))
        curve=graph['nodes'][spawn_section]['fields']['BoolCurve']['fields']
        curve['Times']=array([frame(-10),frame(0),frame(24000)])
        curve['Values']=array([False,True,False])
        self.assertEqual(playback_window(create(graph,'Bounded movie'),(30,1)),(0.,30.))
        curve['Times']=array([frame(0),frame(24000),frame(48000)])
        curve['Values']=array([True,False,True])
        with self.assertRaisesRegex(ValueError,'One authored movie start'):
            playback_window(create(graph,'Multiple intervals'),(30,1))
        graph['nodes'][spawn_section]['fields']['BoolCurve']['fields']['DefaultValue']=True
        with self.assertRaisesRegex(ValueError,'Default-visible keyed'):playback_document(create(graph,'Unsupported default'))

    def test_mixed_scene_private_edit_targets_only_the_movie_actor(self):
        import copy
        from test_authored_cast import fixture,array,struct,guid
        from expedition33.cinematics.authored_timeline import create
        from expedition33.cinematics.authored_media import playback_document,start_frame
        graph=fixture();root=graph['sequence'];scene=root+':MovieScene'
        fields=graph['nodes'][scene]['fields']
        # Keep the original cast actor first: choosing the first spawnable
        # would edit the wrong actor and fail to suppress the movie Blueprint.
        fields['Spawnables']=array(fields['Spawnables']['array']+[struct('MovieSceneSpawnable',
            Guid=guid(3),Name='Movie',ObjectTemplate=dict(object_path=scene+'.Movie',**{'class':'BP_MediaPlayer_C'}))])
        media=scene+'.MediaTrack';section=media+'.MediaSection';spawn=scene+'.SpawnTrack';spawn_section=spawn+'.SpawnSection'
        fields['ObjectBindings']=array(fields['ObjectBindings']['array']+[struct('MovieSceneBinding',ObjectGuid=guid(3),
            Tracks=array([dict(object_path=media,**{'class':'MovieSceneObjectPropertyTrack'}),dict(object_path=spawn,**{'class':'MovieSceneSpawnTrack'})]))])
        fields['TickResolution']=dict(complete=True,errors={},fields=dict(Numerator=24000,Denominator=1))
        example,key=self.fixture();graph['nodes'][media]=copy.deepcopy(example['source']['nodes']['track'])
        graph['nodes'][media]['fields']['Sections']=array([dict(object_path=section)])
        graph['nodes'][section]=copy.deepcopy(example['source']['nodes'][key])
        graph['nodes'][spawn]=dict(class_name='MovieSceneSpawnTrack',fields=dict(Sections=array([dict(object_path=spawn_section)])))
        frame=lambda n:dict(struct='/Script/CoreUObject.FrameNumber',fields=dict(Value=n),complete=True,errors={})
        graph['nodes'][spawn_section]=dict(class_name='MovieSceneSpawnSection',fields=dict(BoolCurve=dict(
            struct='/Script/MovieScene.MovieSceneBoolChannel',complete=True,errors={},fields=dict(
                Times=array([frame(0)]),Values=array([True]),bHasDefaultValue=True,DefaultValue=False))))
        graph['nodes'][scene+'.CameraCut']=dict(class_name='MovieSceneCameraCutTrack',fields={})
        document=create(graph,'Mixed fixture');before=copy.deepcopy(document)
        self.assertEqual(source(document),'/Game/Movie.Movie')
        self.assertEqual(start_frame(document,(30,1)),0.)
        edited=playback_document(document)
        self.assertEqual(document,before)
        self.assertEqual([(e['section'],e['value']) for e in edited['key_edits']],[(spawn_section,False)])

    def test_movie_paths_are_direct_content_files(self):
        self.assertEqual(movie_path('./Movies/CS_Ending_P2.mp4'),'./Movies/CS_Ending_P2.mp4')
        for value in ('C:/Users/Developer/Videos/test.mp4','./Movies/../secret.mp4','./Movies/sub/test.mp4','https://example.org/x.mp4',None):
            with self.assertRaises(ValueError):movie_path(value)

    def test_nested_movie_window_and_edited_clock(self):
        from test_authored_media_occurrence import AuthoredMediaOccurrenceTests
        from expedition33.cinematics.authored_media import playback_window
        graph=AuthoredMediaOccurrenceTests().fixture();nodes=graph['nodes']
        array=lambda rows:dict(complete=True,length=len(rows),array=rows)
        frame=lambda n:dict(complete=True,errors={},fields=dict(Value=n))
        original,key=self.fixture()
        nodes['media']=original['source']['nodes']['track']
        nodes['media']['fields']['Sections']=array([dict(object_path='movie_section')])
        nodes['movie_section']=original['source']['nodes'][key]
        nodes['spawn']=dict(class_name='MovieSceneSpawnTrack',fields=dict(Sections=array([dict(object_path='spawn_section')])))
        nodes['spawn_section']=dict(class_name='MovieSceneSpawnSection',fields=dict(BoolCurve=dict(
            struct='/Script/MovieScene.MovieSceneBoolChannel',complete=True,errors={},fields=dict(
                Times=array([frame(0)]),Values=array([True]),DefaultValue=False,bHasDefaultValue=True))))
        nodes['childscene']['fields']['Spawnables']=array([dict(fields=dict(ObjectTemplate={'class':'BP_MediaPlayer_C'}))])
        actor=dict(sequence='child',scene='childscene',kind='spawnable',template={'class':'BP_MediaPlayer_C'},tracks=['media','spawn'])
        document=dict(source=graph,key_edits=[],section_edits={})
        with patch('expedition33.cinematics.authored_media.bindings',return_value=[actor]):
            self.assertEqual(source(document),'/Game/Movie.Movie')
            self.assertEqual(playback_window(document,(30,1)),(300.,600.))
            document['key_edits']=[dict(section='spawn_section',path=['BoolCurve'],index=0,at=48000,value=True)]
            self.assertEqual(playback_window(document,(30,1)),(330.,600.))
            document['section_edits']={'section':dict(start=480000,end=720000)}
            self.assertEqual(playback_window(document,(30,1)),(630.,900.))
            document['key_edits'][0]['at']=-48000
            with self.assertRaisesRegex(ValueError,'Clipped movie start'):
                playback_window(document,(30,1))
