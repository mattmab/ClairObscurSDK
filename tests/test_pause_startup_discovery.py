import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from expedition33 import RuntimeQueryError
from expedition33.pause_menu import PauseMenuEntry


class PauseStartupDiscoveryTests(unittest.TestCase):
    def entry(self):
        return PauseMenuEntry(NS(_session=NS(_transport=NS(pause_attachment_protocol=2,trace_renew_protocol=1))),NS())

    def test_missing_optional_class_can_be_discovered_on_later_scan(self):
        entry=self.entry()
        def install():
            if entry.install.call_count==1:raise RuntimeQueryError('MATCH_TYPE_NOT_REGISTERED')
            entry.state='attached';return True
        entry.install=Mock(side_effect=install)
        entry.poll()
        self.assertEqual(entry.state,'new');self.assertIsNone(entry.scope);self.assertIsNone(entry.attachment)
        entry.poll();self.assertEqual(entry.install.call_count,1)
        entry._next_scan=0;entry.poll()
        self.assertEqual(entry.state,'attached');self.assertEqual(entry.install.call_count,2)

    def test_class_loss_after_build_started_is_not_replayed(self):
        entry=self.entry()
        def install():
            entry.state='building';raise RuntimeQueryError('MATCH_TYPE_NOT_REGISTERED')
        entry.install=Mock(side_effect=install)
        with self.assertLogs('expedition33.pause_menu',level='ERROR'):entry.poll()
        self.assertEqual(entry.state,'failed');entry._next_scan=0;entry.poll()
        self.assertEqual(entry.install.call_count,1)

    def test_unknown_discovery_errors_still_suspend(self):
        entry=self.entry();entry.install=Mock(side_effect=RuntimeQueryError('INVALID_MATCH_SELECTOR'))
        with self.assertLogs('expedition33.pause_menu',level='ERROR'):entry.poll()
        self.assertEqual(entry.state,'failed');entry._next_scan=0;entry.poll()
        self.assertEqual(entry.install.call_count,1)

class PauseBindingIdentityTests(unittest.TestCase):
    def test_gc_flags_do_not_change_identity_but_class_and_outer_still_must_match(self):
        from dataclasses import replace
        from test_catalog import fixture
        original=fixture()[0][4]
        self.assertTrue(PauseMenuEntry._same_bound_object(original,replace(original,object_flags=0x100000,item_flags=0x200000)))
        for change in ({'serial':99},{'address':0x12345},{'class_index':3},{'outer_index':0,'outer_serial':1}):
            with self.subTest(change=change):self.assertFalse(PauseMenuEntry._same_bound_object(original,replace(original,**change)))
        self.assertFalse(PauseMenuEntry._same_bound_object(None,original))
