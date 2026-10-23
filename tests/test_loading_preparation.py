import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33.loading_preparation import LoadingPreparation
from expedition33.ui_shell_proof import UiProofPending

class LoadingPreparationTests(unittest.TestCase):
    def fixture(self,enabled=True):
        owner=N(prepare=Mock(),bind=Mock(),close=Mock())
        mod=N(prepare_loading_ui=Mock(return_value=owner))
        loader=N(_startup_preparations={'Builder':object()},_loaded={'Builder':(None,mod)})
        loader.registry=N(views=lambda:[{'folder':'Builder','id':'builder'}],
            _settings=N(get=lambda key:{'enabled':enabled}))
        coordinator=LoadingPreparation(object(),loader)
        return coordinator,mod,owner

    def test_title_prepares_enabled_definition_once_without_enabling_mod(self):
        c,mod,owner=self.fixture()
        packet=N(ui_context=N(kind='title'),prewarm_context=None)
        self.assertTrue(c.observe(packet));self.assertTrue(c.observe(packet))
        owner.prepare.assert_called_once_with(packet.ui_context)
        mod.prepare_loading_ui.assert_called_once()
        owner.bind.assert_not_called()
        c.close();owner.close.assert_called_once()

    def test_disabled_preference_does_not_allocate_widgets(self):
        c,mod,owner=self.fixture(False)
        c.observe(N(ui_context=N(kind='title')))
        mod.prepare_loading_ui.assert_not_called()

    def test_loading_handoff_cannot_activate_mod_and_pending_blocks_restore(self):
        c,mod,owner=self.fixture()
        c.observe(N(ui_context=N(kind='title')))
        world=N(kind='world')
        packet=N(ui_context=None,prewarm_context=world,admission=N(activation_ready=False))
        self.assertTrue(c.observe(packet))
        owner.bind.assert_called_once_with(world,preparing=True)
        owner.bind.side_effect=UiProofPending('waiting')
        self.assertFalse(c.observe(packet))
        self.assertIn('Builder',c.owners)

    def test_construction_failure_retains_owner_for_explicit_cleanup(self):
        c,mod,owner=self.fixture();owner.prepare.side_effect=RuntimeError('partial')
        with self.assertLogs('expedition33.loading_preparation',level='ERROR'):
            self.assertTrue(c.observe(N(ui_context=N(kind='title'))))
        self.assertIs(c.owners['Builder'],owner)
        c.close();owner.close.assert_called_once()

    def test_retired_widgets_reprepare_at_title_before_next_save(self):
        c,mod,owner=self.fixture();packet=N(ui_context=N(kind='title'))
        c.observe(packet);owner.released=True
        c.observe(packet)
        owner.close.assert_called_once()
        self.assertEqual(owner.prepare.call_count,2)
