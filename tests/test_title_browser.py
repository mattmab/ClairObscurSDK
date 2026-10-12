import hashlib
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from test_cinematics import module
from expedition33.management import ManagementError

class TitleBrowserTests(unittest.TestCase):
    def scene(self, **changes):
        row=dict(id=module.DEFINITION, saved_id=module.SAVE_ID, sequence=module.SEQUENCE,
            sha256=module.PROLOGUE.definition_sha256, title='Prologue', supported=True, unlocked=True, replay_kind='title', reason='verified')
        row.update(changes)
        return row

    def catalog(self, row):
        return dict(version=1,manifest_sha256=hashlib.sha256(b'x').hexdigest(),scenes=[row])

    def model(self, row=None):
        model=module.Mod()
        model.discovery={'confirmed':[row or self.scene()]}
        model.show_all=False
        model.session=N(_session=N(_transport=N(cinematic_title_profiles=['prologue_lumiere'],**dict.fromkeys(module.TITLE_PROTOCOLS,1))))
        model.discover=Mock()
        model.prepare_title=Mock()
        model.title_replay=Mock()
        model.title_replay.stop.return_value={'active':False,'state':'stopped'}
        return model

    def test_exact_definition_sequence_save_and_unlock_gate(self):
        for changes in ({'id':'wrong'}, {'saved_id':'wrong'}, {'sequence':'wrong'}):
            rows=module.catalog_scenes({module.SAVE_ID:True},False,self.catalog(self.scene(**changes)),b'x',title_profile_ids=('prologue_lumiere',))
            self.assertFalse(rows[0]['supported'])
        for unlock in (False,None,1):
            rows=module.catalog_scenes({module.SAVE_ID:unlock},False,self.catalog(self.scene()),b'x',title_profile_ids=('prologue_lumiere',))
            self.assertFalse(rows[0]['supported'])
        self.assertTrue(module.catalog_scenes({module.SAVE_ID:True},False,self.catalog(self.scene()),b'x',title_profile_ids=('prologue_lumiere',))[0]['supported'])
        self.assertFalse(module.catalog_scenes({module.SAVE_ID:True},False,self.catalog(self.scene()),b'x')[0]['supported'])

    def test_v52_capability_is_required_and_bool_is_not_version(self):
        transport=N(cinematic_title_profiles=['prologue_lumiere'],**dict.fromkeys(module.TITLE_PROTOCOLS,1))
        self.assertTrue(module.title_available(transport))
        for version in (0,True,2):
            transport.owned_audio_cleanup_protocol=version
            self.assertFalse(module.title_available(transport))

    def test_view_only_exposes_play_stop_and_rejects_forged_tokens(self):
        model=self.model()
        view=module.BrowserView(N(_check=Mock()),model)
        view.selected=module.DEFINITION
        frame=view.render()
        self.assertEqual([c.token for c in frame.controls if 1<=c.token<=5],[1,4])
        for token in (2,3,5):
            with self.assertRaisesRegex(ManagementError,'only Play and Stop'):view.activate(frame.revision,token)
        model.prepare_title.assert_not_called()

    def test_title_uses_fresh_discovery_prepare_and_existing_play(self):
        model=self.model()
        events=[]
        model.discover.side_effect=lambda:events.append('discover')
        model.prepare_title.side_effect=lambda scene:events.append('prepare')
        model.title_replay.play.side_effect=lambda:events.append('play')
        model.control(module.DEFINITION,1)
        self.assertEqual(events,['discover','prepare','play'])
        self.assertIsNone(model.video)
        model.control(module.DEFINITION,4)
        self.assertEqual(model.playback_status,'Stopped')

    def test_fresh_discovery_revocation_prevents_preparation(self):
        model=self.model()
        model.discover.side_effect=lambda:model.discovery.update(confirmed=[])
        with self.assertRaisesRegex(ManagementError,'not unlocked'):model.control(module.DEFINITION,1)
        model.prepare_title.assert_not_called()
        model.title_replay.play.assert_not_called()

    def test_pending_cleanup_keeps_menu_and_prevents_new_title(self):
        model=self.model()
        model.title_replay.stop.return_value={'active':True,'state':'cleanup_pending'}
        with self.assertRaisesRegex(ManagementError,'cleanup'):model.control(module.DEFINITION,1)
        model.discover.assert_not_called()
        model.prepare_title.assert_not_called()
        view=module.BrowserView(N(_check=Mock()),model)
        with self.assertRaisesRegex(ManagementError,'cleanup'):view.close()
        self.assertFalse(view.closed)

if __name__=='__main__':unittest.main()

