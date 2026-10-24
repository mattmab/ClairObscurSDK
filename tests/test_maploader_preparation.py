import importlib.util,json,os,pathlib,sys,tempfile,unittest
from unittest.mock import Mock,patch
ROOT=pathlib.Path(__file__).resolve().parents[1]/'mods/WorldBuilderMapLoader'
spec=importlib.util.spec_from_file_location('maploader_preparation',ROOT/'mod.py',submodule_search_locations=[str(ROOT)])
loader=importlib.util.module_from_spec(spec);sys.modules[spec.name]=loader;spec.loader.exec_module(loader)
from maploader_preparation.prepared_maps import PreparedMapStore
from expedition33.worldbuilder_maps import FORMAT

def data(name='test'):
    return dict(format=FORMAT,version=1,name=name,world='/Game/Test.Test',objects=[dict(id='a'*32,kind='mesh',asset='/Game/M.M',transform=[0,0,0,1,0,0,0,0,1,1,1,0])],assets=['/Game/M.M'])
class PreparationTests(unittest.TestCase):
    def test_menu_bounds_long_error_and_supplementary_unicode_names(self):
        from contextlib import nullcontext
        from types import SimpleNamespace
        model=loader.Mod();model.current={'world':'/Game/Test.Test'}
        model.assignments=SimpleNamespace(values={})
        model.message='Read failed: '+('diagnostic '*2000)
        model.rows=[{'id':'a'*32,'name':'\U0001f600'*5000,'count':1}];model.offset=0
        model.panel=Mock(title=object(),detail=object(),labels=[object() for _ in range(12)])
        model.panel.paint_batch.return_value=nullcontext()
        model._paint()
        for call in model.panel.set_text.call_args_list:
            self.assertLessEqual(len(call.args[1].encode('utf-16-le'))//2,4095)

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=pathlib.Path(self.temp.name)
        self.store=PreparedMapStore(self.root);self.key='b'*32;self.path=self.store.file(self.key);self.path.write_text(json.dumps(data()))
    def test_unchanged_hit_avoids_parse_and_returns_defensive_copy(self):
        first=self.store.read(self.key);first['objects'][0]['transform'][4]=99
        with patch('maploader_preparation.prepared_maps.json.loads',side_effect=AssertionError('duplicate parse')):
            second=self.store.read(self.key)
        self.assertEqual(second['objects'][0]['transform'][4],0);self.assertEqual(self.store.stats['hits'],1)
    def test_prepared_plan_reuses_immutable_spawn_work(self):
        self.store.prepare([self.key]);plan=self.store.read_plan(self.key,'/Game/Test.Test')
        self.assertEqual(plan.assets,('/Game/M.M',))
        with patch('maploader_preparation.prepared_maps.SpawnPlan',side_effect=AssertionError('duplicate planning')):
            self.assertIs(self.store.read_plan(self.key),plan)
        with self.assertRaises(AttributeError):plan.rows[0].asset='other'
        self.assertEqual(self.store.stats['plans'],1)
    def test_plan_invalidation_rechecks_same_timestamp_bytes_and_wrong_world(self):
        original=self.store.read_plan(self.key);before=self.path.stat()
        edited=data('tEst');edited['objects'][0]['transform'][4]=9
        self.path.write_text(json.dumps(edited));os.utime(self.path,ns=(before.st_atime_ns,before.st_mtime_ns))
        fresh=self.store.read_plan(self.key)
        self.assertIsNot(original,fresh);self.assertEqual(fresh.rows[0].transform[4],9)
        with self.assertRaisesRegex(ValueError,'same game level'):self.store.read_plan(self.key,'/Game/Other.Other')
    def test_removed_file_invalidates_prepared_plan(self):
        self.store.read_plan(self.key);self.path.unlink()
        with self.assertRaises(FileNotFoundError):self.store.read_plan(self.key)
        self.assertFalse(self.store._plans)
    def test_same_size_same_mtime_edit_invalidates_by_digest(self):
        self.store.read(self.key);before=self.path.stat();self.path.write_text(json.dumps(data('tEst')));os.utime(self.path,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.assertEqual(self.store.read(self.key)['name'],'tEst');self.assertEqual(self.store.stats['invalidated'],1)
    def test_deleted_file_does_not_serve_stale_cache(self):
        self.store.read(self.key);self.path.unlink()
        with self.assertRaises(FileNotFoundError):self.store.read(self.key)
        self.assertFalse(self.store._prepared)
    def test_malformed_edit_does_not_serve_stale_cache(self):
        self.store.read(self.key);self.path.write_text('{}')
        with self.assertRaises(ValueError):self.store.read(self.key)
        self.assertFalse(self.store._prepared)
    def test_cache_eviction_and_preparation_budget(self):
        self.store.MAX_CACHE_ENTRIES=1
        second='c'*32;self.store.file(second).write_text(json.dumps(data()))
        self.store.read(self.key);self.store.read(second);self.assertEqual(list(self.store._prepared),[second])
        self.store.MAX_CACHE_BYTES=1
        result=self.store.prepare([self.key,second]);self.assertEqual(result['skipped'],2)
    def test_oversized_read_rejected(self):
        self.store.MAX_FILE_BYTES=1
        with self.assertRaisesRegex(ValueError,'too large'):self.store.read(self.key)
    def test_startup_prepares_only_synthetic_assignments_without_engine(self):
        settings=self.root/'settings';maps=settings/'E33WorldBuilder/maps';maps.mkdir(parents=True)
        (maps/self.path.name).write_bytes(self.path.read_bytes());assignment=settings/'WorldBuilderMapLoader/assignments.json';assignment.parent.mkdir(parents=True)
        assignment.write_text(json.dumps(dict(version=1,maps={'/Game/Test.Test':self.key})))
        mod=loader.Mod()
        with patch.object(loader,'settings_dir',return_value=settings),patch.object(loader,'MapRuntime',side_effect=AssertionError('engine access')):
            mod.prepare_startup(object())
        self.assertIsNone(mod.session);self.assertIsNone(mod.runtime);self.assertEqual(mod._startup_store.stats['prepared'],1)
        self.assertNotIn(self.key,str(mod.timing_status()))
    def test_legacy_preparation_does_not_migrate_settings_early(self):
        settings=self.root/'settings';legacy=settings/'E33MapOverlays/assignments.json';legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps(dict(version=1,maps={})));before=legacy.read_bytes();mod=loader.Mod()
        with patch.object(loader,'settings_dir',return_value=settings):mod.prepare_startup(object())
        self.assertEqual(legacy.read_bytes(),before);self.assertFalse((settings/'WorldBuilderMapLoader/assignments.json').exists())
    def test_enable_rereads_settings_and_reuses_prepared_store(self):
        settings=self.root/'settings';assignment=settings/'WorldBuilderMapLoader/assignments.json';assignment.parent.mkdir(parents=True)
        assignment.write_text(json.dumps(dict(version=1,maps={})));mod=loader.Mod();session=Mock()
        with patch.object(loader,'settings_dir',return_value=settings),patch.object(loader,'MapRuntime'):
            mod.prepare_startup(object());prepared=mod._startup_store
            assignment.write_text(json.dumps(dict(version=1,maps={'/Game/Test.Test':'c'*32})))
            mod.check_legacy=lambda:None;mod.enable(session)
        self.assertIs(mod.store,prepared);self.assertEqual(mod.assignments.values['/Game/Test.Test'],'c'*32)
    def test_wrong_world_still_rejected_before_actor_load(self):
        mod=loader.Mod();mod.current={'world':'/Game/Other.Other'};mod.store=self.store;mod.check_legacy=lambda:None
        mod.runtime=Mock();mod.runtime.profile={};mod.assignments=Mock();mod.status=lambda:None
        mod.apply(self.key);mod.runtime.load.assert_not_called();self.assertTrue(mod.visits.attempted)
        self.assertIn('same game level',mod.message)
    def test_missing_gap_and_pawn_change_do_not_clear_attempted(self):
        v=loader.Visits();ctx=dict(world='/Game/Test.Test',visit=[1,2,3],pawn=[4,5,6],ready=True)
        self.assertFalse(v.observe(ctx,0));self.assertFalse(v.observe(ctx,1));self.assertTrue(v.observe(ctx,2));v.attempted=True
        self.assertFalse(v.observe(None,3));self.assertFalse(v.observe(dict(ctx,pawn=[4,6,7]),4));self.assertFalse(v.observe(ctx,9))
if __name__=='__main__':unittest.main()


class PassiveContextTests(unittest.TestCase):
    def mod(self):
        from types import SimpleNamespace
        mod=loader.Mod();mod.session=SimpleNamespace(pid=123)
        mod.runtime=Mock(started=False);mod.assignments=SimpleNamespace(values={})
        mod._context_monitor=Mock();mod._context_monitor.snapshot.return_value=None
        return mod

    def test_pending_snapshot_never_scans_or_retires_world(self):
        mod=self.mod();mod.current={'visit':[1,2,3]};mod.visits=Mock()
        with patch.object(loader,'context',side_effect=AssertionError('owner-thread scan')):
            mod.poll()
        mod.visits.observe.assert_not_called();mod.runtime.close.assert_not_called()
        self.assertEqual(mod.current,{'visit':[1,2,3]})

    def test_completed_snapshot_is_defensively_copied_and_observed(self):
        from types import SimpleNamespace
        from maploader_preparation.context_observer import MapContext
        mod=self.mod();value=MapContext('/Game/Test.Test',(1,2,3),(4,5,6),True)
        mod._context_monitor.snapshot.return_value=SimpleNamespace(admission=value)
        mod.visits=Mock();mod.visits.observe.return_value=False
        with patch.object(loader,'context',side_effect=AssertionError('owner-thread scan')):
            mod.poll()
        self.assertEqual(mod.current['visit'],[1,2,3])
        mod.current['visit'][0]=99
        self.assertEqual(value.visit,(1,2,3))
        mod.visits.observe.assert_called_once()

    def test_worker_uses_pid_only_and_freezes_context(self):
        from maploader_preparation.context_observer import ContextObserver
        import maploader_preparation.context_observer as source
        value=dict(world='/Game/Test.Test',visit=[1,2,3],pawn=[4,5,6],ready=True)
        with patch.object(source,'context',return_value=value) as observe:
            result=ContextObserver(123).observe()
        self.assertEqual(vars(observe.call_args.args[0]),{'pid':123})
        value['visit'][0]=99
        self.assertEqual(result.visit,(1,2,3))

    def test_disable_retains_pending_worker_owner(self):
        mod=self.mod();mod._context_monitor.close.return_value=False
        monitor=mod._context_monitor;mod.close_menu=Mock()
        with self.assertRaisesRegex(RuntimeError,'cleanup pending'):mod.disable()
        mod.close_menu.assert_not_called();mod.runtime.close.assert_not_called()
        self.assertIs(mod._context_monitor,monitor);self.assertIsNotNone(mod.session)
        monitor.close.assert_called_once_with(timeout=2.)
        mod.poll();monitor.snapshot.assert_not_called()
        monitor.close.return_value=True;mod.disable()
        mod.close_menu.assert_called_once();mod.runtime.close.assert_called_once()
        self.assertIsNone(mod._context_monitor);self.assertIsNone(mod.session)

    def test_prepare_disable_waits_for_inflight_read_before_any_game_cleanup(self):
        import threading
        from expedition33.admission_monitor import ReadOnlyAdmissionMonitor
        entered=threading.Event();release=threading.Event()
        class Observer:
            def observe(self):entered.set();release.wait(2);return None
            def close(self):pass
        mod=self.mod();mod.close_menu=Mock()
        monitor=ReadOnlyAdmissionMonitor(Observer,interval=1.);mod._context_monitor=monitor
        self.addCleanup(lambda:(release.set(),monitor.close(timeout=2)))
        self.assertTrue(entered.wait(1))
        timer=threading.Timer(.05,release.set);timer.start();self.addCleanup(timer.join)
        self.assertIs(mod.prepare_disable(),True)
        self.assertTrue(monitor.closed.is_set());self.assertIsNone(mod._context_monitor)
        mod.close_menu.assert_not_called();mod.runtime.close.assert_not_called()
        mod.poll();mod.disable()
        mod.close_menu.assert_called_once();mod.runtime.close.assert_called_once()

    def test_invalid_worker_shutdown_ack_never_starts_disable(self):
        mod=self.mod();mod.close_menu=Mock();mod._context_monitor.close.return_value=None
        with self.assertRaisesRegex(RuntimeError,'Invalid map observer shutdown ACK'):mod.disable()
        mod.close_menu.assert_not_called();mod.runtime.close.assert_not_called()
