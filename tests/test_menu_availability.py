from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock, patch

from expedition33 import RuntimeQueryError, release_startup
from expedition33.cinematics.original_game_action import NotReady
from expedition33.management import ManagementError
from expedition33.management_service import NativeMenuService
from expedition33.pause_menu import PauseMenuEntry


class AvailabilityTests(unittest.TestCase):
    def test_expected_missing_controller_and_identity_races_are_uncertain(self):
        for error in (NotReady('controller not available'),
                RuntimeQueryError('Object identity changed or belongs to another process'),
                RuntimeQueryError('Object property reference changed during observation'),
                RuntimeQueryError('READ_FAILED win32=299')):
            with self.subTest(error=error), patch.object(release_startup,'menu_ready',side_effect=error) as read:
                self.assertIsNone(release_startup.menu_availability(7))
                self.assertEqual(read.call_count,1)

    def test_known_false_and_true_preserved(self):
        for state in (False,True):
            with patch.object(release_startup,'menu_ready',return_value=state):
                self.assertIs(release_startup.menu_availability(7),state)

    def test_decoder_and_unknown_failures_are_visible(self):
        for error in (RuntimeQueryError('Invalid object property reference'),RuntimeError('unexpected')):
            with self.subTest(error=error),patch.object(release_startup,'menu_ready',side_effect=error):
                with self.assertRaises(type(error)) as raised:release_startup.menu_availability(7)
                self.assertIs(raised.exception,error)

    def service(self, readiness):
        scope=N(_check=lambda:None,supports_multi_controls=True)
        factory=Mock()
        service=NativeMenuService(scope,Mock(),readiness=lambda:readiness,menu_factory=factory)
        return service,factory

    def test_uncertain_service_retains_old_menu_without_close_or_construction(self):
        service,factory=self.service(None)
        menu=Mock();service.menu=menu
        service.poll();service.prepare()
        self.assertIs(service.menu,menu)
        menu.close.assert_not_called()
        factory.assert_not_called()
        self.assertFalse(service._warmup_attempted)

    def test_false_service_closes_acknowledged_owner_and_stays_inert(self):
        service,factory=self.service(False)
        menu=Mock();menu.close.return_value=True;service.menu=menu
        service.poll();service.prepare()
        menu.close.assert_called_once_with()
        self.assertIsNone(service.menu)
        factory.assert_not_called()

    def test_false_service_retains_deferred_owner(self):
        service,factory=self.service(False)
        menu=Mock();menu.close.return_value=False;service.menu=menu
        with self.assertRaises(ManagementError):service.poll()
        self.assertIs(service.menu,menu)
        factory.assert_not_called()

    def entry(self, readiness):
        scope=N(_session=N(_transport=N(pause_attachment_protocol=2,trace_renew_protocol=1)))
        entry=PauseMenuEntry(scope,Mock(),readiness=lambda:readiness)
        entry.state='attached'
        entry.attachment=Mock()
        entry.attachment.close.return_value=True
        entry.scope=Mock()
        entry.observer=Mock()
        return entry

    def test_uncertain_pause_retains_every_owner_without_install_or_close(self):
        entry=self.entry(None)
        observer=entry.observer
        with patch.object(entry,'install') as install:
            entry.poll()
            install.assert_not_called()
        entry.attachment.close.assert_not_called()
        entry.scope.close.assert_not_called()
        observer.close.assert_not_called()
        self.assertEqual(entry.state,'attached')

    def test_false_pause_performs_acknowledged_cleanup(self):
        entry=self.entry(False)
        observer=entry.observer
        entry.poll()
        observer.close.assert_called_once_with()
        entry.attachment.close.assert_called_once_with()
        entry.scope.close.assert_called_once_with()
        self.assertEqual(entry.state,'closed')
        self.assertTrue(entry._waiting_ready)

    def test_false_pause_retains_deferred_attachment(self):
        entry=self.entry(False)
        attachment=entry.attachment;attachment.close.return_value=False
        with self.assertRaisesRegex(RuntimeError,'deferred'):entry.poll()
        self.assertIs(entry.attachment,attachment)
        self.assertEqual(entry.state,'attached')
        entry.scope.close.assert_not_called()


if __name__=='__main__':unittest.main()
