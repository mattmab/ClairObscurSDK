import importlib
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,MagicMock,patch
import test_firstparty_startup as package_fixture


class LoadingModPreparationTests(unittest.TestCase):
    def load(self,name):
        module,_=package_fixture.Tests.load(self,name)
        return module

    def test_flight_harvests_latest_worker_at_enable_and_discards_other_world(self):
        module=self.load('ContinentFlight')
        loading=importlib.import_module(module.__name__+'.loading')
        mod=module.Mod();owner=loading.LoadingFlight(mod,N(pid=7));monitor=Mock()
        title=N(signature=('title',));world=N(signature=('world',1))
        result=('copied snapshot','copied metadata')
        with patch.object(loading,'prepare_static',return_value=N(_entries={})), patch('expedition33._reader.ReadBatch'), patch.object(loading,'ReadOnlyAdmissionMonitor',return_value=monitor):
            owner.prepare(title)
        monitor.snapshot.return_value=None
        owner.bind(world,preparing=True);self.assertIsNone(mod._loading_flight)
        monitor.snapshot.return_value=N(admission=result)
        with patch.object(owner,'matches',return_value=True):
            self.assertEqual(owner.take_snapshot(),(world.signature,result))
        self.assertIsNone(mod._loading_flight)
        with patch.object(owner,'matches',return_value=False):
            self.assertIsNone(owner.take_snapshot())
        owner.close();monitor.close.assert_called_once_with(timeout=2.)

    def test_flight_read_worker_transfers_once_and_rewarms_after_retirement(self):
        module=self.load('ContinentFlight')
        loading=importlib.import_module(module.__name__+'.loading')
        mod=module.Mod();owner=loading.LoadingFlight(mod,N(pid=7));reader=MagicMock()
        with patch.object(loading,'prepare_static',return_value=N(_entries={})), patch('expedition33._reader.ReadBatch',return_value=reader) as factory, patch.object(loading,'ReadOnlyAdmissionMonitor'):
            owner.prepare(N());self.assertIs(owner.take_reader(),reader)
            self.assertIsNone(owner.take_reader())
            mod.reader=reader;owner.observe_title(N());self.assertEqual(factory.call_count,1)
            mod.reader=None;owner.observe_title(N());self.assertEqual(factory.call_count,2)
            owner.close();reader.close.assert_called_once()

    def test_flight_prepares_captured_package_without_world_mutation(self):
        module=self.load('ContinentFlight')
        loading=importlib.import_module(module.__name__+'.loading')
        module.discover_snapshot=Mock(side_effect=module.ExplorationNotReady('loading'))
        with patch('expedition33._reader.ReadBatch'):
            with self.assertRaises(module.ExplorationNotReady):loading.prepare_snapshot(7)
        module.discover_snapshot.assert_called_once_with(7)

    def test_flight_stops_sampling_without_waiting_and_restarts_only_after_cleanup_ack(self):
        module=self.load('ContinentFlight');loading=importlib.import_module(module.__name__+'.loading')
        mod=module.Mod();owner=loading.LoadingFlight(mod,N(pid=7));old=Mock();new=Mock()
        old.close.side_effect=(False,False,True)
        with patch.object(loading,'prepare_static',return_value=N(_entries={})),patch('expedition33._reader.ReadBatch'),patch.object(loading,'ReadOnlyAdmissionMonitor',side_effect=(old,new)) as factory:
            owner.prepare(N());owner.activated()
            old.close.assert_called_once_with(timeout=0.)
            owner.observe_title(N());self.assertIs(owner.monitor,old);self.assertEqual(factory.call_count,1)
            owner.observe_title(N());self.assertIs(owner.monitor,new);self.assertEqual(factory.call_count,2)
            self.assertTrue(owner._observing)

    def test_flight_does_not_bind_a_new_owned_reader_inside_a_menu_read_operation(self):
        module=self.load('ContinentFlight');loading=importlib.import_module(module.__name__+'.loading')
        owner=loading.LoadingFlight(module.Mod(),N(pid=7));reader=Mock()
        with patch('expedition33._reader.ReadBatch',return_value=reader),patch('expedition33._reader.active_reader',return_value=object()):
            owner._prepare_reader()
        self.assertIs(owner.reader,reader);reader.bind.assert_not_called();reader.warm.assert_called_once_with()

    def test_map_monitor_handoff_does_not_close_the_active_mods_worker(self):
        module=self.load('WorldBuilderMapLoader')
        loading=importlib.import_module(module.__name__+'.loading_context')
        mod=module.Mod();owner=loading.LoadingContext(mod,N(pid=7));monitor=Mock()
        with patch.object(loading,'ReadOnlyAdmissionMonitor',return_value=monitor):owner.prepare(N())
        self.assertIs(owner.take(),monitor);self.assertTrue(owner.released)
        owner.close();monitor.close.assert_not_called()

    def test_travel_entry_builds_without_polling_clicks_and_retains_pending_owner(self):
        module=self.load('MapTravel')
        loading=importlib.import_module(module.__name__+'.loading_entry')
        scope=Mock();scope._closed=False
        session=N(pid=7,_menu_readiness=lambda:True,_native_menu_service=Mock())
        first=N(signature=('world',1),controller=(7,1,2,3))
        second=N(signature=('world',2),controller=(7,4,5,6))
        entry=Mock(state='new')
        with patch.object(loading,'SessionScope',return_value=scope), \
             patch.object(loading,'PauseMenuEntry',return_value=entry) as factory, \
             patch('expedition33.zone_travel.routes',return_value=()):
            owner=loading.LoadingEntry(module.Mod(),session)
            owner.prepare(N(kind='title'));owner.bind(first,preparing=True)
            entry.install.assert_called_once();entry.poll.assert_not_called()
            from expedition33 import RuntimeQueryError
            entry.install.side_effect=RuntimeQueryError('READ_FAILED')
            owner.bind(first,preparing=True) # Pure pre-build read may be sampled again.
            self.assertIs(owner.entry,entry)
            entry.state='prepared'
            entry.install.side_effect=RuntimeQueryError('DESCRIPTOR_IDENTITY_CHANGED')
            owner.bind(first,preparing=True)
            self.assertIs(owner.entry,entry);self.assertEqual(entry.state,'prepared')
            entry.close.assert_not_called();self.assertEqual(factory.call_count,1)
            def partial_failure():
                entry.state='building'
                raise RuntimeQueryError('READ_FAILED')
            entry.install.side_effect=partial_failure
            with self.assertRaises(RuntimeQueryError):owner.bind(first,preparing=True)
            entry.install.side_effect=None
            self.assertEqual(entry._expected_controller,first.controller)
            entry.state='attached';entry.retire_world.return_value='pending'
            owner.bind(second,preparing=True)
            self.assertIs(owner.entry,entry);self.assertEqual(factory.call_count,1)
            with self.assertRaises(RuntimeError):owner.close()
            entry.retire_world.return_value='ack'
            owner.observe_title(N())
            self.assertTrue(owner.released)
            owner.close();scope.close.assert_called_once()

    def test_world_builder_proves_owned_trees_during_bootstrap_without_save(self):
        module=self.load('E33WorldBuilder')
        loading=importlib.import_module(module.__name__+'.loading_ui')
        owner=loading.LoadingUI.__new__(loading.LoadingUI)
        previous=object();owner.mod=N(session=previous,help_minimized=False);owner.scope=N(pid=7)
        catalog=Mock();hud=Mock();proofs=(Mock(),Mock());context=N(kind='world')
        with patch.object(importlib.import_module(module.__name__+'.library'),'Library'), \
             patch.object(importlib.import_module(module.__name__+'.hud'),'BuilderHUD',return_value=hud), \
             patch.object(importlib.import_module(module.__name__+'.catalog_menu'),'CatalogMenu',return_value=catalog), \
             patch.object(loading,'ReadBatch'),patch.object(loading,'prepare_panel_metadata'), \
             patch.object(loading,'OwnedUiProof',side_effect=proofs):
            owner.prepare(context)
        for proof,panel in zip(proofs,(catalog,hud)):
            proof.verify.assert_called_once_with(panel,context,preparing=True)
        self.assertIs(owner.mod.session,previous)

    def test_world_builder_loading_handoff_borrows_the_hosts_reader(self):
        module=self.load('E33WorldBuilder')
        loading=importlib.import_module(module.__name__+'.loading_ui')
        from expedition33._reader import ReadBatch,_active
        parent=ReadBatch(7,share=True)
        owner=loading.LoadingUI.__new__(loading.LoadingUI)
        owner.scope=N(pid=7);owner.context=object();owner.bound=None
        owner.catalog=object();owner.hud=object()
        seen=[]
        owner.proofs=(N(verify=lambda *a,**kw:seen.append(_active.get())),)*2
        token=_active.set(parent)
        try:
            with patch('expedition33._reader.subprocess.Popen',side_effect=AssertionError('must borrow')):
                owner.bind(N(signature=('world',)),preparing=True)
            self.assertEqual(seen,[parent,parent]);self.assertFalse(parent._closed)
        finally:_active.reset(token);parent.close()


if __name__=='__main__':unittest.main()
