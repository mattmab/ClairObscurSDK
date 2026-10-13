import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from expedition33.picto_inventory import PictoOwnership, PictoUnlockJob
from expedition33.picto_preferences import validate
from expedition33.picto_gameplay import GAMEPLAY_PICTOS
from expedition33.settings import SettingsError


class Ownership(unittest.TestCase):
    def adapter(self):
        a=PictoOwnership.__new__(PictoOwnership)
        a.scope=a.manager=a.table=a.gi=object()
        a.rows={'Cheater':{'normal':True,'asset':object()}, 'TEST_FullStatsPicto':{'normal':False,'asset':object()}}
        a.owned={};a.function=Mock();a.refresh=Mock()
        return a

    def test_experimental_definition_cannot_be_granted(self):
        a=self.adapter()
        with patch('expedition33.picto_progression.change') as change:
            with self.assertRaisesRegex(ValueError,'Experimental'):a.set_owned('TEST_FullStatsPicto',True)
        change.assert_not_called();a.refresh.assert_not_called()

    def test_ownership_conflict_rejects_before_dispatch(self):
        a=self.adapter();a.owned={'Cheater':object()}
        with patch('expedition33.picto_progression.change') as change:
            with self.assertRaisesRegex(RuntimeError,'ownership changed'):a.set_owned('Cheater',True,expected=False)
        change.assert_not_called()

    def test_already_owned_does_not_regrant_or_change_level(self):
        a=self.adapter();a.owned={'Cheater':object()}
        with patch('expedition33.picto_progression.change') as change:
            self.assertFalse(a.set_owned('Cheater',True))
        change.assert_not_called()

    def test_unknown_result_has_no_blind_retry(self):
        a=self.adapter()
        with patch('expedition33.picto_progression.change',side_effect=RuntimeError('uncertain')) as change:
            with self.assertRaisesRegex(RuntimeError,'uncertain'):a.set_owned('Cheater',True)
        change.assert_called_once();self.assertEqual(a.refresh.call_count,1)

    def test_equipped_removal_has_actionable_message(self):
        a=self.adapter();a.owned={'Cheater':object()}
        with patch('expedition33.picto_progression.change',side_effect=RuntimeError('error=1759, outcome=0')):
            with self.assertRaisesRegex(RuntimeError,'Unequip'):a.set_owned('Cheater',False)

    def test_reply_does_not_replace_authoritative_inventory_readback(self):
        a=self.adapter()
        with patch('expedition33.picto_progression.change',return_value=1):
            with self.assertRaisesRegex(RuntimeError,'readback mismatch'):a.set_owned('Cheater',True)
        self.assertEqual(a.refresh.call_count,2)

    def test_unlock_all_skips_experimental_and_stops_on_failure(self):
        a=self.adapter();a.rows['Other']={'normal':True};a.set_owned=Mock(side_effect=[True,RuntimeError('uncertain')])
        prefs=Mock(profiles={});job=PictoUnlockJob(a,prefs);self.assertEqual(job.total,2)
        job.tick();prefs.remember.assert_called_once_with('Cheater','owned',True)
        with self.assertRaisesRegex(RuntimeError,'uncertain'):job.tick()
        job.tick();self.assertEqual(a.set_owned.call_count,2);self.assertEqual(job.completed,1)

    def test_unlock_reapplies_profile_only_for_newly_created_items(self):
        a=self.adapter();a.set_owned=Mock(return_value=True)
        prefs=Mock(profiles={'Cheater':{'owned':False,'level':22,'cost':2}})
        with patch('expedition33.picto_restore.restore') as restore:
            PictoUnlockJob(a,prefs).tick()
            restore.assert_called_once_with(a.scope,{'Cheater':{'level':22,'cost':2}})
        a.set_owned.return_value=False
        with patch('expedition33.picto_restore.restore') as restore:
            PictoUnlockJob(a,prefs).tick()
            restore.assert_not_called()

    def test_gameplay_allowlist_excludes_test_placeholder_and_unused(self):
        self.assertEqual(len(GAMEPLAY_PICTOS),210)
        self.assertFalse({'TEST_FullStatsPicto','BlankPictos','LuckyAim','CharybdeToScylla'} & GAMEPLAY_PICTOS.keys())
        self.assertEqual(GAMEPLAY_PICTOS['APOnShell'],'Energising Shell')

    def test_persisted_ownership_requires_exact_boolean(self):
        self.assertEqual(validate({'Cheater':{'owned':False,'level':33}})['Cheater']['owned'],False)
        for value in (0,1,'false',None):
            with self.assertRaises(SettingsError):validate({'Cheater':{'owned':value}})
