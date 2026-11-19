import unittest
from unittest.mock import Mock
from expedition33 import RuntimeQueryError
from expedition33.ui_shell_proof import OwnedUiProof,UiProofPending
class LoadingRaceTests(unittest.TestCase):
    def test_changed_read_only_reflection_target_defers_handoff(self):
        for reason in ('REFLECTION_TARGET_CHANGED','DESCRIPTOR_SET_INCOMPLETE'):
            proof=OwnedUiProof.__new__(OwnedUiProof);proof._current_observation=Mock(side_effect=RuntimeQueryError(reason))
            with self.assertRaises(UiProofPending):proof._current(object(),preparing=True)
            proof._current_observation.assert_called_once()
    def test_unrecognized_failure_is_not_hidden(self):
        proof=OwnedUiProof.__new__(OwnedUiProof);proof._current_observation=Mock(side_effect=RuntimeQueryError('invalid schema'))
        with self.assertRaisesRegex(RuntimeQueryError,'invalid schema'):proof._current(object(),preparing=True)
