import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.cinematics.title_adapters import PreparedMusicDependencies,retain_prepared_dependencies

class PreparedMusicDependencyTests(unittest.TestCase):
 def test_zero_serial_dependency_is_stabilized_before_it_is_reused(self):
  scope=Mock(_session=N(_transport=N(stable_lease_protocol=1)))
  zero=N(index=10,serial=0,address=0x10000);positive=N(index=11,serial=1002,address=0x20000)
  stable=N(active=True,object=N(index=10,serial=1001,address=zero.address))
  ordinary=N(active=True,object=positive);scope.retain.return_value=ordinary
  with patch('expedition33.cinematics.title_adapters.acquire_stable',return_value=(stable,N())) as acquire:
   leases=retain_prepared_dependencies(scope,(zero,positive))
  self.assertEqual(leases,(stable,ordinary));acquire.assert_called_once_with(scope,zero)
  scope.retain.assert_called_once_with(positive)
  self.assertEqual(leases[0].object.serial,1001)
 def test_uncertain_stable_acquisition_is_not_retried_as_an_ordinary_lease(self):
  scope=Mock(_session=N(_transport=N(stable_lease_protocol=1)))
  with patch('expedition33.cinematics.title_adapters.acquire_stable',side_effect=RuntimeError('unknown ownership')) as acquire:
   with self.assertRaisesRegex(RuntimeError,'unknown ownership'):retain_prepared_dependencies(scope,(N(serial=0),))
  acquire.assert_called_once();scope.retain.assert_not_called()
 def fixture(self):
  rows=[]
  def add(name,kind,outer=0):
   o=N(name=name,class_name=kind,index=len(rows)+1,serial=0,address=0x10000+len(rows)*0x100,outer_index=outer)
   rows.append(o);return o
  add('BP_InteractiveMusicSystem_C','BlueprintGeneratedClass')
  statics=add('GameplayStatics','Class');audio=add('AudioComponent','Class');component=add('ActorComponent','Class')
  add('S_InteractiveMusic','UserDefinedStruct')
  for name in ('Default__GameplayStatics','Default__AudioComponent'):add(name,'Object')
  for owner,name in ((statics,'SpawnObject'),(audio,'Stop'),(audio,'SetPaused'),(component,'K2_DestroyComponent')):add(name,'Function',owner.index)
  gi=add('CurrentGI','BP_jRPG_GI_Custom_C')
  gi_class=add('BP_jRPG_GI_Custom_C','BlueprintGeneratedClass');gi.class_index=gi_class.index
  constraint=add('PropertyConstraint','Class')
  inherited=add('InheritedOwner','Class')
  catalog=N(objects=rows,by_index={o.index:o for o in rows})
  metadata=N(catalog=catalog,descriptors={gi_class.index:N(
   owners=({'index':gi_class.index},{'index':inherited.index}),
   properties=({'property_class_index':constraint.index}, {'struct_index':constraint.index}))})
  scope=Mock(pid=7,_session=object());scope.retain.side_effect=lambda obj:N(active=True,object=obj)
  with patch('expedition33.cinematics.title_adapters.capture_matching',return_value=catalog),patch(
    'expedition33.reflection.describe_selected',return_value=metadata) as describe:
   dependencies=PreparedMusicDependencies(scope)
  describe.assert_called_once_with(7,((gi_class.index,gi_class.serial,gi_class.address),))
  self.assertEqual(scope.retain.call_count,15)
  self.assertEqual(len({lease.object.index for lease in dependencies.leases}),15)
  self.assertTrue({gi_class.index,constraint.index,inherited.index}<={lease.object.index for lease in dependencies.leases})
  return dependencies,scope
 def test_fresh_selection_each_play_without_reading_or_assigning_original_music(self):
  dependencies,scope=self.fixture()
  with patch('expedition33.cinematics.title_adapters.capture_selected',side_effect=('first','second')) as selected,patch('expedition33.cinematics.title_adapters.read_object_reference') as music,patch('expedition33.reflection.describe_selected') as describe:
   self.assertEqual(dependencies.capture(scope),'first');self.assertEqual(dependencies.capture(scope),'second')
  self.assertEqual(selected.call_count,2);music.assert_not_called()
  describe.assert_not_called()
  self.assertEqual(len(selected.call_args.args[1]),15)
  scope.invocation_planner.assert_not_called()
 def test_retired_lease_and_other_session_reject_before_selection(self):
  dependencies,scope=self.fixture()
  with patch('expedition33.cinematics.title_adapters.capture_selected') as selected:
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):dependencies.capture(Mock(_session=object()))
   dependencies.leases[0].active=False
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):dependencies.capture(scope)
   selected.assert_not_called()
 def test_changed_identity_has_no_discovery_fallback(self):
  dependencies,scope=self.fixture()
  with patch('expedition33.cinematics.title_adapters.capture_selected',side_effect=RuntimeError('changed')),patch('expedition33.cinematics.title_adapters.capture_matching') as discover:
   with self.assertRaisesRegex(RuntimeError,'changed'):dependencies.capture(scope)
  discover.assert_not_called()

if __name__=='__main__':unittest.main()
