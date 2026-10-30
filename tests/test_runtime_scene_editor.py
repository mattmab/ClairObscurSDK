import copy,hashlib,importlib.util,json,math,struct,tempfile,unittest
from unittest.mock import Mock
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('scene_editor_tests',ROOT/'mods/SceneEditor/mod.py',submodule_search_locations=[str(ROOT/'mods/SceneEditor')])
package=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=package;spec.loader.exec_module(package)
from scene_editor_tests.scene import validate,sample,encode,SceneStore,SAMPLE,PLAN
from scene_editor_tests.view import SceneView
from expedition33._runtime_scene_wire import validate_request
from expedition33.management import ManagementError

WORLD='/Game/Levels/WorldMap/Level_WorldMap_Main_V2.Level_WorldMap_Main_V2'

class SceneTests(unittest.TestCase):
    def test_disable_revokes_all_queued_world_intents_before_deferred_cleanup(self):
        from unittest.mock import Mock
        model=package.Mod();document={'name':'Unsaved local draft'};model.document=document;model.dirty=True
        flags=('want_open','want_play','reopen','want_saved','want_photo','want_timeline','want_author','want_stop','want_visibility','want_audio_library','cursor_pinned','photo_author')
        pending=('photo_transfer','next_screen','pending_clip','pending_audio_preview','pending_edit','timeline_selection')
        for name in flags:setattr(model,name,True)
        for name in pending:setattr(model,name,object())
        def deferred():
            self.assertTrue(all(getattr(model,name) is False for name in flags))
            self.assertTrue(all(getattr(model,name) is None for name in pending))
            raise RuntimeError('Native cleanup pending')
        model.runtime=SimpleNamespace(disable=deferred);model._close_author_ui=Mock()
        with self.assertRaisesRegex(RuntimeError,'cleanup pending'):model.disable()
        self.assertIs(model.document,document);self.assertTrue(model.dirty)

    def test_photo_start_wire_and_flight_fallback(self):
        packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,75,0,0,1)
        validate_request(bytes(packet),protocol=7)
        struct.pack_into('<iiQ',packet,88,12,3,4096)
        with self.assertRaises(ValueError):validate_request(bytes(packet),protocol=7)
        for at in (104,120):struct.pack_into('<iiQ',packet,at,at,3,4096+at)
        validate_request(bytes(packet),protocol=7)
        packet[136]=1
        with self.assertRaises(ValueError):validate_request(bytes(packet),protocol=7)
        packet[136]=0
        struct.pack_into('<iiQ',packet,88,-1,3,4096)
        with self.assertRaises(ValueError):validate_request(bytes(packet),protocol=7)
        model=package.Mod();self.assertFalse(model.photo_author);self.assertFalse(model.runtime.photo_mode)
        model.document=sample(WORLD)
        view=SceneView(None,model)
        rows=view._rows()
        self.assertIn('Photo mode / timeline',str(rows));self.assertIn('Flight editor / timeline',str(rows))

    def test_camera_shortcuts_wire_and_document_ownership(self):
        for action in (6,7):
            packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,79,0,0,1);struct.pack_into('<2d',packet,88,action,0)
            validate_request(bytes(packet),protocol=7)
        model=package.Mod();calls=[];original=sample(WORLD);model.document=original
        updated=copy.deepcopy(original);updated['name']='captured'
        model.runtime=SimpleNamespace(authoring=False,editor_control=lambda a:calls.append(a),sync_document=lambda d:updated)
        model.snap_camera();model.capture_camera();self.assertFalse(calls)
        model.runtime.authoring=True;model.snap_camera();self.assertIs(model.document,original);self.assertFalse(model.dirty)
        model.capture_camera();self.assertEqual(calls,[6,7]);self.assertIs(model.document,updated);self.assertTrue(model.dirty)
        bindings={b.id:b.default for b in model.management().keybinds}
        self.assertEqual(bindings['snap_camera'],'PageUp');self.assertEqual(bindings['capture_camera'],'.')

    def test_startup_reader_lifetime_and_existing_owner(self):
        from unittest.mock import patch,MagicMock
        model=package.Mod();model.session=SimpleNamespace(pid=123)
        reader=MagicMock();reader.pid=123
        with patch.object(package,'active_reader',return_value=None), patch.object(package,'ReadBatch',return_value=reader) as factory:
            model._start_authoring=lambda:'ready'
            self.assertEqual(model.start_authoring(),'ready')
            factory.assert_called_once_with(123);reader.__exit__.assert_called_once()
        reader.reset_mock()
        with patch.object(package,'active_reader',return_value=reader), patch.object(package,'ReadBatch') as factory:
            self.assertEqual(model.start_authoring(),'ready');factory.assert_not_called();reader.__exit__.assert_not_called()
            reader.pid=456
            with self.assertRaisesRegex(RuntimeError,'another process'):model.start_authoring()
        reader.reset_mock()
        with patch.object(package,'active_reader',return_value=None), patch.object(package,'ReadBatch',return_value=reader):
            def fail():raise ValueError('startup failed')
            model._start_authoring=fail
            with self.assertRaisesRegex(ValueError,'startup failed'):model.start_authoring()
            reader.__exit__.assert_called_once()

    def test_passive_timeline_releases_input_but_preserves_picker(self):
        from scene_editor_tests.timeline import TimelineMenu
        menu=TimelineMenu.__new__(TimelineMenu);calls=[]
        view=SimpleNamespace(closed=False,picker='audio',query='piano')
        view.close=lambda:setattr(view,'closed',True)
        panel=SimpleNamespace(state='open',widget=object(),visible=0,invisible=4)
        panel.restore_child_focus=Mock()
        panel.hide=lambda:(setattr(panel,'state','built') or True)
        panel._render_call=lambda *a,**k:calls.append((a[1:],k))
        menu.panel=panel;menu.view=view;menu.passive=False;menu.mirror=None;menu.actions={'old':object()};menu._accept_input=True
        menu._set_cursor(False)
        panel.restore_child_focus.assert_called_once()
        self.assertFalse(menu._accept_input);self.assertFalse(menu.actions);self.assertTrue(menu.passive)
        self.assertFalse(view.closed);self.assertEqual(view.query,'piano');self.assertEqual(view.picker,'audio')
        menu.open=lambda:(setattr(panel,'state','open'),setattr(menu,'_accept_input',True))
        menu._set_cursor(True)
        self.assertFalse(menu.passive);self.assertTrue(menu._accept_input);self.assertEqual(panel.state,'open')
        self.assertEqual(view.query,'piano')

    def test_display_layer_is_visible_before_cursor_owner_detaches(self):
        from scene_editor_tests.timeline import TimelineMenu
        menu=TimelineMenu.__new__(TimelineMenu);state=dict(input=True,display=False);steps=[]
        def render(obj,owner,operation,**args):
            if operation=='SetRenderOpacity':state['display']=args['InOpacity']>0
            self.assertTrue(state['input'] or state['display'])
        menu.mirror=SimpleNamespace(widget=object(),_render_call=render)
        menu.panel=SimpleNamespace(state='open',widget=object(),visible=0,_render_call=lambda *a,**k:None)
        menu.view=SimpleNamespace(closed=False);menu.passive=False
        def hide():
            self.assertTrue(state['display']);state['input']=False;menu.panel.state='built';steps.append('hide')
        def open_menu():
            self.assertTrue(state['display']);state['input']=True;menu.panel.state='open';steps.append('open')
        menu.hide=hide;menu.open=open_menu
        for _ in range(3):menu._set_cursor(False);menu._set_cursor(True)
        self.assertEqual(steps,['hide','open']*3);self.assertFalse(menu.passive)

    def test_photo_settings_hide_timeline_and_block_cursor_reacquisition(self):
        model=package.Mod();calls=[];model.session=object();model.next_hud=float('inf')
        model.runtime=SimpleNamespace(scope=object(),poll=lambda:None,authoring=True,photo_mode=True,photo_settings_open=lambda:True,editor_control=lambda *a:calls.append(('control',a)))
        model.timeline=SimpleNamespace(set_shown=lambda x:calls.append(('shown',x)))
        model.hud=SimpleNamespace(widget=object(),set_photo_help_compact=lambda x:calls.append(('help',x)),_render_call=lambda *a,**k:None)
        model.want_timeline=model.want_visibility=model.cursor_pinned=True
        model.poll()
        self.assertFalse(model.timeline_shown);self.assertFalse(model.cursor_pinned)
        self.assertFalse(model.want_visibility);self.assertFalse(model.want_timeline)
        self.assertEqual(calls,[('shown',False),('control',(5,1)),('help',False)])

    def test_hidden_timeline_releases_camera_and_preserves_scene(self):
        model=package.Mod();calls=[];model.document=sample(WORLD);original=copy.deepcopy(model.document)
        model.runtime=SimpleNamespace(authoring=True,photo_mode=True,editor_control=lambda *a:calls.append(('control',a)))
        model.timeline=SimpleNamespace(set_shown=lambda value:calls.append(('shown',value)))
        model.hud=SimpleNamespace(widget=object(),set_photo_help_compact=lambda value:calls.append(('help',value)),_render_call=lambda *a,**k:None)
        model.cursor_pinned=True
        model._set_timeline_shown(False)
        self.assertEqual(calls,[('shown',False),('control',(5,1)),('help',False)])
        self.assertFalse(model.timeline_shown);self.assertFalse(model.cursor_pinned)
        model._set_timeline_shown(False);self.assertEqual(len(calls),3)
        model._set_timeline_shown(True)
        self.assertEqual(calls[-2:],[('shown',True),('help',True)])
        self.assertTrue(model.timeline_shown);self.assertEqual(model.document,original)
        bindings={b.id:b.default for b in model.management().keybinds}
        self.assertEqual(bindings['timeline_visibility'],'Backspace')

    def test_timeline_native_ownership_and_authored_audio_wire(self):
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,88,0,0,1)
        for at in (88,104):struct.pack_into('<iiQ',p,at,10+at,3,4096+at)
        for flags in range(4):
            struct.pack_into('<I',p,120,flags);validate_request(bytes(p),protocol=7)
        struct.pack_into('<I',p,120,4)
        with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)
        for kind in (2,3,4):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,84,0,0,1)
            struct.pack_into('<iiQIII',p,88,2,3,4096,23,17,kind)
            validate_request(bytes(p),protocol=7)
        struct.pack_into('<I',p,112,5)
        with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)

    def test_native_camera_drag_sync_preserves_key_identity_and_pose(self):
        from scene_editor_tests.runtime import Runtime
        d=sample(WORLD);d['anchor']=[0,0,0,0]
        d['camera_keys']=[dict(id='camera-aaaaaaaaaaaa',at=10,position=[1,2,3],rotation=[4,5,6],fov=50)]
        values=list(PLAN.unpack(encode(d))[2:]);values[154]=2
        values[155:171]=[2,100,200,300,10,20,30,65,10,1,2,3,4,5,6,50]
        r=Runtime();r.scope=object();r.last['state']='authoring';r.author_plan=values
        synced=r.sync_document(d)
        self.assertEqual(synced['camera_keys'][1]['id'],'camera-aaaaaaaaaaaa')
        self.assertEqual(synced['camera_keys'][0]['position'],[100,200,300])
        self.assertEqual(synced['camera_keys'][0]['rotation'],[10,20,30])
        self.assertEqual(synced['camera_keys'][0]['fov'],65)
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(synced)),synced)

    def test_deleting_clips_preserves_other_slots_volumes_and_character(self):
        from scene_editor_tests.runtime import Runtime
        r=Runtime();d=sample(WORLD)
        for i in range(3):
            d['events'].append(dict(id=f'useranim-{i:012x}',type='animation',target='lune',at=2+i,params=dict(asset='target_idle',speed=1.,loop=False)))
            d['events'].append(dict(id=f'useraudio-{i:012x}',type='audio',target='camera',at=5+i,params=dict(asset='sound',volume=.1+i*.2)))
        r._encode(d,reset=True);before=copy.deepcopy(d)
        d['events']=[e for e in d['events'] if e['id'] not in ('anim-lune','useranim-000000000000','useraudio-000000000000')]
        values=PLAN.unpack(r._encode(d))[2:];self.assertEqual(values[62],-1);self.assertEqual(values[68],-1);self.assertEqual(values[83],2.5)
        self.assertEqual(values[283],3);self.assertEqual(values[284:288],(0,-1,-1,0));self.assertEqual(values[289],3)
        self.assertEqual(values[92],-1);self.assertEqual(values[93],6);self.assertAlmostEqual(values[390],.3)
        self.assertEqual(r.animation_slots['useranim-000000000001'],1);self.assertEqual(r.audio_event_slots['useraudio-000000000001'],1)
        r.scope=object();r.last['state']='authoring';r.author_plan=values;synced=r.sync_document(d)
        self.assertEqual(len(synced['actors']),len(before['actors']));self.assertNotIn('anim-lune',[e['id'] for e in synced['events']])
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(synced)),synced)
        m=package.Mod();m.document=d;v=SceneView(Registry(),m);v.actor_id='lune';v.screen='scene_actor';self.assertTrue(v.render().controls)
        m.choose_animation('lune','lune_attack');self.assertEqual(m.event('anim-lune')['params']['asset'],'lune_attack')
    def test_clip_volume_edit_is_bounded_atomic_and_music_preference_persists(self):
        m=package.Mod();m.document=sample(WORLD);calls=[]
        m.runtime=SimpleNamespace(authoring=True,uncertain=False,audio_event_slots={},editor_control=lambda *a:None,sync_document=lambda d:d,apply=lambda d:calls.append(copy.deepcopy(d)),set_music_quiet=lambda enabled:calls.append(enabled))
        for value,action,expected in ((0,'quieter',0),(2,'louder',2),(.35,'quieter',.3)):
            m.event('audio-0')['params']['volume']=value;m.pending_edit=(action,'audio-0');m._apply_pending_edit();self.assertEqual(m.event('audio-0')['params']['volume'],expected)
        m.pending_edit=('music',None);m._apply_pending_edit();self.assertTrue(m.document['mute_game_music']);self.assertIs(calls[-1],True)
        before=copy.deepcopy(m.document);m.runtime.apply=lambda d:(_ for _ in ()).throw(ValueError('rejected'));m.pending_edit=('delete','anim-lune')
        with self.assertRaises(ValueError):m._apply_pending_edit()
        self.assertEqual(m.document,before)
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertTrue(store.read(store.save(m.document))['mute_game_music'])
    def test_volume_and_music_wire_bounds(self):
        d=sample(WORLD)
        # Select the audio event explicitly; sample event ordering is unchanged.
        next(e for e in d['events'] if e['id']=='audio-0')['params']['volume']=1.2
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,74,0,0,1);p[88:88+PLAN.size]=encode(d);validate_request(bytes(p),protocol=7)
        for value in (-.01,2.01,float('nan')):
            bad=bytearray(p);struct.pack_into('<d',bad,96+380*8,value)
            with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=7)
        for enabled in (0,1):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,87,0,0,1);struct.pack_into('<d',p,88,enabled)
            if enabled:
                for at in range(96,160,16):struct.pack_into('<iiQ',p,at,1,1,123)
            validate_request(bytes(p),protocol=7);p[-1]=1
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)
        for slot in (-1,23,float('inf')):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,86,0,0,1);struct.pack_into('<2d',p,88,slot,0)
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)
    def test_audio_library_sound_paths_survive_save_and_timing_sync(self):
        from scene_editor_tests.timeline import clip_name
        m=package.Mod();m.document=sample(WORLD);path='/Game/Audio/FX/Magic_Hit.Magic_Hit'
        m.audio_paths=(path,);m.runtime=SimpleNamespace(authoring=True,last=dict(selected=0,playhead=4),editor_control=lambda *a:None,sync_document=lambda d:d)
        m.queue_clip('audio',path);candidate,_=m.pending_clip
        event=candidate['events'][-1];self.assertEqual(event['params']['asset'],path);self.assertEqual(clip_name(event),'Magic Hit')
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(candidate)),candidate)
        for asset in ('/Script/Engine.SoundWave','../secret','/Game/Bad.Bad_C;exec','/Game/Bad.Other'):
            bad=copy.deepcopy(candidate);bad['events'][-1]['params']['asset']=asset
            with self.assertRaises(ValueError):validate(bad)
        with self.assertRaises(ValueError):m.queue_clip('audio','/Game/Unknown.Unknown')
    def test_audio_native_wire_limits_and_protocol_admission(self):
        for op,slot in ((83,0),(83,22),(84,23)):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,6,op,0,0,1);struct.pack_into('<iiQII',p,88,1,1,123,slot,5);validate_request(bytes(p),protocol=6)
            for offset,value in ((104,24),(108,250000)):
                bad=bytearray(p);struct.pack_into('<I',bad,offset,value)
                with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=6)
            p[-1]=1
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=6)
            p[-1]=0;struct.pack_into('<I',p,0,5)
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=5)
    def test_distinct_audio_slots_are_configured_once_with_registry_indices(self):
        from scene_editor_tests.runtime import Runtime
        r=Runtime();r.scope=object();calls=[];paths=('/Game/Audio/A.A','/Game/Audio/B.B');doc=sample(WORLD)
        reference=next(e for e in doc['events'] if e['type']=='audio')
        for i,path in enumerate(('sound',*paths)):
            e=copy.deepcopy(reference);e.update(id=f'useraudio-{i:012x}',target='camera');e['params']['asset']=path;doc['events'].append(e)
        r.registry=SimpleNamespace(audio_kind=lambda path:2,catalog=lambda kind:list(paths),load=lambda scope,path,kind:path,identity=lambda obj:bytes(16),command=lambda op,payload:calls.append((op,struct.unpack('<III',payload[1][1]))),release_loading=lambda:None)
        from unittest.mock import patch
        with patch.object(sys.modules['scene_editor_tests.runtime'],'SessionScope',return_value=SimpleNamespace(close=lambda:None)):
            r.configure_audio(doc);r.configure_audio(doc)
        self.assertEqual(calls,[(83,(1,0,2)),(83,(2,1,2))])
        changed=copy.deepcopy(doc);changed['events'][-1]['params']['asset']=paths[0]
        with self.assertRaises(ValueError):r.configure_audio(changed)
    def test_audio_insertion_reacquires_timeline_focus_without_rebuilding_actors(self):
        calls=[];m=package.Mod();m.document=sample(WORLD);candidate=copy.deepcopy(m.document)
        m.pending_clip=(candidate,'audio')
        m.runtime=SimpleNamespace(uncertain=False,authoring=True,configure_audio=lambda d:calls.append('configure'),apply=lambda d:calls.append('apply'),sync_document=lambda d:d,editor_control=lambda *args:calls.append(('input',*args)))
        m.timeline=SimpleNamespace(panel=SimpleNamespace(state='open'),hide=lambda:calls.append('hide'),open=lambda:calls.append('open'))
        m._add_pending_clip();self.assertEqual(calls,['hide','configure','apply',('input',5,0),'open']);self.assertTrue(m.dirty);self.assertIsNone(m.pending_clip)
    def test_multiple_animation_clip_roundtrip_wire_and_drag_sync(self):
        from scene_editor_tests.runtime import Runtime
        d=sample(WORLD)
        for i in range(24):d['events'].append(dict(id=f'useranim-{i:012x}',type='animation',target='lune' if i%2==0 else 'maelle',at=i*.5,params=dict(asset='target_idle',speed=1.,loop=False)))
        d=validate(d);p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,74,0,0,1);p[88:88+PLAN.size]=encode(d);validate_request(bytes(p),protocol=7)
        values=list(PLAN.unpack(encode(d))[2:]);self.assertEqual(values[283],24)
        values[285]=9.;r=Runtime();r.scope=object();r.last['state']='authoring';r.author_plan=values
        synced=r.sync_document(d);self.assertEqual(next(e['at'] for e in synced['events'] if e['id']=='useranim-000000000000'),9.)
        self.assertEqual(next(e['at'] for e in synced['events'] if e['id']=='anim-lune'),1.)
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(synced)),synced)
        d['events'].append(dict(id='useranim-ffffffffffff',type='animation',target='lune',at=0,params=dict(asset='target_idle',speed=1.,loop=False)))
        with self.assertRaises(ValueError):validate(d)
        for index,value in ((283,25),(284,6),(286,9999),(287,2),(288,math.inf)):
            bad=bytearray(p);struct.pack_into('<d',bad,96+index*8,value)
            with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=7)
    def test_timeline_add_clips_at_playhead_without_mutating_original(self):
        m=package.Mod();m.document=sample(WORLD);before=copy.deepcopy(m.document)
        m.runtime=SimpleNamespace(character_skeleton=lambda role:sample(WORLD) and __import__("scene_editor_tests.palette",fromlist=["BODY_SKELETON"]).BODY_SKELETON,authoring=True,last=dict(selected=0,playhead=4.01),editor_control=lambda *args:None,sync_document=lambda doc:doc)
        m.queue_clip('animation','target_idle');candidate,kind=m.pending_clip
        self.assertEqual(kind,'animation');self.assertEqual(candidate['events'][-1]['at'],4);self.assertEqual(candidate['events'][-1]['target'],'lune');self.assertEqual(m.document,before)
        m.queue_clip('audio');candidate,kind=m.pending_clip;self.assertEqual(kind,'audio');self.assertEqual(candidate['events'][-1]['at'],4)
        self.assertTrue(candidate['events'][-1]['id'].startswith('useraudio-'))
    def test_expanded_palette_and_legacy_document_upgrade(self):
        from scene_editor_tests.palette import CHARACTERS,ANIMATIONS,ASSETS,PALETTE
        from expedition33._runtime_scene_wire import ROLE_COUNT,CLIP_COUNT
        self.assertEqual(len(CHARACTERS),ROLE_COUNT);self.assertEqual(len(ANIMATIONS),CLIP_COUNT)
        self.assertGreater(len(CHARACTERS),3);self.assertGreater(len(ANIMATIONS),100)
        self.assertTrue(set(validate(json.loads(SAMPLE.read_text()))['assets'])<=set(ASSETS))
        m=package.Mod();m.document=sample(WORLD)
        for actor in list(m.document['actors']):m.remove_character(actor['id'])
        for role in ('verso','sciel','monoco','braseleur','pelerin','stalact'):m.add_character(role)
        for actor,clip in zip(m.document['actors'],[k for k,v in ANIMATIONS.items() if v['skeleton']==PALETTE['skeleton']][-6:]):m.choose_animation(actor['id'],clip)
        packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,74,0,0,1);packet[88:88+PLAN.size]=encode(m.document);validate_request(bytes(packet),protocol=7)
        for row in list(ANIMATIONS.values())[:293]:self.assertEqual(row['skeleton'],PALETTE['skeleton'])
        with self.assertRaises(ValueError):validate_request(bytes(packet),protocol=2)
        self.assertLess(len(json.dumps(m.document).encode()),128*1024)
    def test_add_duplicates_animation_choices_and_remove_dependencies_roundtrip(self):
        m=package.Mod();m.document=sample(WORLD)
        keys=[m.add_character(role) for role in ('lune','maelle','lune')]
        self.assertEqual(len(m.document['actors']),6)
        before=copy.deepcopy(m.document)
        with self.assertRaises(ValueError):m.add_character('target')
        self.assertEqual(m.document,before)
        m.choose_animation(keys[0],'maelle_attack');m.toggle_loop(keys[0]);m.edit('event:anim-'+keys[0],2.3)
        self.assertFalse(m.event('anim-'+keys[0])['params']['loop'])
        m.remove_character('lune')
        self.assertFalse(any(e['target']=='lune' for e in m.document['events']))
        self.assertTrue(any(e['id']=='audio-1' for e in m.document['events']))
        self.assertFalse(any(e['id']=='audio-0' for e in m.document['events']))
        with tempfile.TemporaryDirectory() as tmp:
            m.store=SceneStore(tmp);key=m.save();self.assertEqual(m.store.read(key),m.document)
        packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,74,0,0,1);packet[88:88+PLAN.size]=encode(m.document);validate_request(bytes(packet))
        for actor in list(m.document['actors']):m.remove_character(actor['id'])
        self.assertEqual(m.document['actors'],[]);self.assertEqual(len(m.document['events']),1)
        packet[88:88+PLAN.size]=encode(m.document);validate_request(bytes(packet))
    def test_animation_and_character_guards(self):
        m=package.Mod();m.document=sample(WORLD)
        for clip in ('/Game/Unsafe.Unsafe','montage',''):
            with self.assertRaises(ValueError):m.choose_animation('lune',clip)
        for mutation in (lambda d:d['actors'][0].update(assembly='unsafe'),lambda d:d['events'][0]['params'].update(loop=1),lambda d:d['events'][0]['params'].update(speed=2),lambda d:d['actors'].append(copy.deepcopy(d['actors'][0]))):
            d=sample(WORLD);mutation(d)
            with self.assertRaises(ValueError):validate(d)
        m.want_play=True
        with self.assertRaises(ValueError):m.add_character('lune')
        with self.assertRaises(ValueError):m.remove_character('lune')
        with self.assertRaises(ValueError):m.choose_animation('lune','target_idle')
    def test_sample_and_edited_roundtrip_preserve_assembly_and_sample(self):
        before=hashlib.sha256(SAMPLE.read_bytes()).hexdigest();d=sample(WORLD)
        d['actors'][0]['transform']['position'][0]=37.;d['events'][0]['at']=1.7
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);key=store.save(d)
            self.assertEqual(store.read(key),validate(d));self.assertEqual(len(store.list()),1)
            packet=bytearray(20984);struct.pack_into('<4IQ',packet,0,7,74,0,0,1)
            packet[88:88+PLAN.size]=encode(store.read(key));validate_request(bytes(packet))
        self.assertEqual(before,hashlib.sha256(SAMPLE.read_bytes()).hexdigest())
    def test_unsupported_assets_events_identity_and_nonfinite_rejected(self):
        for edit in (lambda d:d['assets'].update(lune_body='/Game/Unsafe.BP_C'),lambda d:d['events'][0].update(type='damage'),lambda d:d.update(pointer=123),lambda d:d['events'][0].update(at=float('nan')),lambda d:d['actors'][0]['transform'].update(scale=[1,2,1]),lambda d:d['events'][0].update(at=121),lambda d:d['events'].__setitem__(1,copy.deepcopy(d['events'][0]))):
            d=sample(WORLD);edit(d)
            with self.assertRaises((ValueError,TypeError)):validate(d)
    def test_failed_document_edit_is_atomic(self):
        m=package.Mod();m.document=sample(WORLD);before=copy.deepcopy(m.document)
        with self.assertRaises(ValueError):m.edit('pose:lune:scale:0',0)
        self.assertEqual(m.document,before);self.assertFalse(m.dirty)
    def test_scene_paths_and_duplicate_json_fields_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp)
            with self.assertRaises(ValueError):store.file('../sample')
            key='a'*32;store.file(key).write_text('{"name":"a","name":"b"}')
            with self.assertRaises(ValueError):store.read(key)
    def test_packet_padding_and_invalid_plan_rejected(self):
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,74,0,0,1);p[88:88+PLAN.size]=encode(sample(WORLD))
        p[-1]=1
        with self.assertRaises(ValueError):validate_request(bytes(p))
        p[-1]=0;struct.pack_into('<d',p,96,math.inf)
        with self.assertRaises(ValueError):validate_request(bytes(p))

    def test_camera_keys_roundtrip_and_native_plan(self):
        d=sample(WORLD);d['anchor']=[100,200,300,90]
        d['camera_keys']=[dict(id='camera-aaaaaaaaaaaa',at=20.,position=[400,0,180],rotation=[-5,-170,0],fov=70),dict(id='camera-bbbbbbbbbbbb',at=0.,position=[-400,0,180],rotation=[-15,170,0],fov=50)]
        checked=validate(d);self.assertEqual([k['at'] for k in checked['camera_keys']],[0,20])
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(checked)),checked)
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,74,0,0,1);p[88:88+PLAN.size]=encode(checked,[1,2,3,-10,45,0]);validate_request(bytes(p),protocol=7)
        values=PLAN.unpack_from(p,88)[2:];self.assertEqual(values[154],2);self.assertEqual(list(values[142:146]),d['anchor'])
        for index,value in ((154,17),(155,-1),(163,0),(162,121),(171,1),(146,float('nan'))):
            bad=bytearray(p);struct.pack_into('<d',bad,96+8*index,value)
            with self.assertRaises(ValueError):validate_request(bytes(bad),protocol=7)
        duplicate=copy.deepcopy(d);duplicate['camera_keys'][0]['at']=0
        with self.assertRaises(ValueError):validate(duplicate)

    def test_paintress_raw_mesh_defaults_to_bind_pose_and_remains_compact(self):
        from scene_editor_tests.palette import CHARACTERS
        m=package.Mod();m.document=sample(WORLD)
        role=next(k for k,v in CHARACTERS.items() if v.get('raw') and 'Paintress' in v['label'])
        key=m.add_character(role);self.assertEqual(m.event('anim-'+key)['params']['asset'],'bind_pose')
        values=PLAN.unpack(encode(m.document))[2:];self.assertEqual(values[71],-1)
        self.assertLess(len(json.dumps(m.document)),128*1024)
        v=SceneView(Registry(),m);v.actor_id=key;v.screen='scene_actor';self.assertTrue(any('Bind pose' in c.label for c in v.render().controls))

    def test_extra_audio_limit_and_unbound_independent_cues(self):
        m=package.Mod();m.document=sample(WORLD)
        for actor in list(m.document['actors']):m.remove_character(actor['id'])
        reference=next(e for e in sample(WORLD)['events'] if e['type']=='audio')
        for i in range(23):
            e=copy.deepcopy(reference);e.update(id=f'useraudio-{i:012x}',target='camera',at=i*.5);m.document['events'].append(e)
        p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,74,0,0,1);p[88:88+PLAN.size]=encode(m.document);validate_request(bytes(p),protocol=7)
        e=copy.deepcopy(reference);e.update(id='useraudio-ffffffffffff',target='camera');m.document['events'].append(e)
        with self.assertRaises(ValueError):validate(m.document)

    def test_authoring_command_boundaries(self):
        for op,values in ((77,(5,1)),(78,(120,0)),(79,(5,1))):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,op,0,0,1);struct.pack_into('<2d',p,88,*values);validate_request(bytes(p),protocol=7)
            p[-1]=1
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)

    def test_authoring_reply_is_validated_and_sync_preserves_camera_track(self):
        from scene_editor_tests.runtime import Runtime
        r=Runtime();doc=sample(WORLD);doc['anchor']=[10,20,30,45]
        doc['camera_keys']=[dict(id='camera-aaaaaaaaaaaa',at=0,position=[-300,0,150],rotation=[-10,0,0],fov=50)]
        doc['actors'][0]['transform']['position'][0]=123
        def command(name,p):
            out=bytearray(p);struct.pack_into('<I',out,12,7);out[88:88+PLAN.size]=encode(doc,[1,2,3,4,5,6]);struct.pack_into('<3d',out,56,2.,-1.,1.);struct.pack_into('<II',out,20976,20,4)
            return dict(mesh_packet=out.hex())
        r.session=SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(runtime_scene_protocol=7,command=command)));r.scope=object()
        r._command(75);self.assertTrue(r.authoring);self.assertEqual(r.last['selected'],1)
        synced=r.sync_document(doc);self.assertEqual(synced['camera_keys'],doc['camera_keys']);self.assertEqual(synced['actors'][0]['transform']['position'][0],123)
        def corrupt(name,p):
            result=command(name,p);out=bytearray.fromhex(result['mesh_packet']);struct.pack_into('<d',out,96,float('nan'));return dict(mesh_packet=out.hex())
        r.session._session._transport.command=corrupt
        with self.assertRaises(ValueError):r._command(73)
        self.assertTrue(r.uncertain)
        with self.assertRaises(RuntimeError):r._command(72)

    def test_camera_capture_anchor_roundtrip_and_update_identity(self):
        from scene_editor_tests.scene import capture_camera
        d=sample(WORLD);d['anchor']=[100,200,300,90]
        captured=capture_camera(d,[110,220,350,-10,120,5],2.01,60)
        key=captured['camera_keys'][0];self.assertAlmostEqual(key['position'][0],20);self.assertAlmostEqual(key['position'][1],-10)
        self.assertEqual(key['rotation'],[-10,30,5]);self.assertEqual(key['at'],2.)
        updated=capture_camera(captured,[120,220,360,-20,100,0],7,50,replace=key['id'])
        self.assertEqual(updated['camera_keys'][0]['id'],key['id']);self.assertEqual(updated['camera_keys'][0]['at'],2.)
        self.assertEqual(len(capture_camera(captured,[110,220,350,-10,120,5],2)['camera_keys']),1)
        with self.assertRaises(ValueError):capture_camera(d,[10000,0,0,0,0,0],0)
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(updated)),updated)

    def test_native_drag_times_sync_to_correct_event_ids_and_key(self):
        from scene_editor_tests.runtime import Runtime
        d=sample(WORLD);d['anchor']=[0,0,0,0];d['camera_keys']=[dict(id='camera-aaaaaaaaaaaa',at=0,position=[0,0,100],rotation=[0,0,0],fov=50)]
        values=list(PLAN.unpack(encode(d))[2:]);values[62]=3;values[83]=4;values[155]=5
        r=Runtime();r.scope=object();r.last['state']='authoring';r.author_plan=values
        synced=r.sync_document(d);events={e['id']:e for e in synced['events']}
        self.assertEqual(events['anim-lune']['at'],3);self.assertEqual(events['audio-0']['at'],4);self.assertEqual(synced['camera_keys'][0]['at'],5)
        self.assertEqual(synced['camera_keys'][0]['id'],d['camera_keys'][0]['id'])
        self.assertEqual(next(e['at'] for e in d['events'] if e['id']=='anim-lune'),1)
        with tempfile.TemporaryDirectory() as tmp:
            store=SceneStore(tmp);self.assertEqual(store.read(store.save(synced)),synced)
        for op,values in ((77,(6,1)),(77,(0,2)),(78,(-1,0)),(78,(1,1)),(79,(8,0)),(79,(6,1)),(79,(7,1))):
            p=bytearray(20984);struct.pack_into('<4IQ',p,0,7,op,0,0,1);struct.pack_into('<2d',p,88,*values)
            with self.assertRaises(ValueError):validate_request(bytes(p),protocol=7)

class Registry:
    def _check(self):pass
    def select(self,key):return key
    def view(self,key):return {'id':key}

class ViewTests(unittest.TestCase):
    def test_audio_picker_search_select_preview_and_add_use_the_selected_path(self):
        from scene_editor_tests.timeline import TimelineView
        paths=('/Game/Audio/Lune/Lightning_Hit.Lightning_Hit','/Game/Audio/Maelle/Sword_Hit.Sword_Hit','/Game/Audio/UI/Click.Click')
        calls=[];m=SimpleNamespace(audio_paths=paths,runtime=SimpleNamespace(authoring=True,last=dict(selected=0)),document=sample(WORLD),message='',queue_clip=lambda *a:calls.append(a))
        v=TimelineView(Registry(),m);f=v.render();f=v.activate(f.revision,15);self.assertEqual(len(f.controls),36)
        f=v.activate(f.revision,34);f=v.activate(f.revision,27,value='lune hit');self.assertEqual(v.choices,(paths[0],))
        f=v.activate(f.revision,19);f=v.activate(f.revision,29);self.assertEqual(m.pending_audio_preview,paths[0])
        f=v.activate(f.revision,31);self.assertEqual(calls[-1],('audio',paths[0]))
        f=v.activate(f.revision,30);self.assertEqual(m.pending_audio_preview,'')
        f=v.activate(f.revision,27,value='nothingmatches');self.assertFalse(v.choices);self.assertFalse(f.controls[19].enabled)
        with self.assertRaises(ManagementError):v.activate(f.revision,19)
        f=v.activate(f.revision,28);self.assertEqual(len(v.choices),3)
    def test_music_library_uses_authored_sets_without_guessing_note_order(self):
        from scene_editor_tests.timeline import TimelineView
        paths=('/Game/Audio/Music/Piano_C4.Piano_C4','/Game/Audio/MetaSound/Music/Tracks/Melody.Melody','/Game/Audio/Musics/Finale_Cue.Finale_Cue')
        kinds=dict(zip(paths,(2,4,3)));calls=[]
        model=SimpleNamespace(runtime=SimpleNamespace(authoring=True,last=dict(selected=0),registry=SimpleNamespace(audio_kinds=kinds)),audio_paths=paths,document=sample(WORLD),message='',queue_clip=lambda *args:calls.append(args))
        view=TimelineView(None,model);frame=view.render();frame=view.activate(frame.revision,15)
        self.assertEqual(view.choices,paths[1:]);self.assertTrue(frame.controls[19].label.startswith('[Set]'))
        frame=view.activate(frame.revision,19);frame=view.activate(frame.revision,31)
        self.assertEqual(calls,[('audio',paths[1])])
        frame=view.activate(frame.revision,34);self.assertEqual(view.choices,(paths[0],))
        frame=view.activate(frame.revision,35);self.assertEqual(view.choices,paths)

    def test_timeline_picker_adds_named_clips_and_pages_without_replacing_primary(self):
        from scene_editor_tests.timeline import TimelineView,clip_name
        calls=[];model=SimpleNamespace(animation_context=lambda key:('lune',__import__('scene_editor_tests.palette',fromlist=['BODY_SKELETON']).BODY_SKELETON),runtime=SimpleNamespace(authoring=True,last=dict(selected=0)),document=sample(WORLD),message='',audio_paths=None,queue_clip=lambda *args:calls.append(args))
        view=TimelineView(Registry(),model);frame=view.render();frame=view.activate(frame.revision,14)
        self.assertEqual([c.token for c in frame.controls],list(range(36)));self.assertEqual(frame.controls[19].label,'Lune - Thunder Kick')
        frame=view.activate(frame.revision,19);self.assertFalse(calls);self.assertEqual(view.selected_animation,'lune_attack');frame=view.activate(frame.revision,31);self.assertEqual(calls[-1],('animation','lune_attack'));self.assertEqual(view.picker,'animation')
        frame=view.render();view.activate(frame.revision,15);self.assertEqual(view.picker,'audio');self.assertTrue(model.want_audio_library)
        frame=view.render();frame=view.activate(frame.revision,14);frame=view.activate(frame.revision,16)
        self.assertEqual(frame.page,frame.pages-1);self.assertEqual(len(frame.controls),36);self.assertTrue(frame.controls[-1].enabled)
        self.assertEqual(clip_name(model.document['events'][0]),'Lune - Thunder Kick')
    def test_animation_library_search_group_selection_and_explicit_insert(self):
        from scene_editor_tests.timeline import TimelineView,ANIMATIONS
        calls=[];model=SimpleNamespace(animation_context=lambda key:('lune',__import__('scene_editor_tests.palette',fromlist=['BODY_SKELETON']).BODY_SKELETON),runtime=SimpleNamespace(authoring=True,last=dict(selected=0)),document=sample(WORLD),message='',audio_paths=None,queue_clip=lambda *args:calls.append(args))
        view=TimelineView(Registry(),model);frame=view.render();frame=view.activate(frame.revision,14)
        frame=view.activate(frame.revision,35);self.assertEqual(view.animation_group,'character')
        self.assertTrue(all('/Lune/' in ANIMATIONS[key]['path'] for key in view.choices))
        frame=view.activate(frame.revision,27,value='nothingmatches');self.assertFalse(view.choices)
        frame=view.activate(frame.revision,28);frame=view.activate(frame.revision,19)
        self.assertFalse(calls);selected=view.selected_animation
        frame=view.activate(frame.revision,31);self.assertEqual(calls,[('animation',selected)])
        self.assertEqual(view.picker,'animation')
        frame=view.activate(frame.revision,32);self.assertIsNone(view.animation_group)
        frame=view.activate(frame.revision,34);self.assertIsNotNone(view.animation_group)
        with self.assertRaises(ValueError):view.activate(frame.revision,27,value='x'*161)

    def test_timeline_frame_steps_selection_and_stale_controls(self):
        from scene_editor_tests.timeline import TimelineView
        calls=[]
        runtime=SimpleNamespace(authoring=True,last=dict(selected=0,playhead=0,state='authoring'),seek=lambda seconds:calls.append(('seek',seconds)),editor_control=lambda *args:calls.append(('control',*args)),audition=lambda *args:calls.append(('audition',*args)))
        model=SimpleNamespace(runtime=runtime,document=sample(WORLD),message='',want_timeline=False,want_stop=False)
        view=TimelineView(Registry(),model);frame=view.render();view.activate(frame.revision,6);self.assertEqual(calls[-1],('seek',0))
        with self.assertRaises(ManagementError):view.activate(frame.revision,7)
        frame=view.render();view.activate(frame.revision,7);self.assertEqual(calls[-1],('seek',1/30))
        frame=view.render();view.activate(frame.revision,1);self.assertEqual(calls[-1],('control',4,2))
        frame=view.render();view.activate(frame.revision,3);self.assertEqual(calls[-1],('audition',0,True))
        frame=view.render();view.activate(frame.revision,8);self.assertEqual(calls[-1],('control',1))
        frame=view.render();view.activate(frame.revision,10);self.assertTrue(model.want_stop)
    def test_character_search_finds_registry_paintress(self):
        m=package.Mod();m.document=sample(WORLD);v=SceneView(Registry(),m);v.screen='scene_add';v.actor_catalog_all=True
        frame=v.render();search=next(c for c in frame.controls if c.label=='Search');v.activate(frame.revision,search.token,value='Paintress')
        rows=[r for r in v._rows()[2] if r[1]=='scene_actor_asset'];self.assertTrue(rows);self.assertTrue(all('Paintress' in r[0] for r in rows))
    def test_animation_search_and_category_are_scene_local(self):
        m=package.Mod();m.document=sample(WORLD);v=SceneView(Registry(),m);v.screen='scene_animation'
        frame=v.render();all_clips=next(c for c in frame.controls if c.label=='All compatible animations');frame=v.activate(frame.revision,all_clips.token)
        search=next(c for c in frame.controls if c.label=='Search');v.activate(frame.revision,search.token,value='Monoco_Idle_Base')
        self.assertEqual(v.screen,'scene_clips')
        frame=v.render();clip=next(c for c in frame.controls if c.label=='Monoco Idle Base')
        v.activate(frame.revision,clip.token)
        self.assertEqual(v.screen,'scene_actor');self.assertEqual(v.query,'');self.assertNotEqual(m.event('anim-lune')['params']['asset'],'lune_attack')
    def test_native_view_edit_then_save_and_load_without_playback(self):
        m=package.Mod();m.document=sample(WORLD)
        with tempfile.TemporaryDirectory() as tmp:
            m.store=SceneStore(tmp);v=SceneView(Registry(),m);v.screen='scene_transform'
            frame=v.render();control=next(c for c in frame.controls if c.label.startswith('Forward X:'))
            v.activate(frame.revision,control.token)
            frame=v.render();apply=next(c for c in frame.controls if c.label=='Apply')
            v.activate(frame.revision,apply.token,value='45')
            self.assertEqual(m.actor('lune')['transform']['position'][0],45)
            self.assertIsNone(v.editing)
            key=m.save('Edited sample',save_as=True);m.document=sample(WORLD);m.load(key)
            self.assertEqual(m.actor('lune')['transform']['position'][0],45)
            self.assertIsNone(m.runtime.scope);self.assertFalse(m.want_play)
            with self.assertRaises(ManagementError):v.activate(frame.revision,apply.token,value='12')

if __name__=='__main__':unittest.main()
