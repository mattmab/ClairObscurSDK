import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33 import RuntimeQueryError
from expedition33 import story_layers as source


class SelectorTests(unittest.TestCase):
    def setUp(self):
        objects=[];classes={};next_index=iter(range(1,100))
        def obj(name,kind,parent=None):
            i=next(next_index);cls=classes.setdefault(kind,N(index=100+len(classes),path='/Script/Engine.'+kind))
            row=N(index=i,serial=1,address=0x10000+i*8,name=name,class_name=kind,class_index=cls.index,
                object_flags=0,outer_index=parent.index if parent else -1,outer_serial=1 if parent else 0,
                path=(parent.path+(':' if parent.class_name=='World' else '.') if parent else '')+name)
            objects.append(row);return row
        self.world=obj('/Game/W.W','World');self.level=obj('PersistentLevel','Level',self.world)
        self.settings=obj('WorldSettings','WorldSettings',self.level);self.partition=obj('WorldPartition_0','WorldPartition',self.settings)
        self.manager=obj('DataLayerManager','DataLayerManager',self.partition);self.container=obj('WorldDataLayers','WorldDataLayers',self.level)
        self.floor=obj('Floor','DataLayerInstanceWithAsset',self.container);self.garden=obj('Garden','DataLayerInstanceWithAsset',self.container)
        self.catalog=N(pid=1,objects=objects,path_name=lambda o:o.path,by_index={o.index:o for o in (*objects,*classes.values())})
        def chain(o):
            result=[o]
            while result[0].outer_index!=-1:result.insert(0,self.catalog.by_index[result[0].outer_index])
            return result
        self.catalog.outer_chain=chain
        self.ctx=dict(world=self.world.path,visit=list(source._identity(self.world)))
        self.scope=N(pid=1,_world_binding_token=((1,*self.ctx['visit']),(1,90,1,0x20000),(1,91,1,0x21000),2),_session=N())
        self.fields={self.world.index:dict(PersistentLevel=self.level),
            self.level.index:dict(OwningWorld=self.world,WorldSettings=self.settings,WorldDataLayers=self.container),
            self.settings.index:dict(WorldPartition=self.partition),self.partition.index:dict(DataLayerManager=self.manager)}
        def read(c,objects,fields):
            return {o.index:N(values={(o.class_index,n):v for n,v in self.fields[o.index].items()},errors={},truncated=False) for o in objects},c
        self.read=self.enterContext(patch('expedition33.values.read_values_many_with_references',side_effect=read))
        self.scan=self.enterContext(patch.object(source,'capture_matching',return_value=self.catalog))
        self.selected=self.enterContext(patch.object(source,'capture_selected',return_value=self.catalog))
    def discover(self,names):return source._discover_layers(self.scope,self.ctx,names,object())
    def test_different_exact_names_reuse_current_world_selectors_with_fresh_roots(self):
        self.assertEqual(self.discover(('Floor',))[2],'registry and root graph')
        self.assertEqual(self.discover(('Garden',))[2],'active-world selectors')
        self.scan.assert_called_once_with(1,classes=('DataLayerManager','DataLayerInstanceWithAsset'))
        self.selected.assert_called_once_with(1,(source._identity(self.manager),source._identity(self.garden)))
        self.assertEqual(self.read.call_count,2)
        self.assertEqual(set(self.scope._session._story_layer_selectors),{'binding','manager','layers'})
    def test_new_save_token_requires_discovery_even_when_world_identity_matches(self):
        self.discover(('Floor',));token=self.scope._world_binding_token
        self.scope._world_binding_token=(*token[:3],3)
        self.assertEqual(self.discover(('Floor',))[2],'registry and root graph')
        self.assertEqual(self.scan.call_count,2);self.selected.assert_not_called()
    def test_replaced_root_graph_rejects_cached_manager_without_fallback(self):
        self.discover(('Floor',));self.fields[self.partition.index]['DataLayerManager']=self.floor
        with self.assertRaisesRegex(RuntimeError,'root binding changed'):self.discover(('Garden',))
        self.scan.assert_called_once();self.assertIsNone(self.scope._session._story_layer_selectors)
    def test_stale_identity_clears_selector_cache_and_yields_before_rediscovery(self):
        self.discover(('Floor',));self.selected.side_effect=RuntimeQueryError('stale selected serial')
        with self.assertRaisesRegex(RuntimeQueryError,'stale selected'):self.discover(('Garden',))
        self.scan.assert_called_once();self.assertIsNone(self.scope._session._story_layer_selectors)
        self.selected.side_effect=None
        self.assertEqual(self.discover(('Garden',))[2],'registry and root graph')
    def test_wrong_binding_or_instance_container_never_resolves_by_nearby_name(self):
        self.scope._world_binding_token=((1,99,1,0x30000),*self.scope._world_binding_token[1:])
        with self.assertRaisesRegex(RuntimeError,'another admitted world'):self.discover(('Floor',))
        self.scan.assert_not_called()
        self.scope._world_binding_token=((1,*self.ctx['visit']),*self.scope._world_binding_token[1:])
        self.floor.outer_index=self.level.index
        with self.assertRaisesRegex(RuntimeError,'Exact current-world'):self.discover(('Floor',))
    def test_incomplete_root_observation_cannot_become_a_cached_success(self):
        del self.fields[self.level.index]['OwningWorld']
        with self.assertRaisesRegex(RuntimeError,'incomplete'):self.discover(('Floor',))
        self.assertIsNone(self.scope._session._story_layer_selectors)


class EarlySelectorTests(SelectorTests):
    def setUp(self):
        super().setUp()
        self.scope._check=Mock()
        def obj(index,kind):
            cls=N(index=index+200,path='/Script/Engine.'+kind)
            value=N(index=index,serial=1,address=0x10000+index*8,class_name=kind,class_index=cls.index,
                    object_flags=0,path=kind)
            self.catalog.by_index.update({index:value,cls.index:cls})
            return value
        self.engine=obj(50,'GameEngine');self.viewport=obj(51,'GameViewportClient');self.gi=obj(90,'BP_jRPG_GI_Custom_C')
        self.scope._world_binding_token=(self.scope._world_binding_token[0],(1,*source._identity(self.gi)),*self.scope._world_binding_token[2:])
        self.ui=N(kind='world',world=(1,*source._identity(self.world)),gi=(1,*source._identity(self.gi)))
        self.catalog.ancestors=lambda cls:(cls,)
        classes={obj.class_name:self.catalog.by_index[obj.class_index] for obj in (self.engine,self.viewport,self.world,self.gi)}
        self.catalog.find_class=lambda kind:classes[kind]
        self.scope._session._story_construction_resources=N(session=self.scope._session,engine=self.engine,viewport=self.viewport)
        self.active={o.index:N(types={(o.class_index,name):'ObjectProperty'},
                values={(o.class_index,name):target},errors={},truncated=set())
            for o,name,target in ((self.engine,'GameViewport',self.viewport),(self.viewport,'World',self.world),
                                  (self.world,'OwningGameInstance',self.gi))}
        self.active_read=self.enterContext(patch('expedition33.values.capture_selected_values',return_value=(self.catalog,self.active)))
    def prepare(self):return source.prepare_layer_selectors(self.scope,self.ui)
    def test_early_inventory_is_only_selectors_and_admitted_use_revalidates_roots(self):
        self.assertTrue(self.prepare());self.assertTrue(self.prepare())
        self.active_read.assert_called_once();self.scan.assert_called_once();self.read.assert_called_once()
        saved=self.scope._session._story_layer_prepared_selectors
        self.assertEqual(set(saved),{'binding','manager','layers'})
        self.assertEqual(saved['binding'],(self.ui.world,self.ui.gi))
        self.assertFalse(hasattr(self.scope._session,'_story_layer_selectors'))
        self.assertEqual(self.discover(('Floor',))[2],'loading-prepared selectors')
        self.selected.assert_called_once_with(1,(source._identity(self.manager),source._identity(self.floor)))
        self.assertEqual(self.read.call_count,2)
        self.assertEqual(self.discover(('Garden',))[2],'active-world selectors')
        self.assertEqual(self.read.call_count,3);self.scan.assert_called_once()
    def test_early_unbound_scope_cannot_bypass_later_admission(self):
        token=self.scope._world_binding_token;self.scope._world_binding_token=None
        self.assertTrue(self.prepare())
        self.scope._world_binding_token=((1,99,1,0x30000),*token[1:])
        with self.assertRaisesRegex(RuntimeError,'another admitted world'):self.discover(('Floor',))
        self.selected.assert_not_called()
    def test_current_engine_link_must_match_supplied_world_before_discovery(self):
        self.active[self.viewport.index].values[(self.viewport.class_index,'World')]=self.gi
        with self.assertRaisesRegex(source.LayerSelectorsPending,'active context changed'):self.prepare()
        self.scan.assert_not_called();self.assertIsNone(self.scope._session._story_layer_prepared_selectors)
    def test_bootstrap_without_current_manager_defers_without_cache(self):
        self.catalog.objects.remove(self.manager)
        self.assertFalse(self.prepare());self.read.assert_not_called()
        self.assertIsNone(self.scope._session._story_layer_prepared_selectors)
    def test_incomplete_early_roots_are_pending_without_planning_or_cache(self):
        del self.fields[self.level.index]['OwningWorld']
        with self.assertRaises(source.LayerSelectorsPending):self.prepare()
        self.assertIsNone(self.scope._session._story_layer_prepared_selectors)
    def test_early_selector_never_skips_admitted_root_revalidation(self):
        self.prepare();self.fields[self.partition.index]['DataLayerManager']=self.floor
        with self.assertRaisesRegex(RuntimeError,'root binding changed'):self.discover(('Floor',))
        self.scan.assert_called_once();self.assertIsNone(self.scope._session._story_layer_prepared_selectors)
    def test_different_game_instance_cannot_consume_early_selectors(self):
        self.prepare();token=self.scope._world_binding_token
        self.scope._world_binding_token=(token[0],(1,99,1,0x30000),*token[2:])
        self.assertEqual(self.discover(('Floor',))[2],'registry and root graph')
        self.assertEqual(self.scan.call_count,2);self.selected.assert_not_called()
    def test_wrong_process_title_and_cross_session_have_no_discovery(self):
        self.ui.kind='title';self.assertFalse(self.prepare())
        self.ui.kind='world';self.ui.gi=(2,*self.ui.gi[1:])
        with self.assertRaisesRegex(RuntimeError,'process changed'):self.prepare()
        self.ui.gi=(1,*self.ui.gi[1:]);self.scope._session._story_construction_resources.session=object()
        with self.assertRaisesRegex(RuntimeError,'another session'):self.prepare()
        self.scan.assert_not_called();self.active_read.assert_not_called()

    def test_background_inventory_is_immutable_once_per_world_and_not_a_session(self):
        observer=source.LayerSelectorObserver(1)
        chain=(self.engine,self.viewport,self.world,self.gi)
        snapshot=observer.observe(self.catalog,chain)
        self.assertIsInstance(snapshot,source.LayerSelectorSnapshot)
        self.assertIs(observer.observe(self.catalog,chain),snapshot)
        self.scan.assert_called_once();self.read.assert_called_once();self.scope._check.assert_not_called()
        self.assertIsInstance(snapshot.layers,tuple)
        with self.assertRaises(AttributeError):snapshot.manager=(1,2,3)
        self.assertTrue(source.adopt_layer_selectors(self.scope,snapshot,self.ui))
        self.assertEqual(self.discover(('Floor',))[2],'loading-prepared selectors')
        self.assertEqual(self.read.call_count,2);self.scan.assert_called_once()

    def test_background_inventory_waits_for_roots_then_retries_only_after_deadline(self):
        observer=source.LayerSelectorObserver(1);chain=(self.engine,self.viewport,self.world,self.gi)
        missing=self.fields[self.level.index].pop('OwningWorld')
        with patch.object(source.time,'monotonic',side_effect=(1.,1.1,1.51)):
            self.assertIsNone(observer.observe(self.catalog,chain));self.fields[self.level.index]['OwningWorld']=missing
            self.assertIsNone(observer.observe(self.catalog,chain));self.scan.assert_called_once()
            self.assertIsNotNone(observer.observe(self.catalog,chain));self.assertEqual(self.scan.call_count,2)

    def test_background_inventory_new_world_does_not_publish_old_selectors(self):
        observer=source.LayerSelectorObserver(1);chain=(self.engine,self.viewport,self.world,self.gi)
        self.assertIsNotNone(observer.observe(self.catalog,chain))
        other=N(index=99,serial=1,address=0x50000,path='/Game/Levels/Map_Game_Bootstrap.Map_Game_Bootstrap')
        self.assertIsNone(observer.observe(self.catalog,(self.engine,self.viewport,other,self.gi)))
        self.assertIsNone(observer.snapshot);self.scan.assert_called_once()

    def test_snapshot_rejects_mutable_rows_and_wrong_destination_cannot_adopt(self):
        snapshot=source.LayerSelectorSnapshot(self.ui.world,self.ui.gi,source._identity(self.manager),
            (('Floor',source._identity(self.floor)),))
        other=N(kind='world',world=(1,99,1,0x50000),gi=self.ui.gi)
        self.assertFalse(source.adopt_layer_selectors(self.scope,snapshot,other))
        self.assertFalse(hasattr(self.scope._session,'_story_layer_prepared_selectors'))
        with self.assertRaises(ValueError):
            source.LayerSelectorSnapshot(self.ui.world,self.ui.gi,source._identity(self.manager),[['Floor',(1,2,3)]])


if __name__=='__main__':unittest.main()
