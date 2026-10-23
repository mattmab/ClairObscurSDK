import tempfile,unittest,json
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
from test_runtime_scene_editor import package,WORLD,ROOT
from scene_editor_tests.scene import blank,validate,encode,SceneStore
from scene_editor_tests.view import SceneView

class DashboardTests(unittest.TestCase):
    def test_blank_is_valid_and_keeps_sample_separate(self):
        data=blank(WORLD)
        self.assertEqual(data['actors'],[])
        self.assertEqual([e['id'] for e in data['events']],['camera-orbit'])
        self.assertEqual(data['duration'],20)
        self.assertEqual(validate(data),data)
        self.assertTrue(encode(data))

    def test_dashboard_has_eight_short_actions_and_single_summary(self):
        model=package.Mod();model.document=blank(WORLD);model.dirty=True
        view=SceneView(None,model);title,details,rows=view._rows()
        self.assertEqual(len(rows),9)
        self.assertTrue(all(len(r[0])<=24 for r in rows))
        self.assertIn('Unsaved changes',details)
        self.assertNotIn('/Game/',details)
        self.assertNotIn(model.message,details)

    def test_tiny_actor_size_roundtrip_and_quick_controls(self):
        from scene_editor_tests.scene import sample,SceneStore
        model=package.Mod();model.document=sample(WORLD)
        model.edit('pose:lune:scale:0',.002)
        self.assertEqual(validate(model.document)['actors'][0]['transform']['scale'],[.002]*3)
        from expedition33._runtime_scene_wire import validate_request
        import struct
        payload=encode(model.document);packet=bytearray(20984)
        struct.pack_into('<4IQ',packet,0,7,74,0,0,1);packet[88:88+len(payload)]=payload
        validate_request(bytes(packet),protocol=7)
        with tempfile.TemporaryDirectory() as directory:
            model.store=SceneStore(directory);key=model.save();model.load(key)
            self.assertEqual(model.actor('lune')['transform']['scale'],[.002]*3)
        view=SceneView(None,model);view.screen='scene_actor'
        rows=view._rows()[2]
        self.assertTrue(rows[0][0].startswith('Size:'))
        self.assertIn('Half size',[row[0] for row in rows])
        with self.assertRaises(ValueError):model.edit('pose:lune:scale:0',.0001)

    def test_saved_scene_summary_search_and_explicit_load(self):
        with tempfile.TemporaryDirectory() as directory:
            model=package.Mod();model.store=SceneStore(Path(directory));data=blank(WORLD)
            data['name']='Opening shot';key=model.store.save(data)
            view=SceneView(None,model);view.screen='scene_saved'
            rows=view._rows()[2];self.assertFalse(rows[0][3])
            self.assertEqual(rows[-1][1],'scene_saved_select')
            view.saved_id=key;details=view._rows()[1];rows=view._rows()[2]
            self.assertTrue(rows[0][3]);self.assertIn('20s | 0 characters',details)
            self.assertIn('0 animation clips | 0 audio clips',details)
            self.assertIsNone(model.document)
            view.query='missing';self.assertEqual(len(view._rows()[2]),3)

    def test_new_scene_marks_dirty_and_preserves_saved_file(self):
        model=package.Mod();model.session=object()
        with patch.object(package,'controller_context',return_value={'world_path':WORLD}):model.new_scene()
        self.assertTrue(model.dirty);self.assertIsNone(model.key)
        self.assertEqual(model.document['name'],'Untitled scene')

    def test_shortening_blank_scene_and_protecting_user_content(self):
        model=package.Mod();model.document=blank(WORLD)
        model.edit('duration',5)
        self.assertEqual(model.document['duration'],5)
        self.assertEqual(model.document['events'][0]['params']['end'],5)
        model.document['camera_keys']=[dict(id='camera-123456abcdef',at=4,position=[0,0,0],rotation=[0,0,0],fov=90)]
        before=model.document
        with self.assertRaisesRegex(ValueError,'reach 4s'):model.edit('duration',3)
        self.assertIs(model.document,before)
        self.assertEqual(model.document['duration'],5)

class SavedCardTests(unittest.TestCase):
    def test_cards_show_metadata_and_load_only_when_requested(self):
        from scene_editor_tests.view import SavedSceneView
        rows=[dict(id='a'*32,name='Opening',duration=12,actors=2,animations=3,audio=4,camera_keys=2,target_map=WORLD)]
        calls=[];model=SimpleNamespace(store=SimpleNamespace(list=lambda:rows),load=lambda key:calls.append(key),want_open=False)
        view=SavedSceneView(None,model);frame=view.render()
        self.assertIn('12s | 2 characters',frame.controls[0].label);self.assertFalse(frame.controls[8].enabled)
        frame=view.activate(frame.revision,0);self.assertFalse(calls);self.assertIn('Camera keys: 2 / 16',frame.description)
        self.assertTrue(frame.controls[8].enabled)
        frame=view.activate(frame.revision,8);self.assertEqual(calls,['a'*32]);self.assertTrue(frame.closed);self.assertTrue(model.want_open)

    def test_card_search_pagination_and_stale_commands(self):
        from scene_editor_tests.view import SavedSceneView
        from expedition33.management import ManagementError
        rows=[dict(id=str(i),name='Shot '+str(i),duration=20,actors=0,animations=0,audio=0,camera_keys=0,target_map=WORLD) for i in range(10)]
        view=SavedSceneView(None,SimpleNamespace(store=SimpleNamespace(list=lambda:rows)));frame=view.render()
        self.assertEqual(frame.pages,2);frame=view.activate(frame.revision,13);self.assertEqual(len(view.choices),2)
        frame=view.activate(frame.revision,14,value='Shot 9');self.assertEqual(len(view.choices),1);self.assertEqual(view.choices[0]['name'],'Shot 9')
        with self.assertRaises(ManagementError):view.activate(frame.revision-1,0)
        frame=view.activate(frame.revision,15);self.assertEqual(len(view.choices),8)

class SetupFlowTests(unittest.TestCase):
    def test_new_scene_opens_setup_and_length_buttons_resize_document(self):
        from test_runtime_scene_editor import Registry
        model=package.Mod();model.document=blank(WORLD);model.next_screen='scene_setup'
        view=SceneView(Registry(),model);self.assertEqual(view.screen,'scene_setup');self.assertIsNone(model.next_screen)
        frame=view.render();control=next(c for c in frame.controls if c.label=='Length +5 seconds')
        view.activate(frame.revision,control.token);self.assertEqual(model.document['duration'],25)
        frame=view.render();control=next(c for c in frame.controls if c.label=='Length -5 seconds')
        view.activate(frame.revision,control.token);self.assertEqual(model.document['duration'],20)

    def test_actor_library_inspects_before_adding_to_empty_scene(self):
        from test_runtime_scene_editor import Registry
        model=package.Mod();model.document=blank(WORLD);view=SceneView(Registry(),model);view.screen='scene_add'
        from scene_editor_tests.palette import library_label
        frame=view.render();control=next(c for c in frame.controls if c.label==library_label('lune'))
        self.assertRegex(control.label,r'^Lune \| [1-9][0-9]* animations?$')
        view.activate(frame.revision,control.token);self.assertFalse(model.document['actors']);self.assertEqual(view.screen,'scene_actor_asset')
        frame=view.render();control=next(c for c in frame.controls if c.label=='Add to scene')
        view.activate(frame.revision,control.token);self.assertEqual(len(model.document['actors']),1);self.assertEqual(model.document['actors'][0]['assembly'],'lune')

    def test_photo_prerequisite_is_visible_without_queuing_asset_load(self):
        from test_runtime_scene_editor import Registry
        model=package.Mod();model.document=blank(WORLD);view=SceneView(Registry(),model)
        with patch.object(model.runtime,'check_host',side_effect=ValueError('Open game Photo mode first')):
            frame=view.render();control=next(c for c in frame.controls if c.label=='Photo mode / timeline')
            frame=view.activate(frame.revision,control.token)
        self.assertEqual(view.screen,'scene_photo_help');self.assertFalse(model.want_author);self.assertIn('Photo mode',frame.description)
        self.assertIn('Open game Photo mode first',frame.status)

class TimelineCleanupTests(unittest.TestCase):
    def test_returned_unregister_rejection_still_disposes_ui(self):
        from scene_editor_tests.timeline import TimelineMenu
        from expedition33.management_native import NativeManagementMenu
        calls=[];runtime=SimpleNamespace(authoring=True,uncertain=False,timeline_owner=lambda *args:(_ for _ in ()).throw(RuntimeError('Scene asset adapter rejected request: 2040')))
        menu=TimelineMenu.__new__(TimelineMenu);menu.registered=True;menu.model=SimpleNamespace(runtime=runtime);menu.panel=object()
        menu.mirror=SimpleNamespace(widget=object(),_render_call=lambda *a,**k:calls.append('removed'),close_owned_tree=lambda:calls.append('disposed'))
        with patch.object(NativeManagementMenu,'close',return_value='closed') as close:self.assertEqual(menu.close(),'closed')
        close.assert_called_once();self.assertEqual(calls,['removed','disposed']);self.assertIsNone(menu.mirror);self.assertFalse(menu.registered)

class PhotoTransferTests(unittest.TestCase):
    def test_photo_button_queues_switch_and_is_disabled_in_photo_mode(self):
        from scene_editor_tests.timeline import TimelineView
        from scene_editor_tests.scene import sample
        model=SimpleNamespace(document=sample(WORLD),runtime=SimpleNamespace(authoring=True,photo_mode=False,last={}),message='',want_photo=False)
        view=TimelineView(None,model);frame=view.render();self.assertEqual(frame.controls[17].label,'Photo mode');self.assertTrue(frame.controls[17].enabled)
        view.activate(frame.revision,17);self.assertTrue(model.want_photo)
        model.runtime.photo_mode=True;frame=view.render();self.assertFalse(frame.controls[17].enabled)

    def test_transfer_saves_recovery_and_releases_flight_before_entry(self):
        from scene_editor_tests.scene import sample
        calls=[];model=package.Mod();model.document=sample(WORLD)
        runtime=SimpleNamespace(authoring=True,photo_mode=False,last={'playhead':7.5,'selected':1},camera_view=lambda:[123.,456.,789.,-12.,37.,18.,63.],scope=object(),editor_control=lambda *a:calls.append(('control',*a)),sync_document=lambda d:d,enter_photo_mode=lambda:calls.append(('enter',)))
        model.runtime=runtime;model.store=SimpleNamespace(save=lambda d:calls.append(('recovery',d)))
        def stop():calls.append(('stop',));runtime.scope=None
        model.stop=stop;model.transfer_to_photo()
        self.assertEqual(model.photo_transfer['at'],7.5);self.assertEqual(model.photo_transfer['slot'],1)
        self.assertLess(next(i for i,c in enumerate(calls) if c[0]=='stop'),next(i for i,c in enumerate(calls) if c[0]=='enter'))
        self.assertTrue(next(c[1] for c in calls if c[0]=='recovery')['name'].endswith('(before photo)'))

    def test_photo_readiness_restores_time_actor_and_exact_flight_view(self):
        from scene_editor_tests.scene import sample
        calls=[];model=package.Mod();model.document=sample(WORLD);model.photo_transfer={'at':7.5,'slot':1,'camera':[123.,456.,789.,-12.,37.,18.,63.],'next_check':0,'deadline':float('inf')}
        model.runtime=SimpleNamespace(camera_view=lambda view:calls.append(('camera',view)),check_host=lambda photo:None,seek=lambda at:calls.append(('seek',at)),editor_control=lambda *a:calls.append(('control',*a)))
        model.start_authoring=lambda:calls.append(('start',))
        model._poll_photo_transfer();self.assertTrue(model.photo_author);self.assertIsNone(model.photo_transfer)
        self.assertEqual(calls,[('start',),('seek',7.5),('control',4,1),('camera',[123.,456.,789.,-12.,37.,18.,63.])])

    def test_photo_entry_wire_accepts_only_two_identities(self):
        import struct
        from expedition33._runtime_scene_wire import validate_request
        packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,91,0,0,1)
        for at in (88,104):struct.pack_into('<iiQ',packet,at,1,1001,4096)
        validate_request(bytes(packet),protocol=7)
        packet[120]=1
        with self.assertRaises(ValueError):validate_request(bytes(packet),protocol=7)

class CameraTransferWireTests(unittest.TestCase):
    def test_camera_wire_bounds_and_read_only_payload(self):
        import struct,math
        from expedition33._runtime_scene_wire import validate_request
        def packet(action,view):
            data=bytearray(20984);struct.pack_into('<4IQ',data,0,7,92,0,0,1);struct.pack_into('<8d',data,88,action,*view);return data
        validate_request(bytes(packet(0,[0.]*7)),protocol=7)
        validate_request(bytes(packet(1,[123.,456.,789.,-12.,37.,18.,63.])),protocol=7)
        for action,view in ((0,[0.]*6+[90.]),(1,[0.]*6+[19.]),(1,[0.]*3+[361.,0.,0.,90.]),(1,[math.nan]*7),(2,[0.]*7)):
            with self.assertRaises(ValueError):validate_request(bytes(packet(action,view)),protocol=7)
        data=packet(0,[0.]*7);data[152]=1
        with self.assertRaises(ValueError):validate_request(bytes(data),protocol=7)

    def test_menu_planner_refreshes_after_native_shortcut_registration(self):
        from scene_editor_tests.timeline import TimelineMenu
        from expedition33.management_native import NativeManagementMenu
        calls=[];menu=TimelineMenu.__new__(TimelineMenu);menu.registered=False
        old=SimpleNamespace(with_observations=lambda observed:('merged',observed))
        menu.panel=SimpleNamespace(state='built',_functions={},_planner=SimpleNamespace(_catalog=old,refresh_from=lambda catalog:calls.append(('refresh',catalog))))
        menu.model=SimpleNamespace(session=SimpleNamespace(pid=123),runtime=SimpleNamespace(scope=object(),timeline_owner=lambda *args:calls.append('register')))
        with patch('expedition33.catalog.capture_matching',return_value='selected') as capture,patch.object(NativeManagementMenu,'_open',side_effect=lambda:calls.append('open')):
            menu._open();menu._open()
        capture.assert_called_once_with(123,names=('AddToViewport',))
        self.assertEqual(calls,['register',('refresh',('merged','selected')),'open','open']);self.assertTrue(menu.registered)

class LiveAnimationInsertWireTests(unittest.TestCase):
    def test_packet_rejects_bad_slot_identity_padding_and_missing_clip(self):
        import struct,copy
        from scene_editor_tests.scene import sample,encode
        from expedition33._runtime_scene_wire import validate_request
        document=sample(WORLD);document['events'].append(dict(id='useranim-abcdef012345',type='animation',target='lune',at=2.,params=dict(asset='lune_attack',speed=1.,loop=False)))
        payload=encode(document);data=bytearray(20984)
        struct.pack_into('<4IQ',data,0,7,98,0,0,1);struct.pack_into('<iiQ',data,88,12,4,4096);struct.pack_into('<I',data,104,0);data[112:112+len(payload)]=payload
        validate_request(bytes(data),protocol=7)
        for offset,value in ((104,24),(108,1),(20983,1)):
            bad=bytearray(data);bad[offset]=value
            with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=7)
        bad=bytearray(data);bad[96:104]=bytes(8)
        with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=7)

class CharacterAnimationSetTests(unittest.TestCase):
    def test_character_sets_include_samples_and_npc_clips_without_other_heroes(self):
        from scene_editor_tests.palette import animation_choices,BODY_SKELETON,ANIMATIONS,animation_owner
        for role,owner in (('lune','Lune'),('maelle','Maelle'),('monoco','Monoco'),('verso','Verso')):
            clips=animation_choices(role,BODY_SKELETON)
            self.assertTrue(clips)
            self.assertTrue(all(animation_owner(ANIMATIONS[k]['path'])==owner for k in clips))
        self.assertIn('lune_attack',animation_choices('lune',BODY_SKELETON))
        self.assertIn('clip-d32b4f61c4c2fd70',animation_choices('maelle',BODY_SKELETON))
        self.assertNotIn('clip-d32b4f61c4c2fd70',animation_choices('lune',BODY_SKELETON))

    def test_enemy_actor_uses_its_own_asset_folder_set(self):
        from scene_editor_tests.palette import animation_choices,BODY_SKELETON,clip_set
        for role,owner in (('pelerin','Swordman'),('braseleur','Braseleur'),('stalact','Stalact')):
            clips=animation_choices(role,BODY_SKELETON)
            self.assertTrue(clips);self.assertTrue(all(clip_set(k)==owner for k in clips))

    def test_face_skeleton_cannot_select_body_clips_even_from_all(self):
        from scene_editor_tests.palette import animation_choices
        self.assertEqual(animation_choices('mesh-79beacaf148b','/Game/Face.Face',None),())
        self.assertEqual(animation_choices('mesh-79beacaf148b',None,None),())

    def test_incompatible_binding_has_readable_error_and_repair_preserves_actor_and_timing(self):
        from scene_editor_tests.scene import sample,ACTOR_TEMPLATES
        from scene_editor_tests.palette import CHARACTERS
        import copy
        m=package.Mod();d=sample(WORLD);actor=copy.deepcopy(ACTOR_TEMPLATES['mesh-79beacaf148b']);actor['id']='face';actor['name']='Renamed actor'
        d['actors']=[actor];d['events']=[e for e in d['events'] if e['id']=='camera-orbit']
        d['events'].append(dict(id='anim-face',type='animation',target='face',at=1.,params=dict(asset='clip-d32b4f61c4c2fd70',speed=1.,loop=True)))
        m.document=validate(d);before=copy.deepcopy(m.document)
        m.runtime.character_skeleton=lambda role:'/Game/Face.Face'
        with self.assertRaisesRegex(ValueError,'different skeletons'):m.runtime.validate_animations(m.document)
        with self.assertRaisesRegex(ValueError,'different skeleton'):m.choose_animation('face','lune_attack')
        self.assertEqual(m.document,before)
        m.clear_incompatible_clips('face')
        self.assertEqual(m.document['actors'],before['actors']);self.assertEqual(m.document['events'][-1]['at'],1.)
        self.assertEqual(m.document['events'][-1]['params']['asset'],'bind_pose');m.runtime.validate_animations(m.document)

    def test_search_stays_in_character_set_until_all_is_explicit(self):
        from test_runtime_scene_editor import Registry
        m=package.Mod();m.document=__import__('scene_editor_tests.scene',fromlist=['sample']).sample(WORLD)
        v=SceneView(Registry(),m);v.screen='scene_animation'
        frame=v.render();search=next(c for c in frame.controls if c.label=='Search')
        v.activate(frame.revision,search.token,value='Monoco')
        from scene_editor_tests.palette import ANIMATIONS,animation_owner
        matches=[r[2] for r in v._rows()[2] if r[1]=='scene_animation' and r[2]!='bind_pose']
        self.assertTrue(matches)
        self.assertTrue(all(animation_owner(ANIMATIONS[clip]['path'])=='Lune' for clip in matches))
        frame=v.render();all_clips=next(c for c in frame.controls if c.label=='All compatible animations')
        v.activate(frame.revision,all_clips.token);self.assertIsNone(v.animation_group)

class MaskAnimationTests(unittest.TestCase):
    def test_mask_sets_are_character_specific_and_exclude_humanoid_clips(self):
        from scene_editor_tests.palette import CHARACTERS,ANIMATIONS,animation_choices,clip_set
        for name,count in (('Joy',6),('Anger',2)):
            role=next(k for k,v in CHARACTERS.items() if v['parts'][0]['path'].endswith('.Face_'+name))
            skeleton=CHARACTERS[role]['skeleton'];choices=animation_choices(role,skeleton)
            self.assertEqual(len(choices),count)
            self.assertTrue(all(clip_set(k)==name+' mask' for k in choices))
            self.assertNotIn('maelle_attack',animation_choices(role,skeleton,None))
            self.assertEqual(len(animation_choices(role,skeleton,'Shared / Masks')),2)
            self.assertEqual(animation_choices(role,None),())
            self.assertEqual(animation_choices(role,skeleton,query='Maelle'),())

    def test_existing_native_clip_slots_remain_unchanged_and_new_evidence_is_safe(self):
        from scene_editor_tests.palette import PALETTE
        self.assertEqual(len(PALETTE['clips']),2689)
        baseline=json.loads((ROOT/'evidence/scene-editor/clip-baseline-v52.json').read_text())
        self.assertEqual([(r['id'],r['path']) for r in PALETTE['clips'][:303]],[(r['id'],r['path']) for r in baseline])
        for row in PALETTE['clips'][293:303]:
            self.assertEqual(row['skeleton'],'/Game/Animations/EmptySkeleton.EmptySkeleton')
            self.assertGreater(row['length'],.1)
        evidence=json.loads((ROOT/'evidence/scene-editor/mask-animation-inspection.json').read_text(encoding='utf8'))
        for row in evidence['animations']:
            self.assertFalse(row['errors']);self.assertTrue(row['eligible'])
            self.assertEqual(row['values']['Notifies']['length'],0)
            self.assertFalse(row['values']['bEnableRootMotion'])
            self.assertEqual(row['values']['AdditiveAnimType'],0)

class ActorLibraryCurationTests(unittest.TestCase):
    def test_main_library_contains_verified_animated_actors_but_not_parts(self):
        from scene_editor_tests.palette import CHARACTERS,library_roles,animation_choices
        main=library_roles();self.assertEqual(len(main),30)
        promoted=[k for k in main if CHARACTERS[k].get('raw')];self.assertEqual(len(promoted),21)
        for role in promoted:
            row=CHARACTERS[role];self.assertIn(row['default_animation'],animation_choices(role,row['skeleton']))
        for name in ('SK_Hammer_VX','SK_Ramasseur_NevronArm_UE5','esquie_rig3','SK_Troubadour_Trumpet'):
            role=next(k for k,v in CHARACTERS.items() if v['parts'][0]['path'].endswith('.'+name))
            self.assertNotIn(role,main);self.assertIn(role,library_roles(True))
        self.assertEqual(library_roles(query='Paintress'),('mesh-3bcd02b8bbf3',))
        self.assertNotIn('mesh-c26dc496d5c6',main)
        self.assertIn('mesh-c26dc496d5c6',library_roles(True,'Paintress'))

    def test_new_animated_actor_gets_its_own_clip_and_raw_part_stays_bind_pose(self):
        from scene_editor_tests.palette import CHARACTERS,library_roles,ANIMATIONS
        from scene_editor_tests.scene import blank
        m=package.Mod();m.document=blank(WORLD)
        for name in ('Face_Joy','Face_Anger','SK_Esquie_UE5'):
            role=next(k for k,v in CHARACTERS.items() if v['parts'][0]['path'].endswith('.'+name))
            key=m.add_character(role);clip=m.event('anim-'+key)['params']['asset']
            self.assertEqual(clip,CHARACTERS[role]['default_animation']);self.assertEqual(ANIMATIONS[clip]['skeleton'],CHARACTERS[role]['skeleton'])
            if name=='Face_Anger':self.assertEqual(m.actor(key)['transform']['scale'],[.005]*3)
        role=next(k for k,v in CHARACTERS.items() if v['parts'][0]['path'].endswith('.SK_Hammer_VX'))
        key=m.add_character(role);self.assertEqual(m.event('anim-'+key)['params']['asset'],'bind_pose')

if __name__=='__main__':unittest.main()
