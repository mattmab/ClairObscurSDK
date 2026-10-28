import hashlib
import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from cinematics_v2_fixtures import Backend,ready_model,poll
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

    def model(self,row=None):
        return ready_model(module,row or self.scene())

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
        model._refresh_now.assert_not_called()

    def test_title_click_queues_then_fresh_admission_precedes_allocation(self):
        model=self.model();backend=Backend();events=[]
        model._refresh_now.side_effect=lambda:events.append('admit') or model.discovery
        backend.start.side_effect=lambda:events.append('start') or module.StartResult.STARTED
        with patch.object(module,'TitleAdapter',side_effect=lambda *args:events.append('allocate') or backend) as factory:
            model.control(module.DEFINITION,1)
            self.assertEqual(events,[]);factory.assert_not_called()
            poll(model)
            self.assertEqual(events,['admit','allocate','start'])
        self.assertTrue(model.controller.status().busy)
        model.control(module.DEFINITION,4);backend.stop.assert_not_called()
        poll(model);backend.stop.assert_called_once()

    def test_fresh_discovery_revocation_prevents_preparation(self):
        model=self.model()
        model._refresh_now.side_effect=lambda:setattr(model,'library',()) or model.discovery
        with patch.object(module,'TitleAdapter') as factory:
            model.control(module.DEFINITION,1);factory.assert_not_called();poll(model)
            factory.assert_not_called()
        self.assertFalse(model.controller.status().busy)

    def test_pending_cleanup_keeps_menu_and_prevents_new_title(self):
        from expedition33.cinematics.controller import StopResult
        model=self.model();backend=Backend();backend.stop.return_value=StopResult.DEFERRED
        model.controller.queue(module.DEFINITION,lambda:backend,model._last_epoch);model.controller.poll(model._last_epoch)
        with self.assertRaisesRegex(ManagementError,'cleanup'):model.control(module.DEFINITION,1)
        model._refresh_now.assert_not_called()
        view=module.BrowserView(N(_check=Mock()),model)
        with self.assertRaisesRegex(ManagementError,'cleanup'):view.close()
        self.assertFalse(view.closed)

if __name__=='__main__':unittest.main()
