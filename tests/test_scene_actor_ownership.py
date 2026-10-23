import unittest
from test_runtime_scene_editor import package
from scene_editor_tests.palette import animation_owner,ANIMATIONS,BODY_SKELETON


class ActorOwnershipTests(unittest.TestCase):
    def test_cinematic_scene_folder_does_not_own_all_cast_tracks(self):
        cases={
            '/Game/Cinematics/Simon/SimonIntro/Animation/SimonIntro_Lune_01_UE5.SimonIntro_Lune_01_UE5':'Lune',
            '/Game/Cinematics/ThePaintress/Animation/PaintressTransitionToPhase3_Maelle_01_UE5.PaintressTransitionToPhase3_Maelle_01_UE5':'Maelle',
            '/Game/Cinematics/CleasTower/Animation/CleaAlphaFinisher_Sciel_01.CleaAlphaFinisher_Sciel_01':'Sciel',
            '/Game/Cinematics/AncientSanctuary/Animation/TheGestralDidAMassacre_Gustave_02_dataclean_UE5.TheGestralDidAMassacre_Gustave_02_dataclean_UE5':'Gustave',
        }
        for path,owner in cases.items():
            with self.subTest(path=path):self.assertEqual(animation_owner(path),owner)

    def test_explicit_identity_aliases_and_ambiguous_tracks(self):
        for token,owner in (('Noah','Gustave'),('GiantPaintress','Paintress'),('SimonStandIn','Simon')):
            self.assertEqual(animation_owner('/Game/Cinematics/Test/Test_'+token+'_01.Test_'+token+'_01'),owner)
        self.assertIsNone(animation_owner('/Game/Cinematics/Clea/Test_CleaAlicia_01.Test_CleaAlicia_01'))
        self.assertIsNone(animation_owner('/Game/Cinematics/Simon/Test_Lune_Maelle_01.Test_Lune_Maelle_01'))
        self.assertIsNone(animation_owner('/Game/Cinematics/Clea/Test_dataclean_01.Test_dataclean_01'))

    def test_trusted_character_folders_and_exception(self):
        self.assertEqual(animation_owner('/Game/Characters/Enemies/HumanEnnemies/Aline/Animation/Paintress_Skill7_MaelleBurningCanvasVersion.Paintress_Skill7_MaelleBurningCanvasVersion'),'Paintress')
        self.assertEqual(animation_owner('/Game/Characters/Enemies/HumanEnnemies/Clea_v1/Animations/Mocap/Clea_Idle_02.Clea_Idle_02'),'Clea')
        self.assertEqual(animation_owner('/Game/Characters/Heros/Lune/Animations/BattleTurn/Paintress_Idle_FinalSequence.Paintress_Idle_FinalSequence'),'Paintress')

    def test_sadness_three_verified_clips(self):
        clips=[row for row in ANIMATIONS.values() if animation_owner(row['path'])=='Sadness mask']
        self.assertEqual(len(clips),3)
        self.assertTrue(all(row['skeleton']=='/Game/Animations/EmptySkeleton.EmptySkeleton' for row in clips))

    def test_raw_actor_role_ownership_uses_asset_identity(self):
        from scene_editor_tests.palette import CHARACTERS,actor_animation_owner
        cases={'mesh-530d4c6218bf':'Sadness mask','mesh-c26dc496d5c6':'Paintress','mesh-6505d90b9042':'Gustave','mesh-6e00723ff928':'Clea','mesh-d875adaa10b1':'Simon'}
        for role,owner in cases.items():
            with self.subTest(role=role):
                self.assertIn(role,CHARACTERS)
                self.assertEqual(actor_animation_owner(role),owner)

    def test_verified_body_sets_have_expected_conservative_counts(self):
        owners={owner:sum(row['skeleton']==BODY_SKELETON and animation_owner(row['path'])==owner for row in ANIMATIONS.values()) for owner in ('Paintress','Simon','Clea')}
        self.assertEqual(owners,{'Paintress':40,'Simon':20,'Clea':3})


class PromotedActorAssemblyTests(unittest.TestCase):
    def checked_actor(self,role,owner):
        from scene_editor_tests.palette import CHARACTERS,library_roles,animation_choices
        row=CHARACTERS[role]
        self.assertIn(role,library_roles())
        self.assertTrue(row['main_actor'])
        clip=ANIMATIONS[row['default_animation']]
        self.assertEqual(clip['skeleton'],row['skeleton'])
        self.assertEqual(animation_owner(clip['path']),owner)
        self.assertIn(row['default_animation'],animation_choices(role,row['skeleton']))
        return row

    def test_sadness_scale_and_three_own_clips(self):
        from scene_editor_tests.palette import animation_choices
        row=self.checked_actor('mesh-530d4c6218bf','Sadness mask')
        self.assertEqual(row['spawn_scale'],1.5)
        self.assertEqual(len(animation_choices(row['id'],row['skeleton'])),3)
        self.assertEqual(row['parts'][0]['mode'],0)

    def test_paintress_owns_head_attached_independent_hair(self):
        row=self.checked_actor('mesh-3bcd02b8bbf3','Paintress')
        self.assertEqual(row['parts'][0]['mode'],0)
        self.assertEqual((row['parts'][2]['mode'],row['parts'][2]['socket']),(3,'Head'))
        self.assertTrue(row['parts'][2]['path'])

    def test_gustave_has_face_leader_and_head_hair(self):
        row=self.checked_actor('mesh-a44413d5b7d7','Gustave')
        self.assertEqual(row['parts'][1]['mode'],1)
        self.assertIn('/MetaHumans/Gustave/',row['parts'][1]['path'])
        self.assertEqual((row['parts'][2]['mode'],row['parts'][2]['socket']),(2,'Head'))
        self.assertIn('/Hair/Heroes/Gustave/',row['parts'][2]['path'])

    def test_clea_uses_body_leader_for_face_and_hair(self):
        row=self.checked_actor('mesh-ec219a8fbdab','Clea')
        self.assertTrue(row['parts'][1]['path'])
        self.assertTrue(row['parts'][2]['path'])
        self.assertEqual([part['mode'] for part in row['parts'][:3]],[0,1,1])

    def test_simon_owns_head_attached_independent_hair(self):
        row=self.checked_actor('mesh-d875adaa10b1','Simon')
        self.assertEqual(row['parts'][0]['mode'],0)
        self.assertEqual((row['parts'][2]['mode'],row['parts'][2]['socket']),(3,'Head'))
        self.assertIn('/Hair/NPCs/Simon/',row['parts'][2]['path'])


class HistoricalActorAssemblyMigrationTests(unittest.TestCase):
    def legacy_scene(self,role):
        import copy
        from test_runtime_scene_editor import WORLD
        from scene_editor_tests.scene import blank,ACTOR_TEMPLATES,ASSETS
        data=blank(WORLD)
        actor=copy.deepcopy(ACTOR_TEMPLATES[role])
        actor['id']='custom-actor'
        actor['transform']={'position':[12,34,56],'rotation':[10,20,30],'scale':[.5]*3}
        data['actors']=[actor]
        data['assemblies'][role]={'body':role+'_body','recipe':'scene-palette-v15'}
        data['assets'][role+'_body']=ASSETS[role+'_body']
        return data

    def test_exact_historical_body_recipes_upgrade_and_preserve_actor(self):
        import copy
        from scene_editor_tests.scene import validate,ASSEMBLIES,_LEGACY_BODY_ASSEMBLIES
        for role in _LEGACY_BODY_ASSEMBLIES:
            with self.subTest(role=role):
                data=self.legacy_scene(role);actor=copy.deepcopy(data['actors'][0])
                upgraded=validate(data)
                self.assertEqual(upgraded['actors'],[actor])
                self.assertEqual(upgraded['assemblies'][role],ASSEMBLIES[role])
                self.assertEqual(data['assemblies'][role],{'body':role+'_body','recipe':'scene-palette-v15'})

    def test_altered_body_or_extra_legacy_fields_are_rejected(self):
        from scene_editor_tests.scene import validate
        role='mesh-d875adaa10b1'
        for mutation in ('wrong-body','extra-field','changed-path','missing-body'):
            with self.subTest(mutation=mutation):
                data=self.legacy_scene(role)
                if mutation=='wrong-body':data['assemblies'][role]['body']='lune_body'
                elif mutation=='extra-field':data['assemblies'][role]['hair']='lune_hair'
                elif mutation=='changed-path':data['assets'][role+'_body']='/Game/Wrong.Wrong'
                else:del data['assets'][role+'_body']
                with self.assertRaises(ValueError):validate(data)


if __name__=='__main__':unittest.main()
