import importlib.util,sys,json,hashlib,unittest
from pathlib import Path
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics import title_profiles as profiles
from expedition33.cinematics import media_profiles as media
from expedition33.cinematics import title_replay as replay
from expedition33.cinematics import title_adapters as adapters_module
from test_cinematics import module as mod
P=Path(profiles.__file__).parent

class CoverageTests(unittest.TestCase):
    def transport(self,p):return N(cinematic_title_profiles=[p.profile_id],**dict.fromkeys(p.required_protocols,1))
    def row(self,p):return dict(id=p.definition,saved_id=p.saved_id,sequence=p.sequence,sha256=p.definition_sha256,title='Title',unlocked=True)
    def test_profile_admission_requires_exact_runtime_and_protocol(self):
        p=profiles.PROLOGUE;t=self.transport(p);self.assertTrue(p.available(t))
        t.cinematic_title_profiles=[];self.assertFalse(p.available(t))
        t.cinematic_title_profiles=[p.profile_id];t.owned_audio_cleanup_protocol=True;self.assertFalse(p.available(t))
    def test_backatcamp_requires_its_own_advertisement_and_empty_channel_protocol(self):
        p=next(p for p in profiles.TITLE_PROFILES.values() if p.profile_id=='back_at_camp')
        t=self.transport(p);self.assertTrue(p.available(t));self.assertEqual(p.sound_mode,'none_verified_empty')
        t.cinematic_empty_title_protocol=0;self.assertFalse(p.available(t))
        t.cinematic_empty_title_protocol=1;t.cinematic_title_profiles=['prologue_lumiere'];self.assertFalse(p.available(t))
    def test_manifest_immutable_and_malformed_rejected(self):
        with self.assertRaises(TypeError):profiles.TITLE_PROFILES['other']=profiles.PROLOGUE
        d=json.loads((P/'title_profiles.json').read_text());d['profiles'][0]['sound_mode']='none_verified_empty'
        with self.assertRaises(ValueError):profiles.load_profiles(d)
    def test_catalog_shared_unlock_is_not_shared_admission(self):
        p=profiles.PROLOGUE;a=self.row(p);b=dict(a,id='Sandfall/Content/Cinematics/Titles/SequenceTitles/DA_GA_CIN_Title_BackAtCamp.uasset')
        c=dict(version=1,manifest_sha256=hashlib.sha256(b'x').hexdigest(),scenes=[a,b])
        rows=mod.catalog_scenes({p.saved_id:True},False,c,b'x',title_profile_ids=[p.profile_id]);self.assertTrue(rows[0]['supported']);self.assertFalse(rows[1]['supported'])
        a['sha256']='0'*64;self.assertFalse(mod.catalog_scenes({p.saved_id:True},False,c,b'x',title_profile_ids=[p.profile_id])[0]['supported'])
    def test_generic_profile_uses_own_asset_and_fresh_unlock(self):
        d=json.loads((P/'title_profiles.json').read_text());r=d['profiles'][0];r.update(profile_id='test_second',definition=r['definition'].replace('PrologueLumiere','Fixture'),sequence=r['sequence'].replace('PrologueLumiere','Fixture'))
        reg=profiles.load_profiles(d);p=next(iter(reg.values()));row=self.row(p);row['definition_sha256']=row.pop('sha256')
        discovery=Mock(return_value=dict(state='history_verified',definition_catalog_complete=True,confirmed=[row]));sequence=Mock();adapters=Mock();adapters.status.return_value={};sequence.owner.status.return_value='armed'
        with patch.object(replay,'TITLE_PROFILES',reg):
            obj=replay.ExactTitleReplay(N(_session=N(_transport=self.transport(p))),lambda:N(state='open',uncertain=False),discovery,adapter_factory=Mock(return_value=adapters),sequence_factory=Mock(return_value=sequence),profile=p)
        panel=N(state='open',uncertain=False);obj.panel_provider=lambda:panel
        obj.start();self.assertEqual(sequence.build.call_args.args[1],p.sequence);sequence.play.assert_not_called()
        row['unlocked']=False
        with self.assertRaises(RuntimeError):obj.play()
        sequence.play.assert_not_called();sequence.close.assert_called_once();adapters.close.assert_called_once();self.assertEqual(discovery.call_count,2)
    def test_unknown_profile_is_rejected_before_ownership(self):
        p=profiles.PROLOGUE;session=N(_session=N(_transport=N(cinematic_title_profiles=[])));factory=Mock()
        obj=replay.ExactTitleReplay(session,Mock(),Mock(),adapter_factory=factory)
        with self.assertRaises(RuntimeError):obj.start()
        factory.assert_not_called()
    def test_pending_other_profile_never_replaces_owner(self):
        model=mod.Mod();p=profiles.PROLOGUE;model.session=N(_session=N(_transport=self.transport(p)));model.video=None
        old=Mock();old.profile=object();old.status.return_value={'active':True};model.title_replay=old
        with self.assertRaises(mod.ManagementError):model.prepare_title(p.definition)
        self.assertIs(model.title_replay,old)

class MediaCoverageTests(unittest.TestCase):
    def test_exact_segments_are_partial_and_wrong_hash_is_blocked(self):
        for p in media.MEDIA_PROFILES.values():
            row=dict(id=p.definition,saved_id=p.saved_id,sequence=p.sequence,sha256=p.definition_sha256,title='scene')
            c=dict(version=1,manifest_sha256=hashlib.sha256(b'x').hexdigest(),scenes=[row])
            result=mod.catalog_scenes({p.saved_id:True},True,c,b'x')[0]
            self.assertTrue(result['supported']);self.assertFalse(result['full_scene']);self.assertEqual(result['validation'],p.validation)
            row['sha256']='0'*64
            self.assertFalse(mod.catalog_scenes({p.saved_id:True},True,c,b'x')[0]['supported'])
    def test_media_menu_exposes_only_play_stop(self):
        p=next(iter(media.MEDIA_PROFILES.values()));model=mod.Mod();model.show_all=False
        model.discovery={'confirmed':[dict(id=p.definition,title='Partial',reason=p.limitation,supported=True,unlocked=True,replay_kind='movie')]}
        view=mod.BrowserView(N(_check=Mock()),model);view.selected=p.definition;frame=view.render()
        self.assertEqual({c.token for c in frame.controls if c.token in (1,2,3,4,5)},{1,4})
        with self.assertRaises(mod.ManagementError):view.activate(frame.revision,2)
    def test_empty_sound_mode_keeps_music_and_widgets_without_sound_factory(self):
        a=object.__new__(adapters_module.OwnedTitleAdapters);a.audio=Mock();a.sound=None;a.widgets=None;a.closed=False
        a.profile=N(profile_id='fixture_empty',sound_mode='none_verified_empty',director='FixtureDirector');a.scope=N(pid=7,invocation_planner=Mock());a.panel=object()
        catalog=N(pid=7,objects=[N(index=1,name='AudioComponent',class_name='Class'),N(index=2,name='Default__AudioComponent'),N(index=3,name='SetPaused',outer_index=1),N(index=4,name='FixtureDirector',class_name='BlueprintGeneratedClass'),N(index=5,name='SequenceEvent',outer_index=4)])
        # Every enumerated object has outer_index, as real CatalogObjects do.
        for obj in catalog.objects:
            if not hasattr(obj,'outer_index'):obj.outer_index=-1
        widgets=Mock();trap_owner=Mock()
        with patch.object(adapters_module,'NativeCinematicSoundEvent',return_value=trap_owner),patch.object(adapters_module,'capture',return_value=catalog),patch.object(adapters_module,'prepare_widgets',return_value=widgets):a.arm(Mock())
        self.assertIs(a.widgets,widgets);a.audio.create_sound.assert_not_called();a.audio.pause_original_audio.assert_called_once();self.assertIs(a.sound,trap_owner);trap_owner.prepare_empty.assert_called_once()

if __name__=='__main__':unittest.main()


