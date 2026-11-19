import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.loading_preparation import LoadingPreparation,service_loading_io
from expedition33.ui_shell_proof import UiProofPending

class LoadingPreparationTests(unittest.TestCase):
    def test_enabled_opt_in_owner_requests_worker_inventory_without_passing_session(self):
        c,mod,owner=self.fixture();owner.preload_layer_selectors=True
        self.assertFalse(c.layer_preparation_requested.is_set())
        self.assertTrue(c.observe(N(ui_context=N(kind='title'))))
        self.assertTrue(c.layer_preparation_requested.is_set())
        c.close();self.assertFalse(c.layer_preparation_requested.is_set())
        disabled,_,disabled_owner=self.fixture(False);disabled_owner.preload_layer_selectors=True
        disabled.observe(N(ui_context=N(kind='title')))
        self.assertFalse(disabled.layer_preparation_requested.is_set())

    def test_worker_inventory_is_adopted_even_before_controller_context_exists(self):
        c,_,owner=self.fixture();c.layer_preparation_requested.set();snapshot=object()
        with patch('expedition33.story_layers.adopt_layer_selectors') as adopt:
            c.observe(N(ui_context=None,prewarm_context=None,layer_selectors=snapshot))
            adopt.assert_called_once_with(c.session,snapshot,None)
            owner.bind.assert_not_called();owner.prepare.assert_not_called()

    def test_disabling_requester_stops_background_inventory_and_ignores_pending_copy(self):
        c,_,owner=self.fixture();owner.preload_layer_selectors=True
        c.observe(N(ui_context=N(kind='title')))
        self.assertTrue(c.layer_preparation_requested.is_set())
        c.loader.registry._settings=N(get=lambda key:{'enabled':False})
        with patch('expedition33.story_layers.adopt_layer_selectors') as adopt:
            c.observe(N(ui_context=None,layer_selectors=object()))
            self.assertFalse(c.layer_preparation_requested.is_set());adopt.assert_not_called()

    def test_opt_in_preflight_pending_is_not_latched_as_construction_failure(self):
        c,mod,owner=self.fixture()
        owner.preparation_pending=True
        owner.prepare.side_effect=UiProofPending('read-only discovery')
        packet=N(ui_context=N(kind='title'))
        self.assertTrue(c.observe(packet))
        self.assertNotIn('Builder',c.failed)
        self.assertIs(c.owners['Builder'],owner)
        owner.observe_title=Mock()
        c.observe(packet)
        owner.observe_title.assert_called_once_with(packet.ui_context)
        owner.prepare.assert_called_once()

    def test_title_pump_cannot_close_suspended_construction_reader(self):
        from expedition33._reader import _active,active_reader
        construction=N(_closed=False)
        title=N(_closed=False)
        def pump():
            self.assertIsNone(active_reader())
            token=_active.set(title)
            try:
                title._closed=True # A deferred stale-descriptor discovery.
            finally:_active.reset(token)
        token=_active.set(construction)
        try:
            service_loading_io(N(_loading_ui_pump=pump))
            self.assertIs(active_reader(),construction)
            self.assertFalse(construction._closed)
        finally:_active.reset(token)

    def test_title_pump_failure_restores_suspended_reader_without_replay(self):
        from expedition33._reader import _active,active_reader
        reader=object();callback=Mock(side_effect=RuntimeError('held'))
        session=N(_loading_ui_pump=callback)
        token=_active.set(reader)
        try:
            with self.assertRaisesRegex(RuntimeError,'held'):service_loading_io(session)
            self.assertIs(active_reader(),reader)
            self.assertFalse(session._loading_ui_pumping)
            callback.assert_called_once_with()
        finally:_active.reset(token)

    def test_story_declaration_precedes_resource_construction_and_runs_once(self):
        c,mod,owner=self.fixture();mod.register_new_game_stories=Mock()
        c.register_story_choices();c.register_story_choices()
        mod.register_new_game_stories.assert_called_once_with(c.session)
        mod.prepare_loading_ui.assert_not_called();owner.prepare.assert_not_called()

    def test_disabled_story_declaration_is_not_executed(self):
        c,mod,_=self.fixture(False);mod.register_new_game_stories=Mock()
        c.register_story_choices();mod.register_new_game_stories.assert_not_called()

    def test_failed_story_declaration_is_held_without_replay(self):
        c,mod,_=self.fixture();mod.register_new_game_stories=Mock(side_effect=RuntimeError('held'))
        with self.assertLogs('expedition33.loading_preparation',level='ERROR'):c.register_story_choices()
        c.register_story_choices();mod.register_new_game_stories.assert_called_once()
        self.assertIn('Builder',c.failed)

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

    def test_verified_bootstrap_prepares_without_gameplay_binding_or_title_retirement(self):
        c,mod,owner=self.fixture();owner.observe_title=Mock()
        context=N(kind='world')
        packet=N(ui_context=None,prewarm_context=context,bootstrap_ready=True)
        self.assertTrue(c.observe(packet));self.assertTrue(c.observe(packet))
        owner.prepare.assert_called_once_with(context)
        owner.bind.assert_not_called();owner.observe_title.assert_not_called()

    def test_disabled_preference_does_not_allocate_widgets(self):
        c,mod,owner=self.fixture(False)
        c.observe(N(ui_context=N(kind='title')))
        mod.prepare_loading_ui.assert_not_called()

    def test_direct_world_loading_recreates_released_preparer_after_cleanup_ack(self):
        c,mod,owner=self.fixture();c.loader.world_lifecycle=N(cleanup_ready=True,bindings={})
        packet=N(ui_context=N(kind='world',world='world',gi='gi'),admission=N(activation_ready=False))
        c.observe(packet)
        owner.prepare.assert_called_once_with(packet.ui_context)
        owner.bind.assert_called_once_with(packet.ui_context,preparing=True)
        owner.released=True
        replacement=N(prepare=Mock(),bind=Mock(),close=Mock(),released=False)
        mod.prepare_loading_ui.return_value=replacement
        c.observe(packet)
        replacement.prepare.assert_called_once_with(packet.ui_context);owner.close.assert_called_once()

    def test_direct_world_loading_does_not_allocate_before_old_cleanup_ack(self):
        c,mod,owner=self.fixture();c.loader.world_lifecycle=N(cleanup_ready=False)
        c.observe(N(ui_context=N(kind='world'),admission=N(activation_ready=False)))
        mod.prepare_loading_ui.assert_not_called()

    def test_bound_departing_epoch_cannot_authorize_new_preparation(self):
        c,mod,owner=self.fixture();c.loader.world_lifecycle=N(cleanup_ready=True,bindings={'Old':N(state='bound',token=('old','gi'))})
        c.observe(N(ui_context=N(kind='world',world='new',gi='gi'),admission=N(activation_ready=False)))
        mod.prepare_loading_ui.assert_not_called()

    def test_released_travel_entry_is_not_rebuilt_in_still_bound_departing_world(self):
        c,mod,owner=self.fixture()
        c.loader.world_lifecycle=N(cleanup_ready=True,bindings={'Travel':N(state='bound',token=('old','gi'))})
        owner.released=True;c.owners['Builder']=owner
        packet=N(ui_context=N(kind='world',world='old',gi='gi'),admission=N(activation_ready=False))
        c.observe(packet);c.observe(packet)
        owner.close.assert_called_once();mod.prepare_loading_ui.assert_not_called()
        c.loader.world_lifecycle.bindings['Travel'].state='retired'
        packet.ui_context=N(kind='world',world='new',gi='gi')
        c.observe(packet);mod.prepare_loading_ui.assert_called_once()

    def test_closed_shared_reader_defers_unattempted_owner_without_failure(self):
        c,mod,owner=self.fixture();packet=N(ui_context=N(kind='title'))
        with patch('expedition33._reader.active_reader',return_value=N(_closed=True)):
            self.assertFalse(c.observe(packet))
        mod.prepare_loading_ui.assert_not_called();self.assertFalse(c.failed)
        self.assertTrue(c.observe(packet));owner.prepare.assert_called_once()

    def test_opted_in_destination_ui_waits_for_its_own_close_not_unrelated_gameplay_retirement(self):
        c,mod,old=self.fixture();c.loader.world_lifecycle=N(cleanup_ready=False)
        old.released=True;old.reprepare_on_world_change=True;old.context=N(signature=('old',))
        c.owners['Builder']=old
        new=N(prepare=Mock(),bind=Mock(),close=Mock(),released=False)
        mod.prepare_loading_ui.return_value=new
        packet=N(ui_context=N(kind='world',signature=('destination',)),admission=N(activation_ready=False))
        c.observe(packet);old.close.assert_called_once()
        new.prepare.assert_called_once_with(packet.ui_context)
        new.bind.assert_called_once_with(packet.ui_context,preparing=True)
        self.assertIs(c.owners['Builder'],new)

    def test_same_context_release_cannot_trigger_independent_repreparation(self):
        c,mod,old=self.fixture();c.loader.world_lifecycle=N(cleanup_ready=False)
        old.released=True;old.reprepare_on_world_change=True;old.context=N(signature=('old',))
        c.owners['Builder']=old
        c.observe(N(ui_context=N(kind='world',signature=('old',)),admission=N(activation_ready=False)))
        old.close.assert_called_once();mod.prepare_loading_ui.assert_not_called()
        self.assertIs(c.owners['Builder'],old)
        new=N(prepare=Mock(),bind=Mock(),close=Mock(),released=False)
        mod.prepare_loading_ui.return_value=new
        c.observe(N(ui_context=N(kind='world',signature=('new',)),admission=N(activation_ready=False)))
        new.prepare.assert_called_once();new.bind.assert_called_once()

    def test_closed_reader_during_binding_does_not_fail_unattempted_owners_or_allow_activation(self):
        c,mod,owner=self.fixture();c.owners['Builder']=owner
        packet=N(ui_context=N(kind='world'),admission=N(activation_ready=True))
        with patch('expedition33._reader.active_reader',return_value=N(_closed=True)):
            self.assertFalse(c.observe(packet))
        owner.bind.assert_not_called();self.assertFalse(c.failed)
        self.assertTrue(c.observe(packet));owner.bind.assert_called_once()

    def test_pending_title_proof_keeps_owner_and_rechecks_without_reconstruction(self):
        c,mod,owner=self.fixture();packet=N(ui_context=N(kind='title'))
        c.observe(packet);owner.observe_title=Mock(side_effect=UiProofPending('loading GC'))
        self.assertTrue(c.observe(packet));self.assertFalse(c.failed)
        owner.observe_title.side_effect=None
        self.assertTrue(c.observe(packet));self.assertEqual(owner.observe_title.call_count,2)
        owner.prepare.assert_called_once()

    def test_loading_pump_is_bounded_nonreentrant_and_restored_after_failure(self):
        c,mod,owner=self.fixture();c.session=N()
        calls=[]
        def pump():
            calls.append('pump')
            service_loading_io(c.session)
        c.session._loading_ui_pump=pump
        with patch('expedition33.loading_preparation.time.monotonic',return_value=10.):
            service_loading_io(c.session);service_loading_io(c.session)
        self.assertEqual(calls,['pump'])
        previous=c.session._loading_ui_pump
        owner.prepare.side_effect=RuntimeError('partial')
        callback=Mock()
        with self.assertLogs('expedition33.loading_preparation',level='ERROR'):
            c.observe(N(ui_context=N(kind='title')),pump=callback)
        callback.assert_called_once_with()
        self.assertIs(c.session._loading_ui_pump,previous)
        self.assertFalse(c.session._loading_ui_pumping)

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

    def test_world_handoff_discards_acknowledged_released_preparation(self):
        c,mod,owner=self.fixture()
        c.observe(N(ui_context=N(kind='title')))
        owner.released=True
        owner.bind.side_effect=UiProofPending('closed widgets cannot rebind')
        self.assertTrue(c.observe(N(ui_context=N(kind='world'),admission=N(activation_ready=True))))
        owner.close.assert_called_once()
        owner.bind.assert_not_called()
        self.assertNotIn('Builder',c.owners)
