import sys, importlib.util, unittest
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
from concurrent.futures import Future
from unittest.mock import Mock, patch
from expedition33.picto_drafts import PictoDraft, preview_stats
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('picto_control_test',ROOT/'mods/PictoEditor/mod.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class Controls(unittest.TestCase):
    def test_clear_confirmation_is_bound_to_selection_and_bulk_waits(self):
        e=self.editor();e.paint_value=Mock();e.text=Mock();e.status_label='status'
        e.pid=123;e.baselines=Mock();e.baselines.targets.return_value={};e.scope=Mock();e.operation=nullcontext;e.progression_catalog=Mock();e.refresh_current=Mock();e.ownership=Mock();e.panel=None
        e.definition_id='Cheater';e.preferences=Mock();e.preferences.profiles={'Cheater':{}};e.restore_queue=[('Cheater','cost',None,2),('Other','level',None,26)]
        e.drafts={'Cheater':object(),'Other':object()};e.ownership_drafts={'Cheater':object()}
        with patch('expedition33.picto_saved_changes.clear_saved') as clear, patch('expedition33.picto_restore.restore',return_value={'missing':[]}) as restore:
            e.activate(12);clear.assert_not_called()
            e.definition_id='Other';e.activate(12);clear.assert_not_called()
            e.definition_id='Cheater';e.activate(12);clear.assert_not_called()
            e.activate(12);clear.assert_called_once_with(e.preferences,'Cheater')
            self.assertEqual(e.restore_queue,[('Other','level',None,26)])
            self.assertNotIn('Cheater',e.drafts);self.assertIn('Other',e.drafts)
            e.tools_page=True;e.unlock_bulk=object();e.activate(12)
            self.assertEqual(clear.call_count,1)
            e.unlock_bulk=None;e.activate(12);e.activate(12)
            clear.assert_called_with(e.preferences,None)
            self.assertEqual(e.restore_queue,[]);self.assertEqual(e.drafts,{})

    def test_mass_level_uses_fresh_preflight_after_failed_selection_read(self):
        e=self.editor();e.tools_page=True;e.paint_value=Mock();e.scope=SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(picto_level_batch_protocol=0)));e.preferences=Mock()
        e.operation=nullcontext;e.progression_catalog=Mock(return_value='fresh')
        e.refresh_future=Future();e.refresh_future.set_exception(RuntimeError('recycled view'))
        with patch('expedition33.picto_bulk.PictoBulkJob') as create,patch.object(mod.log,'warning'):
            e.activate(7)
        create.assert_called_once_with(e.scope,'fresh','level',33,e.preferences)
        self.assertIsNone(e.refresh_future)

    def test_progression_discovery_excludes_unbounded_transient_instances(self):
        e=mod.StockEditor.__new__(mod.StockEditor);e.pid=123
        with patch.object(mod,'capture_matching',return_value='fresh') as capture:
            self.assertEqual(e.progression_catalog(),'fresh')
        classes=capture.call_args.kwargs['classes']
        self.assertIn('BP_ItemUpgradeSystem_C',classes)
        self.assertNotIn('BP_PassiveEffectInstance_C',classes)
        self.assertNotIn('BP_ItemInstance_Gear_Pictos_C',classes)

    def test_menu_discovery_uses_authoritative_owned_items(self):
        e=mod.StockEditor.__new__(mod.StockEditor);e.pid=123
        with patch.object(mod,'capture_matching',return_value='dependencies') as capture, \
             patch('expedition33.picto_inventory.owned_pictos',return_value=('owned-catalog',{})) as owned:
            self.assertEqual(e.discover(),'owned-catalog')
        owned.assert_called_once_with(123,catalog='dependencies')
        self.assertNotIn('BP_PassiveEffectInstance_C',capture.call_args.kwargs['classes'])

    def bulk_preview_editor(self):
        e=self.editor();e.tools_page=True;e.paint_value=Mock()
        e.scope=SimpleNamespace(_session=SimpleNamespace(_transport=SimpleNamespace(picto_batch_protocol=0)))
        e.ownership=SimpleNamespace(rows={'A':{'normal':True},'B':{'normal':True},
            'TEST':{'normal':False}},owned={'A':object(),'TEST':object()})
        return e

    def test_remove_all_preview_excludes_experimental_and_intent_switch_requires_confirmation(self):
        e=self.bulk_preview_editor()
        with patch('expedition33.picto_transactions.UnlockTransaction') as create:
            e.activate(3)
            self.assertEqual(e.unlock_confirm,1);self.assertFalse(e.unlock_confirm_desired)
            e.activate(9)
            self.assertEqual(e.unlock_confirm,1);self.assertTrue(e.unlock_confirm_desired)
            e.activate(3)
            self.assertEqual(e.unlock_confirm,1);self.assertFalse(e.unlock_confirm_desired)
            create.assert_not_called();self.assertIsNone(e.unlock_bulk)
            e.activate(6);self.assertIsNone(e.unlock_confirm)
            create.assert_not_called()

    def test_remove_all_second_confirmation_starts_only_requested_direction(self):
        e=self.bulk_preview_editor();e.submit_read=Mock()
        with patch('expedition33.picto_transactions.UnlockTransaction') as create, \
                patch('expedition33.picto_transactions.BulkUnlockTransaction') as bulk:
            e.activate(3);create.assert_not_called()
            e.activate(3)
            create.assert_called_once_with(e.ownership,e.submit_read,desired=False)
            bulk.assert_called_once_with(create.return_value)
            bulk.return_value.start.assert_called_once()
            self.assertIsNone(e.unlock_confirm)
            e.activate(6);bulk.return_value.stop.assert_called_once()

    def test_busy_ownership_batch_blocks_property_and_bulk_mutations_but_allows_filters(self):
        e=self.editor();e.unlock_bulk=Mock();e.catalog_page='normal'
        e.catalog_selection='Cheater';e.paint_value=Mock();e.select_catalog=Mock()
        e.catalog_view=SimpleNamespace(filter='owned',experimental=False)
        e.native_catalog=SimpleNamespace(actions={13:'filter:locked'},mapping={},reset=Mock())
        for index in (4,5,6,7,8,9):e.activate(index)
        self.assertFalse(e.drafts);self.assertEqual(e.mode,'stat')
        e.activate(13)
        self.assertEqual(e.catalog_view.filter,'locked');e.native_catalog.reset.assert_called_once()
        e.tools_page=True
        with patch('expedition33.picto_bulk.PictoBulkJob') as create:
            e.activate(7);e.activate(8);e.activate(3);e.activate(9)
            create.assert_not_called()
        e.activate(6);e.unlock_bulk.stop.assert_called_once()

    def test_persist_removed_only_after_verified_transaction_result(self):
        for state in ('Removed','Already Absent','Failed','Timed Out'):
            e=self.editor();e.unlock_reported=None;e.panel=None
            e.unlock_transaction=SimpleNamespace(identity='Cheater',state=state,busy=False,
                desired=False,owned={},error=None,timings={},poll=Mock())
            e.ownership=SimpleNamespace(owned={'Cheater':object()})
            e.preferences=Mock(profiles={});e.ownership_ui_refresh=Mock();e.paint_value=Mock()
            e.poll_unlock()
            if state in ('Removed','Already Absent'):
                self.assertTrue(e.preferences.remember.called)
                self.assertTrue(all(c.args==('Cheater','owned',False) for c in e.preferences.remember.call_args_list))
            else:e.preferences.remember.assert_not_called()

    def test_close_persists_removal_only_when_authoritative_readback_is_absent(self):
        for owned in ({},{'Cheater':object()}):
            e=self.editor();reply=Future();reply.set_result(owned)
            e.unlock_transaction=SimpleNamespace(dispatched=True,state='Unlocking',desired=False,
                future=reply,identity='Cheater',poll=Mock())
            e.preferences=Mock();e.native_catalog=None;e.refresh_future=None
            e.operation=nullcontext;e.card_layout=Mock();e.refresh_worker=Mock()
            e.main_reader=Mock();e.observers=[];e.attachment=None;e.scope=Mock()
            with patch.object(mod.log,'warning'):e.close()
            if owned:e.preferences.remember.assert_not_called()
            else:e.preferences.remember.assert_called_once_with('Cheater','owned',False)
            e.unlock_transaction.poll.assert_not_called()

    def test_retained_mastery_mode_without_passive_cannot_stage_adjustments(self):
        e=self.editor();e.mode='mastery';e.extra={'mastered':True,'steps':4}
        for index in (4,5):
            e.activate(index)
            self.assertFalse(e.draft().changes)

    def test_apply_without_passive_retains_combined_draft_without_partial_write(self):
        e=self.apply_editor();e.extra.pop('source')
        e.draft().stage(('stat',1),.6,.7)
        e.draft().stage(('mastery',None),False,True)
        with patch('expedition33.picto_progression.change') as change:e.activate(6)
        change.assert_not_called();self.assertFalse(e.calls)
        self.assertEqual(e.draft().changes,{('stat',1):.6,('mastery',None):False})
        self.assertEqual(e.rendered['status'],'Passive instance unavailable; draft retained')
        e.preferences.remember_many.assert_not_called()

    def test_definition_cost_and_shared_mastery_render_without_live_passive(self):
        e=self.editor();e.extra={'mastered':True,'steps':4}
        e.catalog_metadata={'Cheater':{'cost':5}}
        e.ownership=SimpleNamespace(rows={'Cheater':{'name':'Display Picto Name'}})
        e.paint_value()
        self.assertEqual(e.rendered['cost'],'Lumina cost: 5')
        self.assertEqual(e.rendered['mastery'],'Mastery: Mastered')
        self.assertIn('Display Picto Name',e.rendered['header'])
        self.assertNotIn('unavailable',e.rendered['cost'].lower())
        for index in (8,9):
            e.activate(index)
            self.assertEqual(e.mode,'stat');self.assertFalse(e.draft().changes)

    def test_disk_save_failure_blocks_next_bulk_dispatch(self):
        e=self.editor();e.unlock_reported=None
        e.unlock_transaction=SimpleNamespace(identity='Cheater',state='Unlocked',busy=False,desired=True)
        e.unlock_bulk=Mock();e.preferences=Mock()
        e.preferences.remember.side_effect=OSError('disk full')
        with self.assertRaisesRegex(OSError,'disk full'):e.poll_unlock()
        e.unlock_bulk.poll.assert_not_called()
        self.assertIsNone(e.unlock_reported)
        e.preferences.remember.assert_called_once_with('Cheater','owned',True)

    def test_close_reconciles_dispatched_unlock_without_new_mutation(self):
        e=self.editor();reply=Future();reply.set_result({'Cheater':object()})
        e.unlock_transaction=SimpleNamespace(dispatched=True,state='Unlocking',desired=True,
            future=reply,identity='Cheater',poll=Mock())
        e.preferences=Mock();e.native_catalog=None;e.refresh_future=None
        e.operation=nullcontext;e.card_layout=Mock();e.refresh_worker=Mock()
        e.main_reader=Mock();e.observers=[];e.attachment=None;e.scope=Mock()
        e.submit_read=Mock()
        e.close()
        e.preferences.remember.assert_called_once_with('Cheater','owned',True)
        e.unlock_transaction.poll.assert_not_called();e.submit_read.assert_not_called()
        self.assertEqual(e.state,'closed')

    def test_close_cancels_undispatched_unlock_without_persisting(self):
        e=self.editor();pending=Future()
        e.unlock_transaction=SimpleNamespace(dispatched=False,state='Unlocking',
            future=pending,identity='Cheater',poll=Mock())
        e.preferences=Mock();e.native_catalog=None;e.refresh_future=None
        e.operation=nullcontext;e.card_layout=Mock();e.refresh_worker=Mock()
        e.main_reader=Mock();e.observers=[];e.attachment=None;e.scope=Mock()
        e.close()
        self.assertTrue(pending.cancelled());e.preferences.remember.assert_not_called()
        e.unlock_transaction.poll.assert_not_called()

    def test_disable_restores_before_readers_close_and_keeps_preferences(self):
        e=self.editor();e.native_catalog=None;e.refresh_future=None
        e.operation=nullcontext;e.card_layout=Mock();e.refresh_worker=Mock()
        e.main_reader=Mock();e.observers=[];e.attachment=None;e.scope=Mock()
        e.preferences=Mock();e.restore_originals=Mock(side_effect=lambda:e.main_reader.close.assert_not_called())
        e.close(restore_originals=True)
        e.restore_originals.assert_called_once();e.main_reader.close.assert_called_once()
        self.assertFalse(e.preferences.mock_calls)

    def test_disable_reports_failed_restore_but_finishes_cleanup(self):
        e=self.editor();e.native_catalog=None;e.refresh_future=None
        e.operation=nullcontext;e.card_layout=Mock();e.refresh_worker=Mock()
        e.main_reader=Mock();e.observers=[];e.attachment=None;e.scope=Mock()
        e.restore_originals=Mock(side_effect=RuntimeError('uncertain'))
        with patch.object(mod.log,'exception'),self.assertRaisesRegex(RuntimeError,'disable restoration incomplete'):
            e.close(restore_originals=True)
        e.restore_originals.assert_called_once();e.main_reader.close.assert_called_once()
        self.assertEqual(e.state,'closed')

    def test_disable_limits_rollback_to_configured_fields(self):
        e=self.editor();e.pid=1;e.scope=object();e.panel=None;e.restore_queue=[]
        e.operation=nullcontext;e.progression_catalog=Mock(return_value='catalog')
        e.preferences=SimpleNamespace(profiles={'Cheater':{'level':20},'Other':{'multipliers':{'6':.2}}})
        original={'owned':True,'level':33,'multipliers':{'6':0.},'stat_keys':[1],
                  'multiplier_keys':[1,6],'cost':40,'mastered':True,'mastery_steps':4}
        e.baselines=Mock();e.baselines.targets.return_value={'Cheater':dict(original),'Other':dict(original)}
        with patch('expedition33.picto_restore.restore',return_value={'missing':[],'applied':[]}) as restore:
            e.restore_originals()
        targets=restore.call_args.args[1]
        self.assertEqual(targets['Cheater'],{'level':33})
        self.assertEqual(set(targets['Other']),{'multipliers','stat_keys','multiplier_keys'})

    def test_removal_is_staged_until_apply_and_preserves_property_drafts(self):
        e=self.editor();e.activate(4);draft=e.drafts['Cheater']
        e.catalog_page='normal';e.catalog_selection='Cheater';e.paint_value=Mock()
        e.ownership=Mock();e.preferences=Mock();e.ownership_ui_refresh=Mock();e.panel=object()
        e.activate(11)
        self.assertEqual(e.ownership_drafts,{'Cheater':(True,False)})
        e.ownership.set_owned.assert_not_called();e.preferences.remember_many.assert_not_called()
        e.activate(11);self.assertFalse(e.ownership_drafts)
        e.ownership.set_owned.assert_not_called()
        e.activate(11);e.activate(6)
        e.ownership.set_owned.assert_called_once_with('Cheater',False,expected=True)
        self.assertIs(e.drafts['Cheater'],draft)
        self.assertEqual(draft.changes,{('stat',1):.6})
        self.assertFalse(e.ownership_drafts)
        saved=e.preferences.remember_many.call_args.args[1]
        self.assertIn(('owned',False,None),saved)
        self.assertIn(('stat',.7,1),saved)  # Current value, not uncommitted draft.

    def test_unlock_refresh_failure_leaves_actual_filter_actions_available(self):
        from expedition33.picto_catalog import CatalogView,NativeCatalog
        e=self.editor();e.state='active';e.error=None;e.catalog_page='normal'
        e.catalog_selection='Cheater';e.catalog_future=None;e.unlock_reported=None
        e.unlock_transaction=SimpleNamespace(identity='Cheater',state='Unlocked',busy=False,desired=True,
            owned={'Cheater':(e.selection,33)},error=None,timings={},poll=Mock())
        e.ownership=SimpleNamespace(owned={});e.preferences=Mock(profiles={})
        e.panel=None
        e.ownership_ui_refresh=Mock(side_effect=RuntimeError('stale menu widget'))
        e.next_scan=float('inf');e._renew_at=float('inf');e.lumina_ui_pending=False
        e.restore_queue=[];e.restore_error=None;e.refresh_future=Future()
        e.paint_value=Mock();e.call=Mock(return_value=0.)
        e.observers=[SimpleNamespace(state='active',read=Mock(return_value=[]))]
        view=CatalogView({'Cheater':{'name':'Cheater','normal':True},
            'Locked':{'name':'Locked','normal':True}}, {'Cheater':object()})
        n=NativeCatalog(e);n.view=view;n.extent=object();n.scroll=object();n.poll=Mock();n.build_ready=True
        n.actions={12:'filter:all',13:'filter:locked'}
        e.native_catalog=n;e.catalog_view=view
        with self.assertLogs(mod.log,level='ERROR'):e._poll()
        self.assertEqual(e.state,'active');self.assertIsNone(e.error)
        self.assertIn('stale menu widget',e.bulk_message)
        e.activate_catalog(13);self.assertEqual(view.ids,['Locked'])
        self.assertEqual(e.catalog_selection,'Locked')
        e.activate_catalog(12);self.assertEqual(len(view.ids),2)

    def test_locked_catalog_disables_inventory_editor_controls(self):
        e=self.editor();e.catalog_page='normal';e.selection=None
        e.buttons=list(range(12));e.defer_layout=Mock();e.flush_layout=Mock();e._paint_value=Mock()
        e.paint_value()
        self.assertEqual(e.defer_layout.call_count,10)
        self.assertTrue(all(c.kwargs=={'bInIsEnabled':False} for c in e.defer_layout.call_args_list))
        e.defer_layout.reset_mock();e.paint_value();e.defer_layout.assert_not_called()
        e.selection=object();e.paint_value()
        self.assertEqual(e.defer_layout.call_count,10)
        self.assertTrue(all(c.kwargs=={'bInIsEnabled':True} for c in e.defer_layout.call_args_list))

    def test_catalog_selection_clears_old_values_but_retains_per_picto_draft(self):
        e=self.editor();e.activate(4);saved=e.drafts['Cheater']
        e.paint_value=Mock();e.catalog_page='normal'
        e.select_catalog('LockedPicto')
        self.assertEqual(e.catalog_selection,'LockedPicto')
        self.assertEqual(e.definition_id,'LockedPicto')
        self.assertIsNone(e.selection);self.assertIsNone(e.level)
        self.assertEqual(e.stats,{});self.assertEqual(e.extra,{})
        self.assertIs(e.drafts['Cheater'],saved)
        self.assertEqual(saved.changes,{('stat',1):.6})
        e.activate(5);self.assertEqual(len(e.drafts),1)

    def test_inflight_old_selection_cannot_replace_current_catalog_selection(self):
        e=self.editor();e.catalog_page='normal';e.catalog_selection='New'
        e.planner=Mock();e.card_layout=Mock();selected=e.selection
        stale=(object(),object(),object(),object(),None,{'catalog_identity':'Old'},.1)
        e.accept_observation(stale)
        self.assertIs(e.selection,selected)
        e.planner.adopt_observations.assert_not_called();e.card_layout.apply.assert_not_called()

    def test_catalog_snapshot_and_editor_use_same_accepted_inventory_identity(self):
        e=self.editor();e.catalog_page='normal';e.catalog_selection='Other'
        e.planner=Mock();e.card_layout=Mock();e.paint_value=Mock()
        item=SimpleNamespace(pid=1,index=20,serial=21,address=22)
        fields={'ItemDefinitionID':'Other','CurrentLevel':32,
            'CurrentStats':SimpleNamespace(items={1:3500}),
            'BaseStatsMultipliers':SimpleNamespace(items={1:1.})}
        values=SimpleNamespace(types={(1,k):None for k in fields},
            values={(1,k):v for k,v in fields.items()},errors={})
        e.accept_observation((object(),object(),object(),item,values,{'catalog_identity':'Other'},.01))
        self.assertIs(e.selection,item);self.assertEqual(e.definition_id,e.catalog_selection)
        self.assertEqual(e.level,32);self.assertEqual(e.stats,{1:3500})
        e.paint_value.assert_called_once()

    def test_action_failure_does_not_stop_next_filter_or_future_polls(self):
        from expedition33.picto_catalog import CatalogView, NativeCatalog
        e=self.editor();e.state='active';e.error=None;e.catalog_page='normal'
        e.catalog_selection='locked';e.catalog_future=None;e.poll_unlock=Mock()
        e.next_scan=float('inf');e._renew_at=float('inf');e.lumina_ui_pending=False
        e.restore_queue=[];e.restore_error=None;e.refresh_future=Future()
        e.paint_value=Mock();e.call=Mock(return_value=0.)
        view=CatalogView({'owned':{'name':'Owned','normal':True},'locked':{'name':'Locked','normal':True}}, {'owned':object()})
        n=NativeCatalog(e);n.view=view;n.extent=object();n.scroll=object();n.build_ready=True
        n.poll=Mock();n.actions={12:'filter:all',13:'filter:locked'}
        e.native_catalog=n;e.catalog_view=view
        observer=SimpleNamespace(state='active',read=Mock(side_effect=[[object(),object()],[]]))
        e.observers=[observer]
        def action(index):
            if not getattr(e,'test_failed_once',False):
                e.test_failed_once=True;raise RuntimeError('error=1753, outcome=0')
            e.activate_catalog(12)
        e.activate=action
        with self.assertLogs(mod.log,level='ERROR'):
            e._poll()
        self.assertEqual(e.state,'active');self.assertIsNone(e.error)
        self.assertIn('1753',e.bulk_message)
        e.activate_catalog(13);self.assertEqual(view.ids,['locked'])
        self.assertEqual(e.catalog_selection,'locked')
        e._poll();self.assertEqual(e.state,'active')

    def test_failed_observation_discards_reader_and_pending_layout(self):
        e=mod.StockEditor.__new__(mod.StockEditor)
        e.owner_thread=-1;e.worker_reader=Mock();owner=e.worker_reader
        owner.bind.return_value=nullcontext()
        e.card_layout=SimpleNamespace(pending=object())
        with patch.object(mod.sdk_reader,'active_reader',return_value=None):
            with self.assertRaisesRegex(mod.RuntimeQueryError,'identity changed'):
                with e.operation():
                    raise mod.RuntimeQueryError('identity changed')
        owner.close.assert_called_once()
        self.assertIsNone(e.worker_reader)
        self.assertIsNone(e.card_layout.pending)

    def test_owner_operation_failure_is_not_retried(self):
        e=mod.StockEditor.__new__(mod.StockEditor)
        e.owner_thread=mod.threading.get_ident();e.main_reader=Mock()
        e.main_reader.bind.return_value=nullcontext()
        with patch.object(mod.sdk_reader,'active_reader',return_value=None):
            with self.assertRaises(mod.RuntimeQueryError):
                with e.operation():
                    raise mod.RuntimeQueryError('uncertain mutation')
        e.main_reader.bind.assert_called_once()
        e.main_reader.close.assert_not_called()

    def editor(self):
        e=mod.StockEditor.__new__(mod.StockEditor)
        e.catalog_page=None;e.catalog_selection=None;e.ownership_drafts={}
        e.catalog_request=None;e.ownership=None;e.catalog_metadata={}
        e.unlock_confirm=None;e.unlock_bulk=None;e.unlock_transaction=None
        e.tools_page=False;e.bulk_job=None;e.bulk_level=33;e.bulk_message='Only currently owned Pictos'
        e.selection=SimpleNamespace(pid=1,index=2,serial=3,address=4);e.character=object()
        e.definition_id='Cheater';e.drafts={};e.scaling={33:{1:3765.,6:2485.,8:764.,9:38.},32:{1:3500.,6:2300.,8:700.,9:35.}}
        e.multipliers={1:.7,6:0.,8:1.,9:0.};e.stats={1:2636,6:0,8:764,9:0}
        e.stat_rows={k:(object(),k,n) for k,n in ((1,'Health'),(6,'Defense'),(8,'Speed'),(9,'Crit Rate'))}
        e.stat_key=1;e.timings={};e.mode='stat';e.level=33;e.extra={'cost':35,'steps':246,'threshold':4,'mastered':True,'source':object()}
        e.progression_available=True;e.cost_available=True
        e.level_label='level';e.mastery_label='mastery';e.cost_label='cost';e.adjust_labels=['minus','plus','apply']
        e.header='header';e.value_label='value';e.status_label='status';e.rendered={}
        e.text=lambda label,text:e.rendered.update({label:text})
        e.operation=lambda:self.fail('Draft unexpectedly started a native reader')
        return e
    def test_rows_preview_actual_values_without_mutation(self):
        e=self.editor();e.activate(4)
        self.assertEqual(e.rendered[1],'> Health: 2259*')
        self.assertEqual(e.stats[1],2636);self.assertEqual(e.multipliers[1],.7)
        e.activate(1);e.activate(5)
        self.assertEqual(e.rendered[6],'> Defense: 249*')
        self.assertEqual(e.rendered[1],'Health: 2259*')
        self.assertEqual(len(e.draft().changes),2)
    def test_status_queues_one_message_per_refresh(self):
        e=self.editor();e.clear_message='Starting values restored'
        e.text=Mock(wraps=e.text)
        for _ in range(2):
            e.text.reset_mock();e.paint_value()
            self.assertEqual([c.args[1] for c in e.text.call_args_list if c.args[0]=='status'],
                             ['Starting values restored'])
        e.clear_message='';e.paint_value()
        self.assertEqual(e.rendered['status'],'')
        e.activate(4)
        self.assertEqual(e.rendered['status'],'1 pending edit — select Apply')
    def test_level_recomputes_all_draft_stats(self):
        e=self.editor();e.activate(4);e.activate(7);e.activate(4)
        self.assertEqual(e.rendered[1],'Health: 2100*')
        self.assertEqual(e.rendered[8],'Speed: 700*')
        self.assertEqual(e.rendered['level'],'> Level: 32*')
    def test_switch_picto_retains_separate_drafts(self):
        e=self.editor();e.activate(4);old=e.selection
        e.definition_id='Other';e.selection=SimpleNamespace(pid=1,index=5,serial=6,address=7)
        e.activate(9);e.activate(5)
        e.definition_id='Cheater';e.selection=old;e.activate(0)
        self.assertEqual(e.rendered[1],'> Health: 2259*')
        self.assertEqual(e.rendered['cost'],'Lumina cost: 35')
    def test_revert_to_original_removes_marker(self):
        e=self.editor();e.activate(4);e.activate(5)
        self.assertFalse(e.draft().changes);self.assertNotIn('*',e.rendered[1]);self.assertNotIn('*',e.rendered['header'])
    def test_identity_reuse_discards_old_draft(self):
        e=self.editor();e.activate(4);e.selection.serial=4;e.paint_value()
        self.assertFalse(e.draft().changes)
    def test_cost_mastery_and_stat_coexist(self):
        e=self.editor();e.activate(4);e.activate(9);e.activate(4);e.activate(8);e.activate(4)
        self.assertEqual(len(e.draft().changes),3)
        self.assertEqual(e.rendered['cost'],'Lumina cost: 34*')
        self.assertEqual(e.rendered['mastery'],'> Mastery: Unmastered*')
    def test_no_selection_cannot_stage(self):
        e=self.editor();e.selection=None;e.activate(5);self.assertFalse(e.drafts)
    def test_conflicting_live_value_detected(self):
        d=PictoDraft((1,2,3,4));d.stage(('cost',None),30,35)
        self.assertEqual(d.conflicts({('cost',None):36}),(('cost',None),))
        d.acknowledge(('cost',None));self.assertFalse(d.changes)
    def test_round_up_and_zero(self):
        self.assertEqual(preview_stats({33:{1:3765,6:2485,8:764,9:38}},33,{1:.9,6:.1,8:1.2,9:.8}),{1:3389,6:249,8:917,9:31})

    def apply_editor(self):
        e=self.editor();e.operation=nullcontext;e.scope=object();e.panel=object();e.game_instance=object();e.passive_table=object()
        e.extra['source']=object();e.preferences=Mock();e.restore_queue=[];e.refresh_current=Mock();e.refresh_lumina_ui=Mock()
        e.fn=lambda owner,name:name;e.calls=[]
        def call(target,owner,name,**args):
            e.calls.append((name,args))
            if name=='SetBaseStatsMultiplier':e.multipliers[args['Stat']]=args['Value']
            if name=='RefreshCurrentGearStats':
                e.stats.update({k:v for k,v in preview_stats(e.scaling,e.level,e.multipliers).items() if e.multipliers[k]>0})
        e.call=call;e.read_stats=lambda item:(e.stats,e.multipliers)
        return e

    def test_one_apply_commits_all_fields_and_refreshes_once(self):
        e=self.apply_editor()
        for key,value in [(('cost',None),34),(('stat',1),.6),(('stat',6),.1),(('level',None),32),(('mastery',None),False)]:
            e.draft().stage(key,value,e.current_fields()[key])
        def native_change(scope,op,target,function,source,panel,gi,expected,value):
            if op==1:e.level=value
        with patch('expedition33.picto_progression.change',side_effect=native_change) as native:
            e.activate(6)
        self.assertEqual([c.args[1] for c in native.call_args_list],[1,2,3])
        self.assertEqual([name for name,args in e.calls].count('RefreshCurrentGearStats'),1)
        self.assertEqual([name for name,args in e.calls].count('UpdateEquipmentStats'),1)
        e.preferences.remember_many.assert_called_once_with('Cheater',[
            ('level',32,None),('stat',.6,1),('stat',.1,6),('mastery',False,None),('cost',34,None)])
        self.assertFalse(e.draft().changes)

    def test_partial_failure_preserves_acknowledged_edits_without_retry(self):
        e=self.apply_editor();original=e.call
        def call(target,owner,name,**args):
            if args.get('Stat')==6:raise RuntimeError('uncertain native reply')
            return original(target,owner,name,**args)
        e.call=call
        e.draft().stage(('stat',1),.6,.7);e.draft().stage(('stat',6),.1,0)
        with self.assertRaisesRegex(RuntimeError,'uncertain'):e.activate(6)
        e.preferences.remember_many.assert_called_once_with('Cheater',[('stat',.6,1)])
        self.assertEqual(e.draft().changes,{('stat',6):.1})

    def test_zero_draft_clears_stat_left_by_game_scaling_function(self):
        e=self.apply_editor();e.multipliers[6]=.1;e.stats[6]=249
        e.draft().stage(('stat',6),0.,.1)
        def clear(scope,op,target,function,source,panel,gi,expected,key):
            self.assertEqual((op,expected,key),(9,249,6));e.stats[key]=0
        with patch('expedition33.picto_progression.change',side_effect=clear) as native:e.activate(6)
        native.assert_called_once();self.assertEqual(e.stats[6],0);self.assertFalse(e.draft().changes)

if __name__=='__main__':unittest.main()
