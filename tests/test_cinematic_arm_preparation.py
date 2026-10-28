import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.title_adapters import OwnedSequenceContext,prepare_widgets,WIDGET_ROUTING_CLASS

class CinematicArmPreparationTests(unittest.TestCase):
 def test_prepared_routing_identity_is_freshly_checked_and_retained_before_factory(self):
  routing=N(index=1,serial=2,address=0x10000,class_name='BlueprintGeneratedClass')
  scope=Mock(pid=7);sequence=N(scope=scope)
  catalog=N(by_index={1:routing},path_name=lambda obj:WIDGET_ROUTING_CLASS)
  prefix='expedition33.cinematics.title_adapters.'
  with patch(prefix+'capture_selected',return_value=catalog) as selected,\
       patch(prefix+'prepare_widget_routing') as load,\
       patch(prefix+'capture_matching',side_effect=RuntimeError('before factory')):
   with self.assertRaisesRegex(RuntimeError,'before factory'):
    prepare_widgets(sequence,retain_track_class=True,routing_class=routing)
  selected.assert_called_once_with(7,((1,2,0x10000),))
  scope.retain.assert_called_once_with(routing);load.assert_not_called()
  scope.retain.reset_mock()
  for path,kind in (('/Game/Other.Other_C','BlueprintGeneratedClass'),(WIDGET_ROUTING_CLASS,'Object')):
   routing.class_name=kind;catalog.path_name=lambda obj:path
   with patch(prefix+'capture_selected',return_value=catalog),patch(prefix+'capture_matching') as factory:
    with self.assertRaisesRegex(RuntimeError,'routing class changed'):
     prepare_widgets(sequence,retain_track_class=True,routing_class=routing)
   factory.assert_not_called();scope.retain.assert_not_called()

 def test_widget_factory_timings_follow_actual_dependencies_without_changing_inputs(self):
  names=('BP_CinematicSystem_C','Default__GameplayStatics','GameplayStatics','SpawnObject',
   'GetCinematicsSystem','GetComponentByClass','Default__FL_jRPG_CustomFunctionLibrary_C',
   'ExecuteUbergraph_BP_WidgetSequencerTrackInstance','BP_WidgetSequencerTrackInstance_C',
   'UserWidget','Default__UserWidget','RegisterSpawnedWidget','UnregisterSpawnedWidget',
   'UpdateCinematicControlsWidget','RemoveFromParent')
  rows=[N(name=name,index=i+1,class_name='Object',outer_index=0) for i,name in enumerate(names)]
  by_name={row.name:row for row in rows}
  by_name['BP_CinematicSystem_C'].class_name='BlueprintGeneratedClass'
  by_name['GameplayStatics'].class_name='Class'
  by_name['SpawnObject'].outer_index=by_name['GameplayStatics'].index
  gi=N(name='GI',index=90)
  catalog=N(objects=rows,select=lambda kind:[gi])
  component=N(class_index=by_name['BP_CinematicSystem_C'].index,outer_index=gi.index)
  plan=object();events=[]
  planner=Mock(_catalog=catalog)
  def prepare(target,function,**kwargs):
   if function is by_name['SpawnObject']:
    events.append('factory')
    self.assertIs(kwargs['Outer'],gi)
    return N(invoke=lambda **kw:N(return_value=component))
   events.append('remove_plan')
   self.assertIs(function,by_name['RemoveFromParent'])
   return N(_plan=plan)
  planner.prepare.side_effect=prepare
  scope=Mock(pid=7);scope.invocation_planner.return_value=planner
  player=object();sequence=N(scope=scope,player=player)
  owner=Mock()
  owner.prepare.side_effect=lambda resources,p,r:events.append('native_arm')
  prefix='expedition33.cinematics.title_adapters.'
  with patch(prefix+'capture_matching',return_value=catalog),patch(prefix+'NativeCinematicWidgets',return_value=owner):
   self.assertIs(prepare_widgets(sequence),owner)
  self.assertEqual(events,['factory','remove_plan','native_arm'])
  resources,p,r=owner.prepare.call_args.args
  self.assertIs(resources['component'],component);self.assertIs(p,player);self.assertIs(r,plan)
  timings=owner.latency.snapshot()['timings']
  self.assertEqual(set(timings),{'widgets.dependencies','widgets.component_factory','widgets.remove_plan'})
  for value in timings.values():
   self.assertEqual((value['count'],value['failed']),(1,0))
   self.assertGreaterEqual(value['last_ms'],0)

 def prepared_dependencies(self):
  from expedition33.cinematics.title_adapters import PreparedWidgetDependencies,WIDGET_DEPENDENCY_NAMES
  rows=[N(name=name,index=i+1,serial=2,address=0x10000+i*0x100) for i,name in enumerate(WIDGET_DEPENDENCY_NAMES)]
  gi=N(name='GI',index=90,serial=3,address=0x90000)
  catalog=N(objects=rows,select=lambda kind:[gi])
  scope=Mock(pid=7,_session=object())
  scope.retain.side_effect=lambda obj:N(object=obj,active=True)
  with patch('expedition33.cinematics.title_adapters.capture_matching',return_value=catalog) as discover:
   prepared=PreparedWidgetDependencies(scope)
  self.assertEqual(discover.call_count,1)
  self.assertEqual(len(prepared.leases),len(rows)+1)
  return prepared,scope

 def test_prepared_dependencies_refresh_selected_closure_every_play(self):
  prepared,scope=self.prepared_dependencies()
  prefix='expedition33.cinematics.title_adapters.'
  fresh1,fresh2=object(),object()
  with patch(prefix+'capture_selected',side_effect=(fresh1,fresh2)) as selected,patch(prefix+'capture_matching') as discovery:
   self.assertIs(prepared.capture(scope),fresh1)
   self.assertIs(prepared.capture(scope),fresh2)
  discovery.assert_not_called()
  selectors=tuple((lease.object.index,lease.object.serial,lease.object.address) for lease in prepared.leases)
  self.assertEqual(selected.call_args.args,(7,selectors))
  self.assertEqual(selected.call_count,2)

 def test_prepared_dependencies_reject_released_lease_and_other_session_before_read(self):
  prepared,scope=self.prepared_dependencies()
  with patch('expedition33.cinematics.title_adapters.capture_selected') as selected:
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):
    prepared.capture(Mock(pid=7,_session=object()))
   prepared.leases[0].active=False
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):prepared.capture(scope)
   selected.assert_not_called()

 def test_prepared_dependencies_do_not_fallback_to_discovery_on_changed_identity(self):
  prepared,scope=self.prepared_dependencies()
  prefix='expedition33.cinematics.title_adapters.'
  with patch(prefix+'capture_selected',side_effect=RuntimeError('identity changed')),patch(prefix+'capture_matching') as discovery:
   with self.assertRaisesRegex(RuntimeError,'identity changed'):prepared.capture(scope)
  discovery.assert_not_called()

 def context(self):
  value=object.__new__(OwnedSequenceContext)
  value.audio=Mock();value.audio.pause_original_audio.return_value=True
  value.widgets=None;value.closed=False;value._pause_plan=object();value.scope=Mock()
  return value
 def test_arm_reuses_scoped_plan_after_widgets_and_requires_native_ack(self):
  context=self.context();events=[];sequence=N(owner=object())
  context.audio.pause_original_audio.side_effect=lambda plan:events.append(('audio',plan)) or True
  with patch('expedition33.cinematics.title_adapters.prepare_widgets',side_effect=lambda *a,**kw:events.append(('widgets',kw)) or 'routes'):
   context.arm(sequence)
  self.assertEqual(events,[('widgets',{'retain_track_class':True}),('audio',context._pause_plan)])
  context.scope.invocation_planner.assert_not_called()
  self.assertIs(context._retirement_sequence_owner,sequence.owner)
  self.assertEqual(context.widgets,'routes')
 def test_missing_plan_rejects_before_any_widget_or_audio_mutation(self):
  context=self.context();context._pause_plan=None
  with patch('expedition33.cinematics.title_adapters.prepare_widgets') as widgets:
   with self.assertRaisesRegex(RuntimeError,'Prepare'):context.arm(Mock())
  widgets.assert_not_called();context.audio.pause_original_audio.assert_not_called()
 def test_failed_native_pause_ack_does_not_claim_success_or_discard_routes(self):
  context=self.context();context.audio.pause_original_audio.return_value=False
  with patch('expedition33.cinematics.title_adapters.prepare_widgets',return_value='routes'):
   with self.assertRaisesRegex(RuntimeError,'acknowledged'):context.arm(Mock())
  self.assertEqual(context.widgets,'routes')

if __name__=='__main__':unittest.main()
