"""Prepared assets must preserve exact admission and partial-spawn semantics."""
import struct,unittest
from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock,patch
from expedition33 import map_runtime as source
from expedition33.map_spawn_plan import SpawnPlan
from expedition33.worldbuilder_maps import FORMAT


class PreparedRuntimeTests(unittest.TestCase):
    def test_construction_anchor_waits_for_new_world_admission(self):
        from expedition33.story_construction import StoryConstruction
        from expedition33.world_lifecycle import WorldLifecycleError
        observed={'world':(123,9,99,0x9000),'controller':(123,8,88,0x8000)}
        owner=StoryConstruction.__new__(StoryConstruction)
        owner.anchor=SimpleNamespace(context=lambda:observed)
        scope=SimpleNamespace(_world_binding_token=((123,1,11,0x1000),(),(),0))
        with self.assertRaises(WorldLifecycleError):owner.context(scope)
        scope._world_binding_token=None
        with self.assertRaises(WorldLifecycleError):owner.context(scope)
        scope._world_binding_token=(observed['world'],(),(),1)
        self.assertIs(owner.context(scope),observed)
    def test_process_preparation_publishes_stabilized_metadata_once(self):
        root=SimpleNamespace(pid=123)
        discovered=[SimpleNamespace(index=i,serial=0,address=0x10000+8*i) for i in range(14)]
        stable={o.index:SimpleNamespace(index=o.index,serial=1001+o.index,address=o.address) for o in discovered}
        catalog=SimpleNamespace(find_path=Mock(side_effect=discovered))
        preparation=SimpleNamespace(prepare=Mock(return_value=SimpleNamespace(by_index=stable)))
        with patch.object(source,'ReadBatch',return_value=nullcontext()),patch.object(source,'capture_matching',return_value=catalog),patch('expedition33._metadata_stabilization.process_preparation',return_value=preparation):
            result=source.prepare_metadata(root)
            self.assertTrue(all(o.serial>0 for o in result))
            self.assertIs(source.prepare_metadata(root),result)
            preparation.prepare.assert_called_once_with(catalog,discovered)
    def test_strict_context_rejects_new_world_before_coordinator_catches_up(self):
        from expedition33.world_lifecycle import WorldLifecycleError
        world=SimpleNamespace(index=9,serial=99,address=0x9000,class_name='World')
        pawn=SimpleNamespace(index=2,serial=22,address=0x2000,class_name='BP_jRPG_Character_World_C',outer_index=9)
        pc=SimpleNamespace(object_flags=0,index=8,serial=88,address=0x8000)
        catalog=SimpleNamespace(select=lambda _: [pc],by_index={9:world},path_name=lambda _: '/Game/QA.Test')
        values=SimpleNamespace(values={(0,'Pawn'):pawn,(0,'bIsLocalPlayerController'):True})
        scope=SimpleNamespace(pid=123,_world_binding_token=((123,1,11,0x1000),(),(),0))
        with patch.object(source,'ReadBatch',side_effect=lambda _:nullcontext()),patch.object(source,'capture_matching',return_value=catalog),patch.object(source,'read_values_with_references',return_value=(values,catalog)):
            with self.assertRaisesRegex(WorldLifecycleError,'lifecycle handoff'):
                source.context(scope,require_bound_world=True)
            # A newly admitted scope can observe the exact same new world.
            scope._world_binding_token=((123,9,99,0x9000),(),(),0)
            self.assertEqual(source.context(scope,require_bound_world=True)['visit'],[9,99,0x9000])
            scope._world_binding_token=None
            with self.assertRaises(WorldLifecycleError):source.context(scope,require_bound_world=True)
            self.assertTrue(source.context(scope)['ready'])
    def owner(self):
        owner=source.MapRuntime.__new__(source.MapRuntime)
        owner.scope=SimpleNamespace(pid=123,_session=SimpleNamespace(_map_runtime_metadata=tuple(range(14))))
        owner.started=False;owner.uncertain=False;owner.objects={};owner.profile={};owner.visit=None
        owner._closed=False
        return owner
    def expected(self):return dict(world='/Game/Test.Test',visit=[1,11,0x10000],pawn=[2,22,0x20000],ready=True)
    def scene(self):
        rows=[dict(id=f'{i:032x}',kind='mesh',asset=asset,transform=[0,0,0,1,i,0,0,0,1,1,1,0])
              for i,asset in enumerate(('/Game/A.A','/Game/B.B','/Game/A.A'))]
        return dict(format=FORMAT,version=1,name='test',world='/Game/Test.Test',objects=rows,assets=['/Game/A.A','/Game/B.B'])
    def test_preloaded_assets_skip_blocking_load_and_partial_batches_do_not_repeat_props(self):
        owner=self.owner();plan=SpawnPlan(self.scene());events=[]
        a=SimpleNamespace(index=10,serial=100,address=0x30000)
        prepared=SimpleNamespace(get=lambda path:a if path=='/Game/A.A' else None)
        def admit(expected):owner.started=True;events.append('admit')
        owner._prepare=Mock(side_effect=admit)
        def send(op,**kwargs):
            raw=bytearray(source.SIZE)
            if op==97:
                events.append(('load',kwargs['path']));struct.pack_into('<iiQ',raw,4096,20,200,0x40000)
            elif op==94:
                rows=kwargs['rows'];events.append(('spawn',tuple(transform[4] for _,transform in rows)))
                # Force a native time-budget boundary after one acknowledged row.
                struct.pack_into('<I',raw,3560,1)
                struct.pack_into('<iiQ',raw,4208,30+rows[0][1][4],300,0x50000+8*rows[0][1][4])
            else:raise AssertionError('unexpected operation')
            return raw
        owner._send=Mock(side_effect=send)
        temporary=SimpleNamespace(close=Mock(),retain=Mock())
        with patch.object(source,'SessionScope',return_value=temporary):
            result=owner.load(plan,self.expected(),asset_preparation=prepared)
        self.assertEqual(result,dict(objects=3,skipped_world_edits=0))
        self.assertEqual(events,['admit',('load','/Game/B.B'),('spawn',(0,1,2)),('spawn',(1,2)),('spawn',(2,))])
        self.assertEqual(len(owner.objects),3);temporary.close.assert_called_once()
        temporary.retain.assert_not_called()
    def test_wrong_world_plan_is_rejected_before_asset_or_actor_dispatch(self):
        owner=self.owner();owner._prepare=Mock();owner._send=Mock();prepared=Mock()
        expected=self.expected();expected['world']='/Game/Other.Other'
        with self.assertRaisesRegex(ValueError,'same game level'):
            owner.load(SpawnPlan(self.scene()),expected,asset_preparation=prepared)
        owner._prepare.assert_not_called();owner._send.assert_not_called();prepared.get.assert_not_called()
    def test_prepared_engine_mesh_needs_no_post_save_discovery_or_second_lease(self):
        owner=self.owner();scene=self.scene();path='/Engine/BasicShapes/Cube.Cube'
        for row in scene['objects']:row['asset']=path
        scene['assets']=[path];plan=SpawnPlan(scene)
        mesh=SimpleNamespace(index=10,serial=1001,address=0x30000)
        prepared=SimpleNamespace(get=lambda _:mesh)
        owner._prepare=Mock(side_effect=lambda _:setattr(owner,'started',True))
        def spawn(op,**kwargs):
            self.assertEqual(op,94);raw=bytearray(source.SIZE);rows=kwargs['rows']
            struct.pack_into('<I',raw,3560,len(rows))
            for i in range(len(rows)):struct.pack_into('<iiQ',raw,4208+128*i,30+i,300,0x50000+8*i)
            return raw
        owner._send=Mock(side_effect=spawn)
        temporary=SimpleNamespace(close=Mock(),retain=Mock())
        with patch.object(source,'SessionScope',return_value=temporary),patch.object(source,'capture_matching',side_effect=AssertionError('post-save engine discovery')):
            result=owner.load(plan,self.expected(),asset_preparation=prepared)
        self.assertEqual(result['objects'],3);temporary.retain.assert_not_called()
    def test_changed_pawn_rejects_cached_metadata_before_native_initialization(self):
        owner=self.owner();owner._send=Mock();expected=self.expected()
        with patch.object(source,'context',return_value=dict(expected,pawn=[2,23,0x20000])):
            with self.assertRaisesRegex(RuntimeError,'changed'):owner._prepare(expected)
        owner._send.assert_not_called();self.assertFalse(owner.started)
    def test_duplicate_local_possession_rejects_before_native_initialization(self):
        owner=self.owner();owner._send=Mock();expected=self.expected()
        pawn=SimpleNamespace(index=2,serial=22,address=0x20000)
        world=SimpleNamespace(index=1,serial=11,address=0x10000)
        controllers=[SimpleNamespace(index=i,object_flags=0) for i in (3,4)]
        pcs=SimpleNamespace(select=lambda _:controllers)
        values=SimpleNamespace(values={(0,'Pawn'):pawn,(0,'bIsLocalPlayerController'):True})
        with patch.object(source,'context',return_value=expected),patch.object(source,'ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_selected',return_value=SimpleNamespace(by_index={1:world,2:pawn})),patch.object(source,'capture_matching',return_value=pcs),patch.object(source,'read_values_with_references',return_value=(values,pcs)):
            with self.assertRaisesRegex(RuntimeError,'local controller'):owner._prepare(expected)
        owner._send.assert_not_called();self.assertFalse(owner.started)

    def test_selected_controller_avoids_unrelated_registry_objects(self):
        owner=self.owner();owner._send=Mock()
        expected=dict(self.expected(),controller=[3,33,0x30000])
        pawn=SimpleNamespace(index=2,serial=22,address=0x20000)
        world=SimpleNamespace(index=1,serial=11,address=0x10000)
        pc=SimpleNamespace(index=3,serial=33,address=0x30000,object_flags=0)
        catalog=SimpleNamespace(by_index={1:world,2:pawn,3:pc})
        values=SimpleNamespace(values={(0,'Pawn'):pawn,(0,'bIsLocalPlayerController'):True},errors=(),truncated=False)
        with patch.object(source,'context',side_effect=AssertionError('redundant global discovery')),patch.object(source,'ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_selected',return_value=catalog) as selected,patch.object(source,'capture_matching',side_effect=AssertionError('retired unrelated object')),patch.object(source,'read_values_with_references',return_value=(values,catalog)):
            owner._prepare(expected)
        selected.assert_called_once_with(123,((1,11,0x10000),(2,22,0x20000),(3,33,0x30000)))
        owner._send.assert_called_once_with(93,ids=[pc,pawn,world,*range(14)])
        self.assertTrue(owner.started);self.assertEqual(owner.visit,expected['visit'])

    def test_selected_controller_rejects_stale_or_partial_possession_before_dispatch(self):
        for changed in ('pawn','local','errors','truncated','retired'):
            with self.subTest(changed=changed):
                owner=self.owner();owner._send=Mock()
                expected=dict(self.expected(),controller=[3,33,0x30000])
                pawn=SimpleNamespace(index=2,serial=22,address=0x20000)
                pc=SimpleNamespace(index=3,serial=33,address=0x30000,object_flags=0x20 if changed=='retired' else 0)
                catalog=SimpleNamespace(by_index={1:object(),2:pawn,3:pc})
                observed=SimpleNamespace(index=2,serial=23,address=0x20000) if changed=='pawn' else pawn
                values=SimpleNamespace(values={(0,'Pawn'):observed,(0,'bIsLocalPlayerController'):changed!='local'},errors=('failed',) if changed=='errors' else (),truncated=changed=='truncated')
                with patch.object(source,'ReadBatch',side_effect=lambda _:nullcontext()),patch('expedition33.catalog.capture_selected',return_value=catalog),patch.object(source,'read_values_with_references',return_value=(values,catalog)):
                    with self.assertRaisesRegex(RuntimeError,'possession changed'):owner._prepare(expected)
                owner._send.assert_not_called();self.assertFalse(owner.started)


if __name__=='__main__':unittest.main()
