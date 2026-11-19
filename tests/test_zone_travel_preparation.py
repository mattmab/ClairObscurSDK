import unittest
from contextlib import nullcontext
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import zone_travel as z


def identity(obj):return obj.index,obj.serial,obj.address


class Catalog:
    def __init__(self,objects):
        self.objects=tuple(objects);self.by_index={o.index:o for o in objects}
    def path_name(self,obj):return obj.path
    def with_observations(self,other):
        merged=dict(self.by_index);merged.update(other.by_index)
        return Catalog(merged.values())


class ZonePreparationTests(unittest.TestCase):
    def registration_fixture(self):
        scope,construction,ctx,current,value,expected=self.fixture()
        def row(**kw):return N(types={(0,k):'ObjectProperty' for k in kw},values={(0,k):v for k,v in kw.items()},errors={},truncated=False)
        system=N(index=8,serial=18,address=0x20000,object_flags=0,class_name='BP_DialogueSystemComponent_C',
            outer_index=expected[5].index,outer_serial=expected[5].serial,path='component')
        current=current.with_observations(Catalog((system,)))
        current.outer_chain=lambda obj:(current.by_index[7],)
        rows={7:value,5:row(PlayerController=expected[5]),6:row(BP_DialogueSystemComponent=system)}
        return scope,construction,ctx,current,rows,expected,system

    def test_registration_combines_current_links_and_component_without_recapturing_identity(self):
        scope,construction,ctx,current,rows,expected,system=self.registration_fixture()
        with patch.object(z,'capture_selected_values',return_value=(current,rows)) as read,patch.object(z,'capture_selected') as repeat:
            objects,catalog,observed=z._travel_objects(scope,registration=True)
        self.assertEqual(objects,expected);self.assertIs(observed,system)
        self.assertTrue(set(o.index for o in expected)<=catalog.by_index.keys())
        construction.anchor.context.assert_called_once_with();repeat.assert_not_called()
        read.assert_called_once_with(17,(ctx['world'][1:],identity(expected[4]),ctx['controller'][1:]),
            fields=('OwningGameInstance','PlayerController','BP_DialogueSystemComponent'),references=True)

    def test_registration_rechecks_changed_controller_component_world_and_schema(self):
        for change in ('controller','component','component lifetime','world','schema','incomplete'):
            scope,construction,ctx,current,rows,expected,system=self.registration_fixture()
            if change=='controller':rows[5].values[(0,'PlayerController')]=system
            elif change=='component':system.outer_serial+=1
            elif change=='component lifetime':system.object_flags=0x20
            elif change=='world':current.outer_chain=lambda obj:()
            elif change=='schema':rows[5].types[(0,'PlayerController')]='IntProperty'
            else:rows[6].truncated=True
            with self.subTest(change=change),patch.object(z,'capture_selected_values',return_value=(current,rows)):
                with self.assertRaises(z.NotReady):z._travel_objects(scope,registration=True)
            scope._session._transport._command.assert_not_called()

    def test_registration_packet_keeps_fresh_catalog_and_never_dispatches_travel(self):
        scope,construction,ctx,current,rows,expected,system=self.registration_fixture()
        route=dict(level_id='Lumiere',asset_name='Level_Lumiere_Main_V2')
        with patch.object(z,'ReadBatch',return_value=nullcontext()),patch.object(z,'active_reader',return_value=None),\
                patch.object(z,'capture_selected_values',return_value=(current,rows)):
            packet,catalog,observed=z.prepare_spawn_registration(scope,route,'Level.SpawnPoint.LumiereAct03.Opera')
        z.validate_request(packet);self.assertEqual(z.HEADER.unpack_from(packet),(2,0,0,0))
        self.assertIs(observed,system);self.assertEqual(catalog.by_index[system.index],system)
        scope._session._transport._command.assert_not_called()
        with self.assertRaisesRegex(ValueError,'read-only'):z.travel_to_entrance(scope,route,_registration=True)

    def fixture(self):
        def obj(index,cls,path=''):
            return N(index=index,serial=index+10,address=0x10000+index*8,
                     object_flags=0,class_name=cls,path=path)
        table=obj(1,'DataTable',z.TABLE)
        function=obj(2,'Function',z.LIB+'.FL_jRPG_CustomFunctionLibrary_C:ChangeMapByName')
        cdo=obj(3,'FL_jRPG_CustomFunctionLibrary_C',z.LIB+'.Default__FL_jRPG_CustomFunctionLibrary_C')
        gi=obj(4,'BP_jRPG_GI_Custom_C');local=obj(5,'LocalPlayer')
        pc=obj(6,'BP_jRPG_PlayerController_C');world=obj(7,'World')
        ctx=dict(controller=(17,*identity(pc)),world=(17,*identity(world)),world_path='/Game/Test')
        static=Catalog((table,function,cdo));current=Catalog((gi,local,pc,world))
        value=N(types={(70,'OwningGameInstance'):'ObjectProperty'},
                values={(70,'OwningGameInstance'):gi},errors={},truncated=False)
        anchor=N(identity=identity(local),context=Mock(return_value=ctx))
        construction=N(catalog=Mock(return_value=static),anchor=anchor,resources=N(gi=gi))
        transport=N(zone_travel_protocol=2,zone_spawn_travel_protocol=1,_command=Mock())
        scope=N(pid=17,_check=Mock(),_world_binding_token=(ctx['world'],),
                _session=N(_story_construction_resources=construction,_transport=transport))
        return scope,construction,ctx,current,value,(table,function,cdo,gi,local,pc)

    def test_retained_selectors_still_read_live_world_ownership_on_every_preparation(self):
        scope,construction,ctx,current,value,expected=self.fixture()
        with patch.object(z,'capture_selected_values',return_value=(current,{7:value})) as read, \
                patch.object(z,'capture_matching') as global_read,patch.object(z,'controller_context') as global_context:
            self.assertEqual(z._travel_objects(scope),expected)
            self.assertEqual(z._travel_objects(scope),expected)
        self.assertEqual(read.call_count,2);self.assertEqual(construction.anchor.context.call_count,4)
        read.assert_called_with(17,(ctx['world'][1:],identity(expected[4]),ctx['controller'][1:]),
            fields=('OwningGameInstance',),references=True)
        global_read.assert_not_called();global_context.assert_not_called()

    def test_mismatched_retired_or_incomplete_game_instance_never_falls_back(self):
        for change in ('different','retired','missing','incomplete','schema'):
            with self.subTest(change=change):
                scope,construction,ctx,current,value,expected=self.fixture()
                if change=='different':construction.resources.gi=N(index=44,serial=54,address=0x20000)
                elif change=='retired':expected[3].object_flags=0x20
                elif change=='missing':value.values[(70,'OwningGameInstance')]=None
                elif change=='incomplete':value.truncated=True
                else:value.types[(70,'OwningGameInstance')]='IntProperty'
                with patch.object(z,'capture_selected_values',return_value=(current,{7:value})),patch.object(z,'capture_matching') as fallback:
                    with self.assertRaises(z.NotReady):z._travel_objects(scope)
                fallback.assert_not_called()

    def test_changed_controller_or_scope_world_refuses_prepared_route(self):
        for change in ('controller','scope world','retired world','retired player'):
            with self.subTest(change=change):
                scope,construction,ctx,current,value,expected=self.fixture()
                if change=='controller':construction.anchor.context.side_effect=(ctx,dict(ctx,controller=(17,90,91,0x20000)))
                elif change=='scope world':scope._world_binding_token=((17,90,91,0x20000),)
                elif change=='retired world':current.by_index[7].object_flags=0x20
                else:expected[4].object_flags=0x20
                with patch.object(z,'capture_selected_values',return_value=(current,{7:value})):
                    with self.assertRaises(z.NotReady):z._travel_objects(scope)

    def test_invalid_metadata_owner_cannot_fall_back_to_unowned_discovery(self):
        scope,construction,*_=self.fixture()
        construction.catalog.side_effect=RuntimeError('Construction resources belong to another session')
        with patch.object(z,'capture_matching') as fallback,patch.object(z,'capture_selected_values') as read:
            with self.assertRaisesRegex(RuntimeError,'another session'):z._travel_objects(scope)
        fallback.assert_not_called();read.assert_not_called()

    def test_exact_static_paths_remain_required(self):
        scope,construction,ctx,current,value,expected=self.fixture()
        expected[0].path='/Game/Other/DT_LevelData.DT_LevelData'
        with patch.object(z,'capture_selected_values',return_value=(current,{7:value})):
            with self.assertRaises(z.NotReady):z._travel_objects(scope)

    def test_generic_scope_without_story_resources_keeps_legacy_discovery(self):
        scope,construction,ctx,current,value,expected=self.fixture()
        del scope._session._story_construction_resources
        with patch.object(z,'controller_context',return_value=ctx), \
                patch.object(z,'capture_matching',return_value=Catalog(expected)) as discovery, \
                patch.object(z,'capture_selected',return_value=Catalog((expected[5],))):
            self.assertEqual(z._travel_objects(scope),expected)
        discovery.assert_called_once_with(17,names=z.ROUTE_NAMES,classes=('LocalPlayer','BP_jRPG_GI_Custom_C'))

    def test_prepared_packet_is_read_only_and_retains_named_spawn_protocol(self):
        scope,construction,ctx,current,value,expected=self.fixture()
        route=dict(level_id='Lumiere',asset_name='Level_Lumiere_Main_V2')
        tag='Level.SpawnPoint.LumiereAct03.Opera'
        with patch.object(z,'ReadBatch',return_value=nullcontext()),patch.object(z,'active_reader',return_value=None), \
                patch.object(z,'capture_selected_values',return_value=(current,{7:value})):
            packet=z.prepare_spawn_packet(scope,route,tag)
        z.validate_request(packet);self.assertEqual(z.HEADER.unpack_from(packet),(2,0,0,0))
        self.assertEqual(tuple(z.IDENTITY.unpack_from(packet,16+16*i) for i in range(6)),tuple(map(identity,expected)))
        scope._session._transport._command.assert_not_called()
