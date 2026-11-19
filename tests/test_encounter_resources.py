import struct
import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch

from expedition33 import encounter_tables as tables,encounter_action as data
from encounter_samples import PROFILES,ACTION


KEY='e33c5701000000020000000300000004'
def obj(index,name='Input'):
    return N(pid=7,index=index,serial=1000+index,address=0x10000+index*256,name=name,
             class_name='Input',outer_index=1,object_flags=0)
def held(value):return N(object=value,active=True,_token=value.index+10000)


class ResourceFixture(unittest.TestCase):
    def setUp(self):
        self.calls=[];self.ids={};self.leases={};self.error_code=None
        def command(_,sent):
            op=struct.unpack_from('<I',sent,4)[0];reply=bytearray(sent)
            if op==254:
                mode=struct.unpack_from('<I',sent,120)[0]
                self.calls.append((op,mode,sent[392:488].split(b'\0',1)[0].decode()))
                self.assertEqual(self.resources.load.call_count,4)
                struct.pack_into('<2I',reply,128,100,101)
            else:mode=struct.unpack_from('<I',sent,232)[0];self.calls.append((op,mode))
            struct.pack_into('<2I',reply,8,self.error_code or 0,mode+1)
            return dict(mesh_packet=bytes(reply).hex())
        self.session=N(_transport=N(command=Mock(side_effect=command),story_trial_data_protocol=2,story_trial_tables_protocol=2,story_original_narrative_protocol=1))
        self.scope=N(_session=self.session,pid=7,_check=Mock(),close=Mock(),invocation_planner=Mock())
        self.parent=N(_session=self.session,pid=7,_check=Mock(),_register_native_owner=Mock(),_close_before_descendants=Mock())
        self.resources=N(scope=N(_session=self.session,pid=7,_check=Mock(),close=Mock()),gi=obj(1))
        def get(path,**options):
            key=(path,options.get('cls',False))
            if key not in self.ids:self.ids[key]=obj(10+len(self.ids),path.rsplit('.',1)[-1])
            return self.ids[key]
        def retain(value):
            key=(value.index,value.serial,value.address)
            if key not in self.leases:self.leases[key]=held(value)
            return self.leases[key]
        self.resources.load=Mock(side_effect=get);self.resources.hold=Mock(side_effect=retain)
        self.definitions=N(map_class=held(obj(3)),map_add=held(obj(4)))
        self.scope_patch=patch('expedition33._scope.SessionScope',return_value=self.scope)
        self.scope_patch.start();self.addCleanup(self.scope_patch.stop)

    def table_owner(self):return tables.EncounterTables(self.parent,KEY,self.definitions,profiles=PROFILES,resources=self.resources)


class EncounterTableResourceTests(ResourceFixture):
    def test_title_warm_reused_without_gi_discovery_or_cold_loads_and_all_inputs_precede_commit(self):
        tables.warm(self.resources,PROFILES);owner=self.table_owner()
        with patch('expedition33.story_save_identity.observe',side_effect=AssertionError('cold GI scan')),patch('expedition33.assets.load_asset',side_effect=AssertionError('cold load')),patch('expedition33.story_items.load_resource_asset',side_effect=AssertionError('cold resource')):
            owner.prepare();owner.prepare()
        self.assertEqual(self.resources.load.call_count,4);self.assertEqual(len(self.calls),2);self.assertTrue(owner.ready)
        self.assertTrue(all(row['attempted'] and row['acknowledged'] for row in owner.rows))
        owner.close();self.resources.scope.close.assert_not_called()

    def test_partial_resource_load_is_terminal_before_any_table_mutation(self):
        load=self.resources.load.side_effect
        def fail(path,**options):
            if self.resources.load.call_count==3:raise RuntimeError('resource receipt unknown')
            return load(path,**options)
        self.resources.load.side_effect=fail;owner=self.table_owner()
        with self.assertRaisesRegex(RuntimeError,'receipt unknown'):owner.prepare()
        with self.assertRaisesRegex(RuntimeError,'unavailable'):owner.prepare()
        with self.assertRaisesRegex(RuntimeError,'not replayed'):tables.warm(self.resources,PROFILES)
        self.assertEqual(self.calls,[]);self.assertEqual(self.resources.load.call_count,3)

    def test_all_packets_validate_before_first_dispatch(self):
        owner=self.table_owner();real=tables.packet
        def validate(owner_id,row,*args):
            if row['asset']=='ExampleEnemies':raise ValueError('second packet invalid')
            return real(owner_id,row,*args)
        with patch.object(tables,'packet',side_effect=validate):
            with self.assertRaisesRegex(ValueError,'second packet'):owner.prepare()
        self.assertEqual(self.calls,[]);self.assertFalse(owner.ready)
        self.assertTrue(all(not row['attempted'] for row in owner.rows))

    def test_known_rejection_cleans_only_acknowledged_prefix_and_never_replays(self):
        owner=self.table_owner();dispatch=self.session._transport.command.side_effect
        def reject(channel,sent):
            if len(self.calls)==1 and struct.unpack_from('<I',sent,120)[0]==0:self.error_code=4240
            result=dispatch(channel,sent);self.error_code=None;return result
        self.session._transport.command.side_effect=reject
        with self.assertRaises(tables.wire.OriginalNarrativeError):owner.prepare()
        self.assertFalse(owner.unknown);self.assertTrue(owner.rows[0]['acknowledged']);self.assertFalse(owner.rows[1]['acknowledged'])
        with self.assertRaises(RuntimeError):owner.prepare()
        self.assertEqual(len(self.calls),2);self.assertTrue(owner.close())
        self.assertEqual(self.calls[-1],(254,2,'ExampleEncounters'))

    def test_unknown_table_ack_cannot_cleanup_or_repeat(self):
        self.error_code=4241;owner=self.table_owner()
        with self.assertRaises(tables.wire.OriginalNarrativeError):owner.prepare()
        self.assertTrue(owner.unknown);self.assertFalse(owner.close());self.scope.close.assert_not_called()
        with self.assertRaises(RuntimeError):owner.prepare()
        self.assertEqual(len(self.calls),1)

    def test_cross_session_resources_rejected_before_load_and_expired_warm_lease_rejected(self):
        owner=self.table_owner();self.resources.scope._session=object()
        with self.assertRaisesRegex(RuntimeError,'another session'):owner.prepare()
        self.resources.load.assert_not_called();self.assertEqual(self.calls,[])
        self.resources.scope._session=self.session;tables.warm(self.resources,PROFILES)
        next(iter(self.resources._encounter_table_inputs[tables.profile_key(PROFILES)]['rows'].values()))[0].active=False
        with self.assertRaisesRegex(RuntimeError,'lease expired'):owner.prepare()
        self.assertEqual(self.calls,[])

    def test_legacy_callers_resolve_all_rows_before_mutation(self):
        owner=tables.EncounterTables(self.parent,KEY,self.definitions,profiles=PROFILES)
        # Retention itself stays scope-owned for legacy callers.
        owner.hold=lambda value:held(value)
        with patch('expedition33.story_save_identity.observe',return_value=(None,None,None,None,obj(1),None)),patch('expedition33.assets.load_asset',side_effect=lambda scope,path:N(return_value=self.resources.load(path))),patch('expedition33.story_items.load_resource_asset',side_effect=lambda scope,path:N(return_value=self.resources.load(path))):
            owner.prepare()
        self.assertTrue(owner.ready);self.assertEqual(len(self.calls),2)


class EncounterDataResourceTests(ResourceFixture):
    def setUp(self):
        super().setUp()
        self.metadata={path:obj(100+i,path.rsplit('.',1)[-1]) for i,path in enumerate(data.METADATA)}
        self.catalog=N(find_path=lambda path:self.metadata[path])
        self.capture=patch('expedition33.catalog.capture_matching',return_value=self.catalog);self.capture.start();self.addCleanup(self.capture.stop)
        self.batch=patch('expedition33._reader.shared_operation',side_effect=lambda *a,**kw:nullcontext());self.batch.start();self.addCleanup(self.batch.stop)
        self.selected=object();p=patch('expedition33.catalog.capture_selected',return_value=self.selected);p.start();self.addCleanup(p.stop)
        self.action=obj(200,'EncounterAction');self.action.class_name='BP_GameAction_TriggerBattle_C'
        self.call=N(invoke=Mock(return_value=nullcontext(N(return_value=self.action))))
        self.planner=N(prepare=Mock(return_value=self.call),close=Mock())
        self.scope.invocation_planner.return_value=self.planner
        p=patch('expedition33._stable_lease.acquire_stable',return_value=(held(self.action),None));self.acquire=p.start();self.addCleanup(p.stop)

    def owner(self):return data.EncounterActionData(self.parent,KEY,profile=ACTION,resources=self.resources)

    def test_warm_has_no_action_spawn_or_save_read_and_prepare_uses_fresh_selected_factory(self):
        with patch('expedition33.story_save_identity.observe',side_effect=AssertionError('save read')):
            data.warm(self.resources,ACTION);data.warm(self.resources,ACTION)
        self.assertEqual(self.resources.load.call_count,3);self.scope.invocation_planner.assert_not_called();self.assertEqual(self.calls,[])
        self.session._story_construction_resources=N(movement_planner=Mock(return_value=self.planner))
        owner=self.owner()
        with patch.object(owner,'context',side_effect=AssertionError('unrelated dialogue discovery')),patch('expedition33.assets.load_asset',side_effect=AssertionError('cold asset load')),patch('expedition33.picto_class_load.load_class',side_effect=AssertionError('cold class load')):
            owner.prepare()
        self.session._story_construction_resources.movement_planner.assert_called_once_with(self.scope,self.selected)
        self.assertEqual(self.calls,[(260,0)]);self.assertTrue(owner.started);self.assertEqual(owner.action.object,self.action)
        with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare()
        self.call.invoke.assert_called_once_with(fresh_results=True)

    def test_partial_warm_remains_terminal_without_factory(self):
        self.resources.load.side_effect=RuntimeError('class receipt unknown');owner=self.owner()
        with self.assertRaisesRegex(RuntimeError,'receipt unknown'):owner.prepare()
        with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare()
        with self.assertRaisesRegex(RuntimeError,'not replayed'):data.warm(self.resources,ACTION)
        self.call.invoke.assert_not_called();self.assertEqual(self.calls,[])

    def test_unknown_factory_receipt_is_not_replayed_or_discarded(self):
        self.call.invoke.side_effect=RuntimeError('factory receipt unknown');owner=self.owner()
        with self.assertRaisesRegex(RuntimeError,'factory receipt'):owner.prepare()
        self.assertTrue(owner.creation_attempted);self.assertTrue(owner.unknown);self.assertFalse(owner.close())
        with self.assertRaisesRegex(RuntimeError,'one-shot'):owner.prepare()
        self.call.invoke.assert_called_once();self.assertEqual(self.calls,[]);self.scope.close.assert_not_called()

    def test_unknown_action_lease_after_factory_ack_is_retained(self):
        self.acquire.side_effect=RuntimeError('action lease unknown');owner=self.owner()
        with self.assertRaisesRegex(RuntimeError,'lease unknown'):owner.prepare()
        self.assertTrue(owner.creation_returned);self.assertTrue(owner.unknown);self.assertFalse(owner.close())
        self.assertEqual(self.calls,[])

    def test_known_data_rejection_preserves_action_owner_for_clean_close(self):
        self.error_code=4290;owner=self.owner()
        with self.assertRaises(data.OriginalNarrativeError):owner.prepare()
        self.assertFalse(owner.unknown);self.assertFalse(owner.started);self.assertTrue(owner.close())
        self.scope.close.assert_called_once();self.resources.scope.close.assert_not_called()

    def test_resource_session_and_stable_lease_checked_before_factory(self):
        owner=self.owner();self.resources.scope._session=object()
        with self.assertRaisesRegex(RuntimeError,'another session'):owner.prepare()
        self.call.invoke.assert_not_called();self.resources.load.assert_not_called()
        self.resources.scope._session=self.session;data.warm(self.resources,ACTION)
        self.resources._encounter_action_inputs[data.profiles.encode(ACTION)]['objects'][0].active=False
        owner=self.owner()
        with self.assertRaisesRegex(RuntimeError,'lease expired'):owner.prepare()
        self.call.invoke.assert_not_called()

    def test_legacy_factory_path_remains_available(self):
        owner=data.EncounterActionData(self.parent,KEY,profile=ACTION)
        def context():owner.gi=held(obj(1))
        owner.context=Mock(side_effect=context);owner.hold=lambda value:held(value)
        with patch('expedition33.picto_class_load.load_class',return_value=N(return_value=obj(20))),patch('expedition33.assets.load_asset',return_value=N(return_value=obj(21))),patch('expedition33.story_items.load_resource_asset',return_value=N(return_value=obj(22))):
            owner.prepare()
        owner.context.assert_called_once();self.assertTrue(owner.started);self.assertEqual(self.calls,[(260,0)])


