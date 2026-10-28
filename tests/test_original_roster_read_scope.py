import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from expedition33 import RuntimeQueryError
from expedition33._reader import ReadBatch, active_reader
from expedition33.original_encounter_roster import _verify_source


class ReachedSelectedRead(Exception):
    pass


class RosterReadScopeTests(unittest.TestCase):
    def setUp(self):
        self.scope=SimpleNamespace(pid=123,_session=SimpleNamespace(
            _transport=SimpleNamespace(_executable=Path('candidate-reader.exe'))))
        self.source=SimpleNamespace(index=1,serial=2,address=0x10000)
        self.enterContext(patch.object(ReadBatch,'warm',return_value=None))
        self.enterContext(patch('expedition33.original_encounter_roster.capture_selected',
                                side_effect=ReachedSelectedRead))

    def test_borrows_existing_reader_without_replacing_or_closing_owner(self):
        with ReadBatch(123,share=True) as owner:
            with self.assertRaises(ReachedSelectedRead):
                _verify_source(self.scope,self.source,'exact')
            self.assertIs(active_reader(),owner)
            self.assertFalse(owner._closed)

    def test_standalone_read_owns_and_releases_reader(self):
        with self.assertRaises(ReachedSelectedRead):
            _verify_source(self.scope,self.source,'exact')
        self.assertIsNone(active_reader())

    def test_foreign_process_or_exclusive_owner_still_rejected(self):
        for pid,share in ((124,True),(123,False)):
            with ReadBatch(pid,share=share) as owner:
                with self.assertRaises(RuntimeQueryError):
                    _verify_source(self.scope,self.source,'exact')
                self.assertIs(active_reader(),owner)
                self.assertFalse(owner._closed)
