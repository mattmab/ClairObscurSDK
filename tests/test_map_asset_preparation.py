import struct,unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock,patch
from expedition33.map_asset_preparation import AssetPreparation,SIZE,validate_request,process_asset_preparation
from expedition33.map_spawn_plan import SpawnPlan
from expedition33.worldbuilder_maps import FORMAT


class SpawnPlanTests(unittest.TestCase):
    def scene(self):
        return dict(format=FORMAT,version=1,name='test',world='/Game/Test.Test',
                    objects=[dict(id='a'*32,kind='mesh',asset='/Game/M.M',transform=[0,0,0,1,0,0,0,0,1,1,1,0])],assets=['/Game/M.M'])
    def test_caller_mutation_cannot_change_prepared_transform(self):
        scene=self.scene();plan=SpawnPlan(scene);scene['objects'][0]['transform'][4]=999
        self.assertEqual(plan.rows[0].transform[4],0)
        self.assertEqual(plan.object_count,1);self.assertEqual(plan.skipped_world_edits,0)
    def test_invalid_or_unsupported_scene_cannot_construct_plan(self):
        scene=self.scene();scene['objects'][0]['transform'][0]=float('nan')
        with self.assertRaises(ValueError):SpawnPlan(scene)
        scene=self.scene();scene['objects'][0]['kind']='actor'
        with self.assertRaisesRegex(ValueError,'static-mesh'):SpawnPlan(scene)


class AssetWireTests(unittest.TestCase):
    def packet(self,op):
        data=bytearray(SIZE);struct.pack_into('<4IQ',data,0,3,op,0,0,73)
        if op==104:
            for i in range(3):struct.pack_into('<iiQ',data,88+16*i,i+1,i+2,0x10000+8*i)
        elif op==105:data[2000:2009]=b'/Game/M.M'
        return data
    def owner(self,mutate=None):
        owner=AssetPreparation.__new__(AssetPreparation)
        owner.owner=73;owner.closed=False;owner.uncertain=False;owner.started=True;owner.assets={};owner.attempts={}
        owner.profile=dict(assets=0,load_ms=0.)
        owner.session=SimpleNamespace(_check=Mock(),pid=123)
        def command(_,packet):
            raw=bytearray(packet)
            if struct.unpack_from('<I',raw,4)[0]==105:struct.pack_into('<iiQ',raw,4096,3,17,0x10000)
            if mutate:mutate(raw)
            return dict(mesh_packet=raw.hex())
        owner.session._transport=SimpleNamespace(command=Mock(side_effect=command))
        owner.scope=SimpleNamespace(_lease_context=nullcontext,close=Mock())
        return owner
    def test_packet_bounds_and_positive_metadata(self):
        for op in (104,105,106):validate_request(bytes(self.packet(op)))
        raw=self.packet(104);struct.pack_into('<i',raw,92,0)
        with self.assertRaises(ValueError):validate_request(bytes(raw))
        raw=self.packet(105);raw[2512]=1
        with self.assertRaises(ValueError):validate_request(bytes(raw))
        raw=self.packet(106);raw[88]=1
        with self.assertRaises(ValueError):validate_request(bytes(raw))
    def test_cached_game_assets_are_not_reloaded(self):
        owner=self.owner()
        with patch('expedition33.loading_preparation.service_loading_io') as pump:
            owner.prepare(['/Game/M.M','/Game/M.M'])
            owner.prepare(['/Game/M.M'])
        owner.session._transport.command.assert_called_once();pump.assert_called_once_with(owner.session)
        self.assertEqual(owner.get('/Game/M.M').serial,17)
        self.assertTrue(owner.attempts['/Game/M.M']['acknowledged'])
    def test_failed_engine_lease_is_not_retried_or_admitted(self):
        owner=self.owner();path='/Engine/BasicShapes/Cube.Cube'
        with patch.object(owner,'_prepare_engine_asset',side_effect=RuntimeError('lease outcome unknown')) as acquire:
            with self.assertRaisesRegex(RuntimeError,'lease outcome unknown'):owner.prepare([path])
            with self.assertRaisesRegex(RuntimeError,'not replayed'):owner.prepare([path])
        acquire.assert_called_once_with(path);self.assertIsNone(owner.get(path))
        self.assertFalse(owner.attempts[path]['acknowledged'])
    def test_acknowledged_assets_survive_later_rejected_path_without_reloading_it(self):
        def reject_second(raw):
            if raw[2000:2009]==b'/Game/X.X':struct.pack_into('<I',raw,8,2165)
        owner=self.owner(reject_second)
        with patch('expedition33.loading_preparation.service_loading_io'):
            with self.assertRaisesRegex(RuntimeError,'2165'):owner.prepare(['/Game/M.M','/Game/X.X'])
            with self.assertRaisesRegex(RuntimeError,'not replayed'):owner.prepare(['/Game/M.M','/Game/X.X'])
        self.assertEqual(owner.session._transport.command.call_count,2)
        self.assertEqual(owner.get('/Game/M.M').serial,17);self.assertIsNone(owner.get('/Game/X.X'))
    def test_loaded_engine_mesh_is_retained_during_loading_and_reused_without_world_lookup(self):
        owner=self.owner();path='/Engine/BasicShapes/Cube.Cube'
        mesh=SimpleNamespace(index=12,serial=1234,address=0x12000,class_name='StaticMesh')
        owner.scope.retain=Mock(return_value=SimpleNamespace(object=mesh))
        catalog=SimpleNamespace(find_path=Mock(return_value=mesh))
        with patch('expedition33._reader.ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_matching',return_value=catalog) as capture,patch('expedition33.loading_preparation.service_loading_io') as pump:
            owner.prepare([path]);owner.prepare([path])
        capture.assert_called_once_with(123,names=('Cube',));catalog.find_path.assert_called_once_with(path)
        owner.scope.retain.assert_called_once_with(mesh);pump.assert_called_once_with(owner.session)
        owner.session._transport.command.assert_not_called()
        self.assertEqual(owner.get(path).serial,1234)
    def test_engine_zero_serial_is_atomically_stabilized_before_cache_admission(self):
        owner=self.owner();path='/Engine/BasicShapes/Cube.Cube'
        observed=SimpleNamespace(index=12,serial=0,address=0x12000,class_name='StaticMesh')
        stable=SimpleNamespace(index=12,serial=1234,address=0x12000,class_name='StaticMesh')
        owner.scope.retain=Mock()
        with patch('expedition33._reader.ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_matching',return_value=SimpleNamespace(find_path=lambda _:observed)),patch('expedition33._stable_lease.acquire_stable',return_value=(SimpleNamespace(object=stable),None)) as acquire:
            owner.prepare([path])
        acquire.assert_called_once_with(owner.scope,observed);owner.scope.retain.assert_not_called()
        self.assertEqual(owner.get(path).serial,1234)
    def test_engine_wrong_class_never_acquires_or_enters_prepared_cache(self):
        owner=self.owner();owner.scope.retain=Mock()
        mesh=SimpleNamespace(index=12,serial=1234,address=0x12000,class_name='World')
        with patch('expedition33._reader.ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_matching',return_value=SimpleNamespace(find_path=lambda _:mesh)):
            with self.assertRaisesRegex(ValueError,'Unsupported engine asset'):owner.prepare(['/Engine/BasicShapes/Cube.Cube'])
        owner.scope.retain.assert_not_called();self.assertFalse(owner.assets)
    def test_uncertain_reply_is_not_replayed_or_exposed(self):
        owner=self.owner(lambda raw:raw.__setitem__(1500,1))
        with self.assertRaisesRegex(RuntimeError,'mismatch'):owner.prepare(['/Game/M.M'])
        self.assertTrue(owner.uncertain);self.assertIsNone(owner.get('/Game/M.M'))
        with self.assertRaisesRegex(RuntimeError,'unavailable'):owner.prepare(['/Game/M.M'])
        owner.session._transport.command.assert_called_once()
    def test_zero_serial_asset_reply_is_not_usable(self):
        owner=self.owner(lambda raw:struct.pack_into('<i',raw,4100,0))
        with self.assertRaisesRegex(RuntimeError,'identity'):owner.prepare(['/Game/M.M'])
        self.assertTrue(owner.uncertain);self.assertFalse(owner.assets)
    def test_close_releases_owner_and_rejects_further_commands(self):
        owner=self.owner();self.assertTrue(owner.close());self.assertTrue(owner.close())
        owner.session._transport.command.assert_called_once();owner.scope.close.assert_called_once()
        with self.assertRaises(RuntimeError):owner._send(106)


class ProcessAssetOwnerTests(unittest.TestCase):
    def setup_process(self):
        session=SimpleNamespace(_check=Mock())
        metadata=SimpleNamespace(scope=SimpleNamespace(_reference_owners=[]))
        return session,metadata
    def owner(self,session,*,started=True):
        owner=AssetPreparation.__new__(AssetPreparation)
        owner.session=session;owner.closed=False;owner.uncertain=False;owner.started=started
        return owner
    def test_two_mods_share_one_construction_and_never_replace_foreign_cache(self):
        session,metadata=self.setup_process();foreign_cache=object();session._other_asset_cache=foreign_cache
        created=[]
        def construct(owner,current):
            created.append(owner);owner.session=current;owner.closed=False;owner.uncertain=False;owner.started=True
            metadata.scope._reference_owners.append(owner)
        with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata),patch.object(AssetPreparation,'__init__',construct):
            first=process_asset_preparation(session);second=process_asset_preparation(session)
        self.assertIs(first,second);self.assertEqual(created,[first]);self.assertIs(session._other_asset_cache,foreign_cache)
    def test_adopts_preexisting_exact_session_owner_registered_by_another_mod(self):
        session,metadata=self.setup_process();existing=self.owner(session);metadata.scope._reference_owners.append(existing)
        with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata),patch.object(AssetPreparation,'__init__',side_effect=AssertionError('must share')):
            self.assertIs(process_asset_preparation(session),existing)
        self.assertFalse(session._map_asset_preparation_journal.attempted)
    def test_failed_partial_constructor_is_terminal_even_with_registered_owner(self):
        session,metadata=self.setup_process();calls=[]
        def construct(owner,current):
            calls.append(owner);owner.session=current;owner.closed=False;owner.uncertain=True;owner.started=False
            metadata.scope._reference_owners.append(owner)
            raise RuntimeError('registration receipt unknown')
        with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata),patch.object(AssetPreparation,'__init__',construct):
            with self.assertRaisesRegex(RuntimeError,'receipt unknown'):process_asset_preparation(session)
            with self.assertRaisesRegex(RuntimeError,'not replayed'):process_asset_preparation(session)
        self.assertEqual(len(calls),1);self.assertEqual(metadata.scope._reference_owners,calls)
    def test_failed_preexisting_registration_cannot_be_adopted(self):
        session,metadata=self.setup_process();existing=self.owner(session,started=False);metadata.scope._reference_owners.append(existing)
        with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata),patch.object(AssetPreparation,'__init__',side_effect=AssertionError('must not replace')):
            with self.assertRaisesRegex(RuntimeError,'unavailable'):process_asset_preparation(session)
            with self.assertRaisesRegex(RuntimeError,'not replayed'):process_asset_preparation(session)
    def test_closed_uncertain_or_cross_session_owner_never_gets_replaced(self):
        for field in ('closed','uncertain','session'):
            with self.subTest(field=field):
                session,metadata=self.setup_process();existing=self.owner(session);metadata.scope._reference_owners.append(existing)
                with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata),patch.object(AssetPreparation,'__init__',side_effect=AssertionError('must not replace')):
                    self.assertIs(process_asset_preparation(session),existing)
                    setattr(existing,field,object() if field=='session' else True)
                    with self.assertRaisesRegex(RuntimeError,'unavailable'):process_asset_preparation(session)
    def test_duplicate_active_owners_are_not_arbitrarily_selected_or_closed(self):
        session,metadata=self.setup_process();metadata.scope._reference_owners.extend([self.owner(session),self.owner(session)])
        with patch('expedition33._metadata_stabilization.process_preparation',return_value=metadata):
            with self.assertRaisesRegex(RuntimeError,'Multiple'):process_asset_preparation(session)
            with self.assertRaisesRegex(RuntimeError,'not replayed'):process_asset_preparation(session)


if __name__=='__main__':unittest.main()
