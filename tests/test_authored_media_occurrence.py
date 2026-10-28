import copy,unittest
from fractions import Fraction
from expedition33.cinematics.authored_media_occurrence import occurrence

class AuthoredMediaOccurrenceTests(unittest.TestCase):
    def fixture(self):
        def rate(n):return dict(complete=True,errors={},fields=dict(Numerator=n,Denominator=1))
        def span(a,b):return dict(complete=True,errors={},frame_range=dict(lower=dict(kind='inclusive',value=a),upper=dict(kind='exclusive',value=b)))
        def array(rows):return dict(complete=True,length=len(rows),array=rows)
        def ref(p,c):return dict(object_path=p,**{'class':c})
        params=dict(bCanLoop=False,TimeScale=1.)
        for key in ('StartFrameOffset','EndFrameOffset','FirstLoopStartFrameOffset'):params[key]=dict(complete=True,errors={},fields=dict(Value=0))
        nodes={}
        for name,hz,a,b in (('root',24000,0,2400000),('child',48000,0,480000)):
            nodes[name]=dict(class_name='LevelSequence',fields=dict(MovieScene=ref(name+'scene','MovieScene')))
            nodes[name+'scene']=dict(class_name='MovieScene',fields=dict(TickResolution=rate(hz),PlaybackRange=span(a,b),Tracks=array([])))
        nodes['rootscene']['fields']['Tracks']=array([ref('track','MovieSceneCinematicShotTrack')])
        nodes['track']=dict(class_name='MovieSceneCinematicShotTrack',fields=dict(Sections=array([ref('section','MovieSceneCinematicShotSection')])))
        nodes['section']=dict(class_name='MovieSceneCinematicShotSection',fields=dict(SubSequence=ref('child','LevelSequence'),bIsActive=True,SectionRange=span(240000,480000),Parameters=dict(fields=params)))
        return dict(sequence='root',nodes=nodes,pending=[])
    def test_different_tick_rates_map_to_root_seconds(self):
        graph=self.fixture();before=copy.deepcopy(graph)
        self.assertEqual(occurrence(graph,'child'),(Fraction(10),Fraction(10),Fraction(20)))
        self.assertEqual(graph,before)
    def test_shared_child_is_two_occurrences(self):
        graph=self.fixture();refs=graph['nodes']['track']['fields']['Sections'];refs['array']*=2;refs['length']=2
        with self.assertRaisesRegex(ValueError,'Exactly one'):occurrence(graph,'child')
    def test_cycles_are_rejected(self):
        graph=self.fixture();graph['nodes']['section']['fields']['SubSequence']['object_path']='root'
        with self.assertRaisesRegex(ValueError,'Cyclic'):occurrence(graph,'child')
    def test_loops_speed_and_trim_are_explicit(self):
        for name,value in (('bCanLoop',True),('TimeScale',2.)):
            graph=self.fixture();graph['nodes']['section']['fields']['Parameters']['fields'][name]=value
            with self.assertRaisesRegex(ValueError,'clock adapter'):occurrence(graph,'child')
        graph=self.fixture();graph['nodes']['section']['fields']['Parameters']['fields']['StartFrameOffset']['fields']['Value']=1
        with self.assertRaisesRegex(ValueError,'trim offsets'):occurrence(graph,'child')
    def test_partial_array_or_open_range_is_rejected(self):
        graph=self.fixture();graph['nodes']['track']['fields']['Sections']['complete']=False
        with self.assertRaisesRegex(ValueError,'reference array'):occurrence(graph,'child')
        graph=self.fixture();graph['nodes']['section']['fields']['SectionRange']['frame_range']['lower']['kind']='open'
        with self.assertRaisesRegex(ValueError,'half-open'):occurrence(graph,'child')

    def test_unrelated_trimmed_3d_shot_does_not_block_movie(self):
        graph=self.fixture();nodes=graph['nodes']
        nodes['other']=copy.deepcopy(nodes['child'])
        nodes['other']['fields']['MovieScene']['object_path']='otherscene'
        nodes['otherscene']=copy.deepcopy(nodes['childscene'])
        nodes['othersection']=copy.deepcopy(nodes['section'])
        nodes['othersection']['fields']['SubSequence']['object_path']='other'
        nodes['othersection']['fields']['Parameters']['fields']['StartFrameOffset']['fields']['Value']=488000
        refs=nodes['track']['fields']['Sections'];refs['array'].append(dict(object_path='othersection',**{'class':'MovieSceneCinematicShotSection'}));refs['length']=2
        self.assertEqual(occurrence(graph,'child'),(Fraction(10),Fraction(10),Fraction(20)))
        # Timing on the movie's own path is still rejected.
        with self.assertRaisesRegex(ValueError,'trim offsets'):occurrence(graph,'other')

    def test_unrelated_cycle_is_still_rejected(self):
        graph=self.fixture();nodes=graph['nodes']
        nodes['cycle']=copy.deepcopy(nodes['section'])
        nodes['cycle']['fields']['SubSequence']['object_path']='root'
        refs=nodes['track']['fields']['Sections'];refs['array'].append(dict(object_path='cycle',**{'class':'MovieSceneCinematicShotSection'}));refs['length']=2
        with self.assertRaisesRegex(ValueError,'Cyclic'):occurrence(graph,'child')
