import struct,unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import save_story_ui as ui,save_list_entries as query


class SharedMetadataTests(unittest.TestCase):
    def service(self):
        service=ui.SaveStoryUI.__new__(ui.SaveStoryUI)
        service.session=N(_transport=N(metadata_stabilization_protocol=1))
        service.metadata=None;service.timings={};service.labels={};service._closed=False
        return service
    def test_metadata_warms_once_and_failed_preparation_never_replays(self):
        for fail in (False,True):
            service=self.service();metadata=Mock(ready=False)
            def prepare():
                if fail:raise RuntimeError('schema changed')
                metadata.ready=True
            metadata.prepare.side_effect=prepare
            with patch.object(ui,'LabelMetadata',return_value=metadata) as factory:
                if fail:
                    with self.assertRaisesRegex(RuntimeError,'schema changed'):service._prepare_metadata()
                    with self.assertRaisesRegex(RuntimeError,'not replayed'):service._prepare_metadata()
                else:service._prepare_metadata();service._prepare_metadata()
                factory.assert_called_once();metadata.prepare.assert_called_once()
            self.assertIs(service.metadata,metadata)
            service.close();metadata.close.assert_called_once()
    def test_planner_adopts_fresh_row_catalog_and_rejects_foreign_session(self):
        session=object();scope=N(_session=session,_check=Mock(),invocation_planner=Mock())
        metadata=ui.LabelMetadata.__new__(ui.LabelMetadata);metadata.ready=True;metadata.scope=scope
        metadata.session=session;metadata.observations=object();fresh=object();planner=Mock()
        scope.invocation_planner.return_value=planner
        self.assertIs(metadata.planner(scope,fresh),planner)
        planner.adopt_observations.assert_called_once_with(fresh)
        scope.invocation_planner.assert_called_once_with(observations=metadata.observations,selected_results=True)
        with self.assertRaisesRegex(RuntimeError,'another session'):metadata.planner(N(_session=object(),_check=Mock()),fresh)
        planner.adopt_observations.side_effect=RuntimeError('recycled row')
        with self.assertRaisesRegex(RuntimeError,'recycled'):metadata.planner(scope,fresh)
        planner.close.assert_called_once()
    def test_cleanup_uses_fresh_owned_frame_without_old_recycled_row_catalog(self):
        owner=ui.Label.__new__(ui.Label);owner.unknown=False;owner.added=True
        owner.frame=N(index=1,serial=2,address=0x10000);owner.widget=object();owner.scope=Mock(pid=1)
        owner.planner=Mock();previous=owner.planner;catalog=Mock();fresh=object();planner=Mock(_catalog=catalog)
        planner.prepare.return_value.invoke.return_value=nullcontext();owner.metadata=Mock()
        owner.metadata.planner.return_value=planner
        with patch.object(ui,'capture_selected',return_value=fresh) as selected,patch.object(ui,'capture_matching') as scan:
            self.assertTrue(owner.close())
        selected.assert_called_once_with(1,((1,2,0x10000),));scan.assert_not_called()
        owner.metadata.planner.assert_called_once_with(owner.scope,fresh)
        previous.close.assert_called_once();planner.close.assert_called_once();owner.scope.close.assert_called_once()
    def test_build_reuses_metadata_before_first_spawn_but_checks_original_image_cell(self):
        tree=object();grid=object();row=object();catalog=Mock(by_index={1:object()});metadata=Mock(enum_arguments={})
        catalog.find_class.return_value=N(index=1)
        planner=Mock(_catalog=catalog);metadata.planner.return_value=planner
        planner.prepare.return_value.invoke.return_value=nullcontext(N(return_value=None))
        session=N(_save_story_ui=N(metadata=metadata));scope=Mock(pid=1)
        values=N(errors=[],values={('Row','WidgetTree'):tree,('Row','SlotGrid'):grid})
        with patch.object(ui,'SessionScope',return_value=scope),patch.object(ui,'read_values_with_references',return_value=(values,catalog)),patch.object(ui,'image_cell',return_value=(dict(Row=0,Column=0,RowSpan=5,ColumnSpan=1,Layer=0),catalog)) as cell,patch.object(ui,'capture_matching') as scan,patch('expedition33.reflection.describe_selected') as describe:
            owner=ui.Label(session)
            with self.assertRaisesRegex(RuntimeError,'construction failed'):owner.build(row,catalog,'Story',still_bound=lambda:True)
        cell.assert_called_once_with(catalog,tree,grid);scan.assert_not_called();describe.assert_not_called()
        metadata.planner.assert_called_once_with(scope,catalog)


class GetterMetadataTests(unittest.TestCase):
    def test_queries_lease_only_fresh_row_and_return_current_native_model_each_time(self):
        session=N();scope=N(pid=1,_session=session);row=N(index=1,serial=2,address=0x10000)
        child=N(_session=session,_check=Mock(),_lease_context=lambda:nullcontext(),close=Mock())
        library=N(index=2,serial=3,address=0x20000);function=N(index=3,serial=4,address=0x30000)
        metadata=Mock();metadata.held.return_value=(N(object=library,_token=20),N(object=function,_token=30))
        oldmodel=N(index=4,serial=5,address=0x40000);newmodel=N(index=5,serial=6,address=0x50000)
        models=iter((oldmodel,newmodel));packets=[]
        def command(kind,sent):
            query.validate(sent);packets.append(sent);model=next(models);reply=bytearray(sent)
            struct.pack_into('<I',reply,12,1);struct.pack_into('<iiQ',reply,96,model.index,model.serial,model.address)
            return {'mesh_packet':reply.hex()}
        session._transport=N(command=command)
        catalog=Mock();catalog.with_observations.return_value=catalog;catalog.resolve.return_value=row
        fresh=N(by_index={1:row,4:oldmodel,5:newmodel})
        with patch.object(query,'SessionScope',return_value=child),patch.object(query,'capture_selected',return_value=fresh),patch.object(query,'acquire_stable',return_value=(N(object=row,_token=10),None)) as lease,patch.object(query,'capture_matching') as scan:
            self.assertIs(query.read(scope,row,catalog,metadata=metadata),oldmodel)
            self.assertIs(query.read(scope,row,catalog,metadata=metadata),newmodel)
        self.assertEqual(lease.call_args_list,[((child,row),),((child,row),)])
        self.assertEqual(child.close.call_count,2);self.assertEqual(metadata.held.call_count,2);scan.assert_not_called()
        self.assertTrue(all(struct.unpack_from('<3Q',p,72)==(10,20,30) for p in packets))
    def test_getter_cannot_outlive_its_scope_or_cross_sessions(self):
        session=object();scope=N(_session=session,_check=Mock())
        metadata=query.GetterMetadata.__new__(query.GetterMetadata);metadata.scope=scope;metadata.session=session
        metadata.ready=True;metadata.leases=[N(active=True),N(active=True)]
        self.assertEqual(metadata.held(scope),tuple(metadata.leases))
        with self.assertRaisesRegex(RuntimeError,'another session'):metadata.held(N(_session=object(),_check=Mock()))
        metadata.leases[1].active=False
        with self.assertRaisesRegex(RuntimeError,'unavailable'):metadata.held(scope)


if __name__=='__main__':unittest.main()
