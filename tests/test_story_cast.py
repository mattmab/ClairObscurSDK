import unittest
from unittest.mock import Mock,patch
from types import SimpleNamespace as N
from expedition33.story_cast import matches_profile,AuthoredDialogueCast


def values(**items):
    fields={(0,name):value for name,value in items.items()}
    return N(values=fields,types={key:'Observed' for key in fields},errors={})


class CastResolutionReadsTests(unittest.TestCase):
    def setUp(self):
        self.pawn=N(index=1,serial=2,address=100)
        self.component=N(index=2,serial=3,address=200,class_index=70,outer_index=1,outer_serial=2)
        self.mesh=N(index=3,serial=4,address=300)
        self.controller=(10,11,1000);self.pawn_id=(1,2,100)
        self.stage=AuthoredDialogueCast(N(pid=7),'gustave');self.stage.borrowed_actor=self.pawn_id
        self.standin=N(visual=N(identity=(4,5,400)))
        self.catalog=N(classes={70:N(name='SkeletalMeshComponent')},ancestors=lambda index:(70,),
                       path_name=lambda mesh:'/Game/Noah/SK_Gustave.SK_Gustave')
        self.anchor=self.enterContext(patch('expedition33.cinematics.controller_anchor.for_scope',
            return_value=N(context=lambda:dict(controller=(7,*self.controller)))))
        self.responses=[(self.catalog,{10:values(Pawn=self.pawn),1:values(Body=self.component,Mesh=None)}),
                        (self.catalog,{2:values(SkeletalMesh=self.mesh)})]
        self.read=self.enterContext(patch('expedition33.values.capture_selected_values',side_effect=self.responses))

    def test_selected_borrowed_actor_shares_fresh_body_discovery_with_controller_read(self):
        self.assertFalse(self.stage.resolve(self.standin))
        self.assertEqual(self.read.call_count,2)
        self.assertEqual(self.read.call_args_list[0].args[1],(self.controller,self.pawn_id))
        self.assertEqual(self.read.call_args_list[0].kwargs['fields'],('Pawn','Body','Mesh'))
        self.assertEqual(self.read.call_args_list[1].args[1],((2,3,200),))
        self.assertEqual(self.stage.actor,self.pawn_id)

    def test_original_player_shortcut_revalidates_possession_and_current_mesh(self):
        self.assertTrue(self.stage.resolve_player())
        self.assertEqual(self.read.call_count,2)
        self.assertEqual(self.stage.actor,self.pawn_id);self.assertIsNone(self.stage.standin)
        self.assertFalse(self.stage.replacement)

    def test_cosmetic_mismatch_cannot_take_original_player_shortcut(self):
        self.catalog.path_name=lambda mesh:'/Game/Sophie/SK_Sophie.SK_Sophie'
        self.assertFalse(self.stage.resolve_player());self.assertTrue(self.stage.replacement)
        self.assertIsNone(self.stage.standin);self.assertEqual(self.read.call_count,2)

    def test_borrowed_companion_cannot_take_original_player_shortcut(self):
        other=N(index=8,serial=9,address=800)
        other_body=N(index=9,serial=10,address=900,class_index=70,outer_index=8,outer_serial=9)
        self.read.side_effect=[(self.catalog,{10:values(Pawn=other),1:values(Body=self.component,Mesh=None)}),
            (self.catalog,{8:values(Body=other_body,Mesh=None)}),
            (self.catalog,{9:values(SkeletalMesh=self.mesh)})]
        self.assertFalse(self.stage.resolve_player())
        self.assertEqual(self.stage.pawn,(8,9,800));self.assertEqual(self.stage.actor,self.pawn_id)
        self.assertEqual(self.read.call_count,3)

    def test_unresolved_or_active_role_never_shortcuts(self):
        self.stage.borrowed_actor=None
        self.assertFalse(self.stage.resolve_player());self.read.assert_not_called()
        self.stage.borrowed_actor=self.pawn_id;self.stage.saved=self.pawn_id
        with self.assertRaisesRegex(RuntimeError,'active authored scene'):self.stage.resolve_player()
        self.read.assert_not_called()

    def test_cosmetic_change_still_reads_current_mesh_and_recomputes_replacement(self):
        self.catalog.path_name=lambda mesh:'/Game/Sophie/SK_Sophie.SK_Sophie'
        self.assertTrue(self.stage.resolve(self.standin))
        self.assertEqual(self.read.call_count,2)

    def test_switched_pawn_never_uses_borrowed_actor_body_as_selected_body(self):
        other=N(index=8,serial=9,address=800)
        other_body=N(index=9,serial=10,address=900,class_index=70,outer_index=8,outer_serial=9)
        self.read.side_effect=[(self.catalog,{10:values(Pawn=other),1:values(Body=self.component,Mesh=None)}),
            (self.catalog,{8:values(Body=other_body,Mesh=None)}),
            (self.catalog,{9:values(SkeletalMesh=self.mesh)})]
        self.stage.resolve(self.standin)
        self.assertEqual(self.read.call_count,3)
        self.assertEqual(self.read.call_args_list[1].args[1],((8,9,800),))
        self.assertEqual(self.stage.pawn,(8,9,800))

    def test_nonborrowed_fallback_preserves_original_fresh_discovery(self):
        self.stage.borrowed_actor=None
        self.read.side_effect=[(self.catalog,{10:values(Pawn=self.pawn)}),
            (self.catalog,{1:values(Body=self.component,Mesh=None)}),self.responses[1]]
        self.stage.resolve(self.standin)
        self.assertEqual(self.read.call_count,3)
        self.assertEqual(self.read.call_args_list[0].kwargs['fields'],('Pawn',))

    def test_batched_body_from_another_actor_rejects_without_mesh_or_native_calls(self):
        self.component.outer_serial=99
        with self.assertRaisesRegex(ValueError,'not owned by its actor'):self.stage.resolve(self.standin)
        self.assertEqual(self.read.call_count,1)
        self.assertIsNone(self.stage.pawn)

class AuthoredCastTests(unittest.TestCase):
    def test_cosmetic_aliases_do_not_make_sophie_the_authored_gustave(self):
        self.assertTrue(matches_profile('/Game/Characters/Heros/Noah/Lumiere_Intro/SK_Gustave_Lumiere_Intro.SK_Gustave_Lumiere_Intro','gustave'))
        self.assertTrue(matches_profile('/Game/SDK/alias.SK_Gustave_CustomSkin01','gustave'))
        self.assertFalse(matches_profile('/Game/SDK/alias.SK_Sophie_Outfit06','gustave'))
        self.assertFalse(matches_profile('/Game/Characters/Heros/Sophie/SK_Sophie.SK_Sophie','gustave'))

    def test_matching_player_positions_camera_carrier_without_hiding_pawn(self):
        stage=AuthoredDialogueCast(N(pid=1),'gustave');stage.pawn=(1,2,0x10000);stage.replacement=False;stage.standin=Mock()
        catalog=Mock();root=N(index=2,serial=3,address=0x20000);capsule=N(index=3,serial=4,address=0x30000)
        location=N(fields=dict(X=10.,Y=20.,Z=188.));rotation=N(fields=dict(Yaw=90.))
        with patch('expedition33.values.capture_selected_values',side_effect=[(catalog,{1:'pawn'}),(catalog,{2:'root',3:'capsule'})]) as read,patch('expedition33.story_cast.field',side_effect=[False,root,capsule,None,location,rotation,88.]):
            stage.begin()
        stage.standin.move.assert_called_once_with([10.,20.,100.],90.,visual=False)
        self.assertEqual(read.call_count,2)
        self.assertIsNone(stage.saved)

    def test_retired_world_releases_local_stage_without_restoring_old_pawn(self):
        stage=AuthoredDialogueCast(N(),'gustave');stage.saved=(1,2,3);stage.restore=Mock();stage.planner=Mock()
        self.assertTrue(stage.close(world_retired=True))
        self.assertIsNone(stage.saved);self.assertIsNone(stage.planner)


    def test_dialogue_preserves_selected_pawn_when_primary_role_is_elsewhere(self):
        stage=AuthoredDialogueCast(N(pid=1),'gustave');stage.pawn=(1,2,0x10000)
        stage.borrowed_actor=(9,10,0x20000);stage.replacement=True;stage.preserve_player=True;stage.standin=Mock()
        catalog=Mock();root=N(index=2,serial=3,address=0x20000);capsule=N(index=3,serial=4,address=0x30000)
        location=N(fields=dict(X=10.,Y=20.,Z=188.));rotation=N(fields=dict(Yaw=90.))
        with patch('expedition33.values.capture_selected_values',side_effect=[(catalog,{9:'pawn'}),(catalog,{2:'root',3:'capsule'})]),patch('expedition33.story_cast.field',side_effect=[False,root,capsule,None,location,rotation,88.]):
            stage.begin()
        stage.standin.move.assert_called_once_with([10.,20.,100.],90.,visual=False)
        self.assertIsNone(stage.saved)
        self.assertIsNone(stage.planner)

    def test_owned_replacement_still_moves_visual_and_shared_root_is_deduplicated(self):
        stage=AuthoredDialogueCast(N(pid=1),'gustave');stage.pawn=(1,2,0x10000)
        stage.replacement=True;stage.preserve_player=True;stage.standin=Mock()
        root=N(index=2,serial=3,address=0x20000)
        location=N(fields=dict(X=10.,Y=20.,Z=188.));rotation=N(fields=dict(Yaw=90.))
        with patch('expedition33.values.capture_selected_values',side_effect=[(None,{1:'pawn'}),(None,{2:'root'})]) as read,patch('expedition33.story_cast.field',side_effect=[False,root,root,None,location,rotation,88.]):
            stage.begin()
        self.assertEqual(read.call_args.args[1],((2,3,0x20000),))
        stage.standin.move.assert_called_once_with([10.,20.,100.],90.,visual=True)
        self.assertIsNone(stage.saved)

    def test_attached_pawn_does_not_move_any_cast(self):
        stage=AuthoredDialogueCast(N(pid=1),'gustave');stage.pawn=(1,2,0x10000);stage.standin=Mock()
        root=N(index=2,serial=3,address=0x20000)
        with patch('expedition33.values.capture_selected_values',side_effect=[(None,{1:'pawn'}),(None,{2:'root'})]),patch('expedition33.story_cast.field',side_effect=[False,root,root,object()]):
            with self.assertRaisesRegex(RuntimeError,'Finish traversal'):stage.begin()
        stage.standin.move.assert_not_called()

    def test_direct_player_still_rejects_traversal_without_private_carrier(self):
        stage=AuthoredDialogueCast(N(pid=1),'gustave');stage.pawn=(1,2,0x10000)
        stage.actor=stage.pawn;stage.borrowed_actor=stage.pawn
        root=N(index=2,serial=3,address=0x20000);capsule=N(index=3,serial=4,address=0x30000)
        with patch('expedition33.values.capture_selected_values',side_effect=[(None,{1:'pawn'}),(None,{2:'root'})]) as read, \
                patch('expedition33.story_cast.field',side_effect=[False,root,capsule,object()]):
            with self.assertRaisesRegex(RuntimeError,'Finish traversal'):stage.begin()
        self.assertEqual(read.call_count,2);self.assertIsNone(stage.saved);self.assertIsNone(stage.planner)
