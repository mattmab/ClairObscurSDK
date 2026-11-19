import unittest
from unittest.mock import patch,Mock
from types import SimpleNamespace
from expedition33.story_layers import StoryDataLayers

class Catalog:
    def __init__(self,objects):self.pid=1;self.objects=objects
    def path_name(self,obj):return obj.path
    def find_path(self,path):return path
    def with_observations(self,other):return self

class Call:
    def __init__(self,value=None,error=None):self.value=value;self.error=error;self.count=0
    def invoke(self):
        self.count+=1
        if self.error:raise self.error
        return self
    def __enter__(self):return SimpleNamespace(return_value=self.value)
    def __exit__(self,*args):pass

class LayerTests(unittest.TestCase):
    def test_capable_owner_batches_original_state_before_preparing_any_setters(self):
        o,ctx,catalog,planner,read,setters,construction=self.preparation(warm=True)
        o.scope._session._transport=SimpleNamespace(story_layer_batch_protocol=1)
        ctx['controller']=[10,20,0x10000]
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog),patch('expedition33.story_layer_batch.execute',return_value=(SimpleNamespace(value=0),)) as batch:
            o.prepare(ctx,{'Floor':2})
        batch.assert_called_once_with(o.scope,(1,2,3),(10,20,0x10000),(read,))
        self.assertEqual(read.count,0);self.assertEqual(len(setters),3)
        self.assertEqual(o.rows[0]['previous'],0);self.assertEqual(o.state,'prepared')

    def test_failed_original_state_batch_has_no_setter_plans_and_is_not_replayed(self):
        from expedition33._story_layer_batch_wire import LayerBatchError
        o,ctx,catalog,planner,read,setters,construction=self.preparation(warm=True)
        o.scope._session._transport=SimpleNamespace(story_layer_batch_protocol=1);ctx['controller']=[10,20,0x10000]
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog),patch('expedition33.story_layer_batch.execute',side_effect=LayerBatchError(4332,unknown=True)) as batch:
            with self.assertRaises(LayerBatchError):o.prepare(ctx,{'Floor':2})
            with self.assertRaisesRegex(RuntimeError,'Fresh scene owner'):o.prepare(ctx,{'Floor':2})
        self.assertEqual(batch.call_count,1);self.assertFalse(setters);self.assertFalse(o.rows);self.assertTrue(o.unknown)

    def test_setter_prefix_records_only_acknowledged_effects_and_preserves_untouched_tail(self):
        from expedition33._story_layer_batch_wire import LayerBatchError
        for outcome,data in (('unknown',b''),('dispatch_returned',b'\0'),('not_dispatched',b'')):
            o,row=self.owner();o.state='prepared';o._batch_controller=(10,20,0x10000)
            o.rows=[]
            for _ in range(3):
                setter=Call(True);setter._plan=SimpleNamespace(return_offset=0)
                o.rows.append(dict(get=Call(SimpleNamespace(value=0)),set=setter,previous=0,wanted=2,attempted=False,applied=False))
            receipts=(SimpleNamespace(outcome='dispatch_returned',error=0,data=b'\1'),
                      SimpleNamespace(outcome=outcome,error=0 if outcome=='dispatch_returned' else 201,data=data))
            error=LayerBatchError(4332 if outcome=='unknown' else 4331,receipts,unknown=outcome=='unknown')
            with patch('expedition33.story_layer_batch.execute',side_effect=error) as batch:
                with self.assertRaises(LayerBatchError):o.apply()
                with self.assertRaises(RuntimeError):o.apply()
            batch.assert_called_once();self.assertTrue(o.unknown);self.assertFalse(o.close())
            self.assertEqual([r['applied'] for r in o.rows],[True,False,False])
            self.assertEqual([r['attempted'] for r in o.rows],[True,outcome!='not_dispatched',False])

    def test_apply_batches_only_changed_states_and_readiness_observes_all_layers(self):
        o,row=self.owner();o.state='prepared';o._batch_controller=(10,20,0x10000);row['attempted']=row['applied']=False
        unchanged=dict(get=Call(SimpleNamespace(value=2)),set=Call(True),previous=2,wanted=2,attempted=False,applied=False)
        o.rows.append(unchanged)
        with patch('expedition33.story_layer_batch.execute',side_effect=((True,),(SimpleNamespace(value=2),SimpleNamespace(value=1)),(SimpleNamespace(value=2),SimpleNamespace(value=2)))) as batch:
            o.apply();self.assertFalse(o.requested_ready());self.assertTrue(o.requested_ready())
        self.assertEqual(batch.call_args_list[0].args[-1],(row['set'],))
        self.assertEqual(batch.call_args_list[1].args[-1],(row['get'],unchanged['get']))
        self.assertTrue(row['applied']);self.assertFalse(unchanged['applied'])
        self.assertEqual(row['set'].count,0);self.assertEqual(unchanged['set'].count,0)

    def test_failed_readiness_query_is_not_retried_or_reported_ready(self):
        from expedition33._story_layer_batch_wire import LayerBatchError
        o,row=self.owner();o._batch_controller=(10,20,0x10000)
        with patch('expedition33.story_layer_batch.execute',side_effect=LayerBatchError(4330)) as batch:
            with self.assertRaises(LayerBatchError):o.requested_ready()
            self.assertFalse(o.requested_ready())
        batch.assert_called_once();self.assertTrue(o.unknown)

    def preparation(self,*,warm):
        o=object.__new__(StoryDataLayers);o.state='new';o.rows=[];o.unknown=False;o.timings={}
        ctx={'ready':True,'visit':[1,2,3],'world':'/Game/Current.Current'}
        manager=SimpleNamespace(class_name='DataLayerManager',name='Manager',path=ctx['world']+':Manager')
        layer=SimpleNamespace(class_name='DataLayerInstanceWithAsset',name='Floor',path=ctx['world']+':Layers.Floor')
        other=SimpleNamespace(class_name='DataLayerInstanceWithAsset',name='Floor',path='/Game/Other.Other:Layers.Floor')
        catalog=Catalog([manager,layer,other])
        planner=Mock();read=Call(SimpleNamespace(value=0));setters=[]
        def prepare(target,function,**arguments):
            self.assertIs(target,manager);self.assertIs(arguments['InDataLayerInstance'],layer)
            if function.endswith(':GetDataLayerInstanceRuntimeState'):return read
            self.assertFalse(arguments['bInIsRecursive'])
            result=Call(True);setters.append((arguments['InState'].value,result));return result
        planner.prepare.side_effect=prepare
        typed={n:SimpleNamespace(value=n) for n in (0,1,2)}
        construction=SimpleNamespace(catalog=Mock(return_value=object()),layer_values=typed,
                                     movement_planner=Mock(return_value=planner)) if warm else None
        o.scope=SimpleNamespace(pid=1,_session=SimpleNamespace(_story_construction_resources=construction),
                                invocation_planner=Mock(return_value=planner),close=Mock())
        return o,ctx,catalog,planner,read,setters,construction
    def test_warm_preparation_matches_exact_names_and_reuses_unique_setters(self):
        o,ctx,catalog,planner,read,setters,construction=self.preparation(warm=True)
        with patch('expedition33.story_layers.context',return_value=ctx) as context,patch('expedition33.story_layers.capture_matching',return_value=catalog) as discover,patch('expedition33.story_layers.describe_enums') as enum:
            o.prepare(ctx,{'Floor':2})
        context.assert_called_once_with(o.scope,require_bound_world=True)
        self.assertEqual(discover.call_args.kwargs,dict(classes=('DataLayerManager',),names=('Floor',)))
        enum.assert_not_called();o.scope.invocation_planner.assert_not_called()
        construction.catalog.assert_called_once();construction.movement_planner.assert_called_once_with(o.scope,catalog)
        self.assertEqual(planner.prepare.call_count,4);self.assertEqual(read.count,1)
        row=o.rows[0];self.assertIs(row['set'],row['states'][2]);self.assertIs(row['restore'],row['states'][0])
        self.assertEqual([value for value,_ in setters],[0,1,2])
    def test_unprepared_generic_scope_keeps_context_discovery_and_changed_world_rejects_before_scan(self):
        for warm in (False,True):
            with self.subTest(warm=warm):
                o,ctx,catalog,planner,_,_,_=self.preparation(warm=warm)
                with patch('expedition33.story_layers.context',return_value=dict(ctx,visit=[4,5,6])) as context, \
                        patch('expedition33.story_layers.capture_matching') as discover:
                    with self.assertRaisesRegex(RuntimeError,'world changed'):o.prepare(ctx,{'Floor':2})
                context.assert_called_once_with(o.scope,require_bound_world=warm)
                discover.assert_not_called();planner.prepare.assert_not_called()
    def test_deduplicated_plans_apply_transition_and_restore_exact_states(self):
        o,ctx,catalog,_,read,setters,_=self.preparation(warm=True)
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog):
            o.prepare(ctx,{'Floor':2});o.apply()
            read.value=SimpleNamespace(value=2);o.transition({'Floor':1})
            read.value=SimpleNamespace(value=1);self.assertTrue(o.close())
        self.assertEqual({value:call.count for value,call in setters},{0:1,1:1,2:1})
    def test_same_name_in_different_world_is_not_selected(self):
        o,ctx,catalog,planner,_,_,_=self.preparation(warm=True)
        catalog.objects=[obj for obj in catalog.objects if obj.path!=ctx['world']+':Layers.Floor']
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog):
            with self.assertRaisesRegex(RuntimeError,'Exact data-layer instance required'):o.prepare(ctx,{'Floor':2})
        planner.prepare.assert_not_called()
    def test_ambiguous_current_world_manager_is_rejected(self):
        o,ctx,catalog,planner,_,_,_=self.preparation(warm=True)
        catalog.objects.append(SimpleNamespace(class_name='DataLayerManager',name='Manager2',path=ctx['world']+':Manager2'))
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog):
            with self.assertRaisesRegex(RuntimeError,'One current-world layer manager required'):o.prepare(ctx,{'Floor':2})
        planner.prepare.assert_not_called()
    def test_changed_retained_metadata_cannot_fall_back_to_new_discovery(self):
        o,ctx,catalog,planner,_,_,construction=self.preparation(warm=True)
        construction.catalog.side_effect=RuntimeError('identity changed')
        with patch('expedition33.story_layers.context',return_value=ctx),patch('expedition33.story_layers.capture_matching',return_value=catalog) as discover:
            with self.assertRaisesRegex(RuntimeError,'identity changed'):o.prepare(ctx,{'Floor':2})
        discover.assert_called_once();planner.prepare.assert_not_called()
    def owner(self,current=2):
        o=object.__new__(StoryDataLayers);o.scope=SimpleNamespace(close=lambda:True);o.planner=SimpleNamespace(close=lambda:True)
        o.visit=(1,2,3);o.state='active';o.unknown=False
        row=dict(get=Call(SimpleNamespace(value=current)),restore=Call(True),set=Call(True),previous=0,wanted=2,attempted=True,applied=True)
        o.rows=[row];return o,row
    def test_restore_only_owned_requested_state(self):
        for current,calls in ((2,1),(1,0)):
            o,row=self.owner(current)
            with patch('expedition33.story_layers.context',return_value={'visit':[1,2,3]}):self.assertTrue(o.close())
            self.assertEqual(row['restore'].count,calls);self.assertEqual(o.state,'closed')
    def test_world_change_and_missing_observation_never_restore(self):
        for ctx in (None,{'visit':[4,5,6]}):
            o,row=self.owner()
            with patch('expedition33.story_layers.context',return_value=ctx):self.assertFalse(o.close())
            self.assertEqual(row['restore'].count,0)
    def test_unknown_apply_retains_owners_without_replay(self):
        o,row=self.owner();o.state='prepared';row['applied']=False;row['set']=Call(error=RuntimeError('unknown dispatch'))
        with self.assertRaises(RuntimeError):o.apply()
        self.assertTrue(o.unknown);self.assertFalse(o.close())
        with self.assertRaises(RuntimeError):o.apply()
        self.assertEqual(row['set'].count,1)
    def test_retirement_requires_positive_replacement_world(self):
        o,row=self.owner()
        with patch('expedition33.story_layers.context',return_value=None):self.assertFalse(o.retire_world())
        with patch('expedition33.story_layers.context',return_value={'visit':[4,5,6]}):self.assertTrue(o.retire_world())
        self.assertEqual(row['restore'].count,0)
