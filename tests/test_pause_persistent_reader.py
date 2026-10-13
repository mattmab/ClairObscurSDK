import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

from expedition33.pause_menu import PauseMenuEntry
from expedition33 import RuntimeQueryError


class PersistentPauseReaderTests(unittest.TestCase):
    def entry(self):
        parent=NS(pid=123,_session=NS(_transport=NS(pause_attachment_protocol=2,trace_renew_protocol=1)))
        service=NS(menu=NS(panel=NS(state='built')),dispose_menu=Mock())
        entry=PauseMenuEntry(parent,service)
        entry.state='attached'
        entry.player=NS(index=1,serial=2,address=100)
        entry.local_player=NS(index=9,serial=10,address=900)
        entry._local_player_owner='LocalPlayer'
        entry.observer=NS(state='active',_observed=0,read=Mock(return_value=[]),renew=Mock(),close=Mock())
        entry._renew_at=float('inf')
        entry.attachment=NS(close=Mock(return_value=True))
        return entry

    def test_reuses_worker_but_reads_fresh_identity_and_reference_each_check(self):
        entry=self.entry()
        with patch('expedition33.pause_menu.ReadBatch') as factory, \
             patch('expedition33.pause_menu.active_reader',return_value=None), \
             patch('expedition33.pause_menu.capture_selected',side_effect=['first','second']) as capture, \
             patch('expedition33.pause_menu.read_object_reference',return_value=(entry.player,None)) as reference:
            entry.poll()
            entry._next_poll=entry._next_world_check=0
            entry.poll()
            factory.assert_called_once_with(123,share=True)
            self.assertEqual(factory.return_value.bind.call_count,2)
            self.assertEqual(capture.call_count,2)
            self.assertEqual([c.args[0] for c in reference.call_args_list],['first','second'])
            factory.return_value.close.assert_not_called()
            entry.close();entry.close()
            factory.return_value.close.assert_called_once()
        self.assertIsNone(entry._world_reader)

    def test_active_context_is_borrowed_without_rebinding_or_closing_owner(self):
        entry=self.entry()
        existing=Mock()
        with patch('expedition33.pause_menu.ReadBatch') as factory, \
             patch('expedition33.pause_menu.active_reader',return_value=existing), \
             patch('expedition33.pause_menu.capture_selected',return_value='fresh'), \
             patch('expedition33.pause_menu.read_object_reference',return_value=(entry.player,None)):
            entry.poll()
            factory.assert_called_once_with(123)
            factory.return_value.bind.assert_not_called()
            self.assertIsNone(entry._world_reader)
            entry.close()
            existing.close.assert_not_called()

    def test_terminal_read_failure_closes_discards_and_does_not_retry(self):
        entry=self.entry()
        with patch('expedition33.pause_menu.ReadBatch') as factory, \
             patch('expedition33.pause_menu.active_reader',return_value=None), \
             patch('expedition33.pause_menu.capture_selected',side_effect=RuntimeQueryError('reader failed')) as capture:
            with self.assertLogs('expedition33.pause_menu',level='ERROR'): entry.poll()
            self.assertEqual(entry.state,'failed')
            self.assertIsNone(entry._world_reader)
            factory.return_value.close.assert_called_once()
            entry.poll()
            capture.assert_called_once()
            entry.close()
            factory.return_value.close.assert_called_once()

    def test_travel_closes_old_worker_before_reinitializing_owner(self):
        entry=self.entry()
        with patch('expedition33.pause_menu.ReadBatch') as factory, \
             patch('expedition33.pause_menu.active_reader',return_value=None), \
             patch('expedition33.pause_menu.capture_selected',return_value='fresh'), \
             patch('expedition33.pause_menu.read_object_reference',return_value=(NS(index=2,serial=3,address=200),None)):
            entry.poll()
            factory.return_value.close.assert_called_once()
        self.assertEqual(entry.state,'new')
        self.assertIsNone(entry._world_reader)
        entry.service.dispose_menu.assert_called_once()


if __name__=='__main__': unittest.main()
