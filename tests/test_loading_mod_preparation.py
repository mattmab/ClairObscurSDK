import importlib
from concurrent.futures import Future
from types import SimpleNamespace as N
import unittest
from unittest.mock import Mock,MagicMock,patch
import test_firstparty_startup as package_fixture


class LoadingModPreparationTests(unittest.TestCase):
    def load(self,name):
        module,_=package_fixture.Tests.load(self,name)
        return module

    def test_flight_result_from_another_world_is_discarded(self):
        module=self.load('ContinentFlight')
        loading=importlib.import_module(module.__name__+'.loading')
        mod=module.Mod();owner=loading.LoadingFlight(mod,N(pid=7))
        title=N(signature=('title',));first=N(signature=('world',1));second=N(signature=('world',2))
        with patch.object(loading,'prepare_static',return_value=N(_entries={})), patch('expedition33._reader.ReadBatch'):
            owner.prepare(title)
        future=Future();worker=Mock();worker.submit.return_value=future
        with patch.object(loading,'ThreadPoolExecutor',return_value=worker):
            owner.bind(first,preparing=True)
            self.assertIsNone(mod._loading_flight)
            owner.bind(second,preparing=True)
            future.set_result(('copied snapshot','copied schemas'))
            owner.bind(second,preparing=True)
            self.assertIsNone(mod._loading_flight)
            self.assertEqual(worker.submit.call_count,1)
        owner.close()
        worker.shutdown.assert_called_once_with(wait=False,cancel_futures=True)

    def test_flight_read_worker_transfers_once_and_rewarms_after_retirement(self):
        module=self.load('ContinentFlight')
        loading=importlib.import_module(module.__name__+'.loading')
        mod=module.Mod();owner=loading.LoadingFlight(mod,N(pid=7));reader=MagicMock()
        with patch.object(loading,'prepare_static',return_value=N(_entries={})), patch('expedition33._reader.ReadBatch',return_value=reader) as factory:
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
            owner.prepare(N());owner.bind(first,preparing=True)
            entry.install.assert_called_once();entry.poll.assert_not_called()
            from expedition33 import RuntimeQueryError
            entry.install.side_effect=RuntimeQueryError('READ_FAILED')
            owner.bind(first,preparing=True) # Pure pre-build read may be sampled again.
            self.assertIs(owner.entry,entry)
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


if __name__=='__main__':unittest.main()
