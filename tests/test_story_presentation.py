import unittest
from types import SimpleNamespace as N
from contextlib import nullcontext
from unittest.mock import Mock,patch
from expedition33.story_presentation import _body,_configure_faceless_boy_npc,verify_faceless_boy_npc,FACELESS_SCALE,FACELESS_IDLE

def obj(index,**kw):
    return N(index=index,serial=1001+index,address=0x10000+16*index,**kw)

def values(**kw):
    return N(values={(1,k):v for k,v in kw.items()},errors={},truncated=())

class PresentationPreparationTests(unittest.TestCase):
    def test_body_read_checks_exact_actor_membership_and_complete_observation(self):
        actor=(1,1002,0x10010);body=obj(2,outer_index=1,outer_serial=1002,class_index=9)
        catalog=N(classes={9:N(name='SkeletalMeshComponent')},ancestors=lambda _: (9,))
        row=values(Body=body)
        with patch('expedition33.values.capture_selected_values',return_value=(catalog,{1:row})) as capture:
            self.assertIs(_body(N(pid=7),actor)[1],body)
            capture.assert_called_once_with(7,(actor,),fields=('Body',),references=True)
            body.outer_serial+=1
            with self.assertRaisesRegex(ValueError,'not owned'):_body(N(pid=7),actor)
            row.truncated=('Body',)
            with self.assertRaisesRegex(RuntimeError,'incomplete'):_body(N(pid=7),actor)

    def test_warm_scale_and_idle_share_metadata_but_preserve_dispatch_and_verification(self):
        body=obj(2);clip=obj(3,class_name='AnimSequence')
        catalog=N(find_path=lambda path:path,with_observations=lambda _:catalog)
        planner=Mock();planner.__enter__=Mock(return_value=planner);planner.__exit__=Mock(return_value=False)
        planner._catalog=catalog
        calls=[Mock(),Mock()]
        for call in calls:call.invoke.side_effect=lambda:nullcontext(None)
        planner.prepare.side_effect=calls
        warm=N(paths={'/Script/Engine.SkeletalMeshComponent:PlayAnimation','/Script/Engine.SceneComponent:SetRelativeScale3D'},planner=Mock(return_value=planner))
        construction=N(resources=N(load=Mock(return_value=clip)),catalog=Mock(return_value=catalog))
        scope=N(pid=7,_check=Mock(),_session=N(_story_construction_resources=construction,_story_performance_preflight=warm),invocation_planner=Mock())
        visual=N(profile='faceless-boy',state='prepared',identity=(1,1002,0x10010),scope=scope)
        with patch('expedition33.story_presentation._body',return_value=(catalog,body)),patch('expedition33.story_presentation.verify_faceless_boy_npc',return_value='verified') as verify:
            self.assertEqual(_configure_faceless_boy_npc(visual),'verified')
        warm.planner.assert_called_once_with(scope,body,'/Script/Engine.SkeletalMeshComponent:PlayAnimation',dict(NewAnimToPlay=clip,bLooping=True))
        scope.invocation_planner.assert_not_called()
        self.assertEqual(planner.prepare.call_count,2)
        for call in calls:call.invoke.assert_called_once()
        verify.assert_called_once_with(visual)
        with self.assertRaisesRegex(RuntimeError,'one-shot'):_configure_faceless_boy_npc(visual)

    def test_readback_requires_current_animation_asset_and_source_scale(self):
        body=obj(2);instance=obj(3,class_name='AnimSingleNodeInstance');clip=obj(4)
        catalog=N(path_name=lambda _:FACELESS_IDLE)
        first=values(RelativeScale3D=N(fields=dict(zip('XYZ',FACELESS_SCALE))),AnimationMode=1,AnimScriptInstance=instance)
        final=values(CurrentAsset=clip)
        visual=N(scope=N(pid=7),identity=(1,1002,0x10010))
        with patch('expedition33.story_presentation._body',return_value=(catalog,body)),patch('expedition33.values.capture_selected_values',side_effect=((catalog,{2:first}),(catalog,{3:final}))) as read:
            verify_faceless_boy_npc(visual)
        self.assertEqual(read.call_count,2);self.assertTrue(visual._npc_presentation_ready)
        del visual._npc_presentation_ready
        final.errors={'CurrentAsset':'changed'}
        with patch('expedition33.story_presentation._body',return_value=(catalog,body)),patch('expedition33.values.capture_selected_values',side_effect=((catalog,{2:first}),(catalog,{3:final}))):
            with self.assertRaisesRegex(RuntimeError,'idle differs'):verify_faceless_boy_npc(visual)
        self.assertFalse(hasattr(visual,'_npc_presentation_ready'))

if __name__=='__main__':unittest.main()
