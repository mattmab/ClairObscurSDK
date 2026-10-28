import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.authored_copy import duplicate,display_frames,signature,apply_section_edits,_select_reachable_sections


class AuthoredCopyTests(unittest.TestCase):
    def test_duplicate_signature_selects_only_the_referenced_copy(self):
        a,b=N(index=1),N(index=2)
        catalog=Mock();catalog.path_name.side_effect=lambda obj:'/private/'+str(obj.index)
        with patch('expedition33.cinematics.authored_references.reachable_sections',return_value={2}):
            self.assertEqual(_select_reachable_sections(Mock(),Mock(),catalog,{'source':[a,b]}),{'source':b})
        for reachable in ({1,2},set()):
            with patch('expedition33.cinematics.authored_references.reachable_sections',return_value=reachable):
                with self.assertRaises(RuntimeError):_select_reachable_sections(Mock(),Mock(),catalog,{'source':[a,b]})

    def test_off_grid_range_uses_tick_rate_then_restores_private_display_rate(self):
        root=N(index=1,serial=1,address=0x10000,class_name='LevelSequence')
        outer=N(index=2,serial=1,address=0x20000,class_name='Object')
        section=N(index=3,serial=1,address=0x30000,name='Section_0',class_name='MovieSceneCinematicShotSection')
        original=N(index=4,name='Section_0',class_name=section.class_name)
        scene=N(index=5);path='/Game/Source.Source:MovieScene.Section_0'
        sig={'struct':'/Script/CoreUObject.Guid','fields':dict(A=1,B=2,C=3,D=4),'complete':True,'errors':{}}
        def bounds(start):return {'frame_range':{'lower':{'kind':'inclusive','value':start},'upper':{'kind':'exclusive','value':1600}}}
        before=bounds(0);after=bounds(1);tick=dict(Numerator=24000,Denominator=1);display=dict(Numerator=30,Denominator=1)
        document=dict(section_edits={path:dict(start=1,end=1600)},source=dict(nodes={path:dict(class_name=section.class_name,fields=dict(Signature=sig,SectionRange=before))}))
        catalog=Mock();catalog.objects=(section,original);catalog.with_observations.return_value=catalog
        catalog.outer_chain.side_effect=lambda obj: (root,outer) if obj is section else (outer,) if obj is root else ()
        catalog.find_path.side_effect=lambda name: original if name==path else name
        planner=Mock();invocations=[]
        def prepare(target,function,**arguments):
            invocations.append((function,arguments))
            return N(invoke=lambda:nullcontext())
        planner.prepare.side_effect=prepare
        scope=Mock();scope.pid=99;scope.invocation_planner.return_value=planner;scope._session._transport.sequencer_frame_values_protocol=1
        def read(c,obj,fields):
            if fields==('Signature',):result={'Signature':sig}
            elif fields==('SectionRange',):result={'SectionRange':after if obj is section and invocations else before}
            elif fields==('MovieScene',):result={'MovieScene':scene}
            elif fields==('TickResolution','DisplayRate'):result={'TickResolution':N(fields=tick),'DisplayRate':N(fields=display)}
            else:result={'DisplayRate':N(fields=display)}
            return N(errors={},truncated=(),values={(obj.index,k):v for k,v in result.items()}),catalog
        with patch('expedition33.cinematics.authored_copy.shared_operation',return_value=nullcontext()),\
             patch('expedition33.cinematics.authored_copy.authored_timeline.validate',return_value=document),\
             patch('expedition33.cinematics.authored_copy.capture_matching',return_value=catalog),\
             patch('expedition33.cinematics.authored_copy.capture_selected'),\
             patch('expedition33.cinematics.authored_copy.read_values_with_references',side_effect=read),\
             patch('expedition33.cinematics.authored_copy.copied',side_effect=lambda v,c:v):
            self.assertEqual(apply_section_edits(scope,root,outer,document),{path:after['frame_range']})
        self.assertEqual([f.rsplit(':',1)[1] for f,a in invocations],['SetDisplayRate','SetRange','SetDisplayRate'])
        self.assertEqual(invocations[0][1]['DisplayRate'],tick)
        self.assertEqual(invocations[1][1],dict(Section=section,StartFrame=1,EndFrame=1600))
        self.assertEqual(invocations[2][1]['DisplayRate'],display)
    def test_tick_to_display_conversion_is_exact_and_never_rounds(self):
        tick={'Numerator':24000,'Denominator':1};display={'Numerator':30,'Denominator':1}
        self.assertEqual(display_frames({'start':75200,'end':1739200},tick,display),(94,2174))
        self.assertEqual(display_frames({'start':-800,'end':800},tick,display),(-1,1))
        with self.assertRaisesRegex(ValueError,'between display frames'):
            display_frames({'start':75201,'end':1739200},tick,display)
        ntsc={'Numerator':30000,'Denominator':1001}
        self.assertEqual(display_frames({'start':800800,'end':1601600},tick,ntsc),(1000,2000))
    def test_complete_nonzero_guid_signature_is_required(self):
        guid={'struct':'/Script/CoreUObject.Guid','fields':dict(A=1,B=2,C=3,D=4),'complete':True,'errors':{}}
        self.assertEqual(signature({'fields':{'Signature':guid}}),(1,2,3,4))
        for bad in ({},dict(guid,complete=False),dict(guid,errors={'A':'unread'}),dict(guid,fields=dict(A=0,B=0,C=0,D=0))):
            with self.assertRaises(ValueError):signature({'fields':{'Signature':bad}})
    def run_copy(self,*,copy=None,source_scene=None,copy_scene=None):
        source=N(index=1,serial=2,address=0x10000,class_name='LevelSequence')
        outer=N(index=2,serial=3,address=0x20000)
        copy=copy or N(index=3,serial=4,address=0x30000,class_name='LevelSequence',outer_index=2,outer_serial=3)
        source_scene=source_scene or N(index=4,class_name='MovieScene',outer_index=1,outer_serial=2)
        copy_scene=copy_scene or N(index=5,class_name='MovieScene',outer_index=copy.index,outer_serial=copy.serial)
        catalog=Mock();catalog.with_observations.return_value=catalog
        planner=Mock();planner._catalog=catalog;planner.prepare.return_value.invoke.return_value=N(return_value=copy)
        scope=Mock();scope.pid=42;scope.invocation_planner.return_value=planner
        reads=[(N(values={(obj.index,'MovieScene'):scene},errors={}),catalog)
               for obj,scene in ((source,source_scene),(copy,copy_scene))]
        with patch('expedition33.cinematics.authored_copy.shared_operation',return_value=nullcontext()),\
             patch('expedition33.cinematics.authored_copy.load_asset',return_value=N(return_value=source)),\
             patch('expedition33.cinematics.authored_copy.capture_matching',return_value=catalog),\
             patch('expedition33.cinematics.authored_copy.capture_selected'),\
             patch('expedition33.cinematics.authored_copy.read_values_with_references',side_effect=reads):
            result=duplicate(scope,'/Game/Source.Source',outer)
        return result,planner

    def test_engine_copy_retains_result_and_requires_distinct_owned_movie_scene(self):
        result,planner=self.run_copy()
        self.assertEqual(result.index,3)
        self.assertEqual(planner.prepare.call_count,1)
        self.assertEqual(planner.prepare.call_args.kwargs['InSequence'].index,1)
        planner.prepare.return_value.invoke.assert_called_once_with(refresh_from_result=True)

    def test_original_or_foreign_outer_is_never_accepted(self):
        for index,outer in ((1,2),(3,99)):
            copy=N(index=index,serial=4,address=0x30000,class_name='LevelSequence',outer_index=outer,outer_serial=3)
            with self.assertRaisesRegex(RuntimeError,'private LevelSequence'):self.run_copy(copy=copy)

    def test_shared_or_foreign_movie_scene_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'still shares'):
            self.run_copy(source_scene=N(index=5,class_name='MovieScene',outer_index=1,outer_serial=2))
        with self.assertRaisesRegex(RuntimeError,'not owned'):
            self.run_copy(copy_scene=N(index=5,class_name='MovieScene',outer_index=1,outer_serial=2))
