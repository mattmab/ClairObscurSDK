import copy,unittest
from fractions import Fraction
from test_runtime_scene_editor import package
from scene_editor_tests.sequence_projection import root_sections,project_sections
from test_authored_timeline import fixture,ROOT,SECTION


def document():
    d=fixture();scene=ROOT+':MovieScene'
    d['source']['nodes'][ROOT]['fields']['MovieScene']={'object_path':scene,'class':'MovieScene'}
    d['source']['nodes'][scene]=dict(class_name='MovieScene',fields=dict(
        TickResolution=dict(complete=True,errors={},fields=dict(Numerator=24000,Denominator=1))))
    return d


class SequenceProjectionTests(unittest.TestCase):
    def nested(self):
        d=document();nodes=d['source']['nodes'];child='/Game/Child.Child';scene=child+':MovieScene'
        nodes[ROOT]['fields']['MovieScene']['object_path']=ROOT+':MovieScene'
        shot=nodes[SECTION];shot['fields']['SectionRange']['frame_range']=dict(lower=dict(kind='inclusive',value=74400),upper=dict(kind='exclusive',value=98400))
        shot['fields']['SubSequence']=dict(object_path=child)
        shot['fields']['Parameters']=dict(fields=dict(TimeScale=2.,bCanLoop=False,
            StartFrameOffset=dict(complete=True,errors={},fields=dict(Value=2400))),errors={'Flags':'unsupported'},complete=False)
        nodes[child]=dict(class_name='LevelSequence',fields=dict(MovieScene=dict(object_path=scene)))
        nodes[scene]=dict(class_name='MovieScene',fields=dict(
            TickResolution=dict(complete=True,errors={},fields=dict(Numerator=12000,Denominator=1)),
            PlaybackRange=dict(frame_range=dict(lower=dict(kind='inclusive',value=4800),upper=dict(kind='exclusive',value=48000)))))
        section=scene+'.AudioTrack.AudioSection';nodes[section]=copy.deepcopy(nodes[SECTION])
        nodes[section]['fields'].pop('SubSequence');nodes[section]['class_name']='MovieSceneAudioSection'
        nodes[section]['fields']['SectionRange']['frame_range']=dict(lower=dict(kind='inclusive',value=7200),upper=dict(kind='exclusive',value=19200))
        return d,child,section
    def test_nested_rate_offsets_and_lower_bound_map_to_parent_interval(self):
        d,child,path=self.nested();before=copy.deepcopy(d)
        rows,issues=project_sections(d,(30,1));self.assertEqual(issues,())
        row=next(r for r in rows if r['path']==path)
        self.assertEqual((row['start'],row['end']),(93,108));self.assertEqual(row['depth'],1)
        self.assertEqual(d,before)
        d['section_edits'][path]=dict(start=0,end=48000)
        row=next(r for r in project_sections(d,(30,1))[0] if r['path']==path)
        self.assertEqual((row['start'],row['end']),(93,123))
    def test_loop_reverse_and_incomplete_child_are_explicit_not_wrong_markers(self):
        for change in ('loop','reverse','missing'):
            d,child,path=self.nested()
            if change=='loop':d['source']['nodes'][SECTION]['fields']['Parameters']['fields']['bCanLoop']=True
            elif change=='reverse':d['source']['nodes'][SECTION]['fields']['Parameters']['fields']['TimeScale']=-1.
            else:d['source']['nodes'].pop(child)
            rows,issues=project_sections(d,(30,1))
            self.assertTrue(issues);self.assertNotIn(path,[r['path'] for r in rows])
    def test_reused_child_keeps_both_instances_and_cycle_is_bounded(self):
        d,child,path=self.nested();other=SECTION+'2'
        d['source']['nodes'][other]=copy.deepcopy(d['source']['nodes'][SECTION])
        d['section_edits'][other]=dict(start=98400,end=122400)
        rows,issues=project_sections(d,(30,1));self.assertFalse(issues)
        children=[r for r in rows if r['path']==path]
        self.assertEqual([r['start'] for r in children],[93,123]);self.assertNotEqual(children[0]['instance'],children[1]['instance'])
        d['source']['nodes'][path]['fields'].update(SubSequence=dict(object_path=ROOT),Parameters=copy.deepcopy(d['source']['nodes'][SECTION]['fields']['Parameters']))
        d['source']['nodes'][ROOT+':MovieScene']['fields']['PlaybackRange']=copy.deepcopy(d['source']['nodes'][child+':MovieScene']['fields']['PlaybackRange'])
        self.assertTrue(project_sections(d,(30,1))[1])
    def test_source_ticks_project_to_native_frames_without_playback_origin_subtraction(self):
        d=document();d['section_edits'][SECTION]=dict(start=74400,end=1739200)
        before=copy.deepcopy(d);row=root_sections(d,(30,1))[0]
        self.assertEqual((row['start'],row['end']),(93,2174));self.assertEqual(d,before)
    def test_fractional_rate_retains_precision_and_nested_sections_are_not_mislabelled(self):
        d=document();nested=ROOT+'_Nested:MovieScene.Track.Section'
        d['source']['nodes'][nested]=copy.deepcopy(d['source']['nodes'][SECTION])
        rows=root_sections(d,(30000,1001))
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['end'],Fraction(60000,1001))
    def test_scene_index_excludes_similar_prefixes_and_refreshes_edits(self):
        d=document();nodes=d['source']['nodes'];scene=ROOT+':MovieScene'
        impostor=scene+'Extra.Track.Section'
        nodes[impostor]=copy.deepcopy(nodes[SECTION])
        rows,issues=project_sections(d,(30,1))
        self.assertEqual(issues,());self.assertEqual([r['path'] for r in rows],[SECTION])
        before=rows[0]['end']
        d['section_edits'][SECTION]=dict(start=0,end=24000)
        rows,_=project_sections(d,(30,1))
        self.assertEqual(rows[0]['end'],30);self.assertNotEqual(before,30)
        # Newly added sections must appear on the next projection, in source order.
        added=scene+'.OtherTrack.Section';nodes[added]=copy.deepcopy(nodes[SECTION])
        self.assertEqual([r['path'] for r in project_sections(d,(30,1))[0]],[SECTION,added])

    def test_missing_or_incomplete_timebase_is_explicit(self):
        with self.assertRaisesRegex(ValueError,'metadata'):root_sections(fixture(),(30,1))
        d=document();d['source']['nodes'][ROOT+':MovieScene']['fields']['TickResolution']['complete']=False
        with self.assertRaisesRegex(ValueError,'incomplete'):root_sections(d,(30,1))
        for rate in ((True,1),(30,0),(-30,1)):
            with self.assertRaises(ValueError):root_sections(document(),rate)
    def test_unbounded_root_section_has_no_fabricated_endpoint(self):
        d=document();bounds=d['source']['nodes'][SECTION]['fields']['SectionRange']['frame_range']
        bounds['lower']=dict(kind='open',value=None)
        self.assertEqual(root_sections(d,(30,1)),())


if __name__=='__main__':unittest.main()
