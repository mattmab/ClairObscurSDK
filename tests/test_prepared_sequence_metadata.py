import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33._sequence_metadata import PreparedSequenceMetadata,FUNCTIONS

class PreparedSequenceMetadataTests(unittest.TestCase):
 def fixture(self,zero=False,stable=False):
  rows=[]
  def add(name,kind,outer=0):
   obj=N(name=name,class_name=kind,index=len(rows)+1,serial=2,address=0x10000+len(rows)*0x100,outer_index=outer)
   rows.append(obj);return obj
  classes={name:add(name,'Class') for name in (*FUNCTIONS,'LevelSequenceActor')}
  for name in ('MovieSceneSequencePlaybackSettings','QualifiedFrameTime','FrameTime','FrameRate','FrameNumber'):add(name,'ScriptStruct')
  add('EViewTargetBlendFunction','Enum')
  for name in ('Default__LevelSequencePlayer','Default__LevelSequenceActor'):add(name,'Object')
  for owner,names in FUNCTIONS.items():
   for name in names:add(name,'Function',classes[owner].index)
  if zero:rows[-1].serial=0
  scope=Mock(pid=7,_session=N(_transport=N(stable_lease_protocol=1 if stable else 0)));scope.retain.side_effect=lambda obj:N(active=True,object=obj)
  with patch('expedition33._sequence_metadata.capture_matching',return_value=N(objects=rows)):
   prepared=PreparedSequenceMetadata(scope)
  return prepared,scope
 def test_zero_serial_is_stabilized_during_preparation_when_supported(self):
  def acquire(scope,obj):
   stable=N(**vars(obj));stable.serial=1001
   return N(active=True,object=stable),N()
  with patch('expedition33._sequence_metadata.acquire_stable',side_effect=acquire) as native:
   prepared,scope=self.fixture(zero=True,stable=True)
  self.assertEqual(native.call_count,1)
  self.assertEqual(prepared.unassigned,())
  with patch('expedition33._sequence_metadata.capture_selected',return_value='fresh') as selected,patch('expedition33._sequence_metadata.capture_matching') as discover:
   self.assertEqual(prepared.capture(scope,names=('Play',)),'fresh')
  self.assertEqual(selected.call_args.args[1][-1][1],1001)
  discover.assert_not_called()
 def test_positive_roots_are_retained_and_each_capture_is_fresh(self):
  prepared,scope=self.fixture();self.assertTrue(prepared.ready)
  self.assertEqual(scope.retain.call_count,len(prepared.leases))
  with patch('expedition33._sequence_metadata.capture_selected',side_effect=('before','after')) as selected,patch('expedition33._sequence_metadata.capture_matching') as discover:
   self.assertEqual(prepared.capture(scope,names=('Play',)),'before')
   self.assertEqual(prepared.capture(scope,names=('GetEndTime',)),'after')
  self.assertEqual(selected.call_count,2);discover.assert_not_called()
 def test_zero_serial_metadata_requires_fresh_discovery_across_factory(self):
  prepared,scope=self.fixture(zero=True);self.assertTrue(prepared.ready)
  self.assertIn('GetEndTime',prepared.unassigned)
  with patch('expedition33._sequence_metadata.capture_selected') as selected,patch('expedition33._sequence_metadata.capture_matching',side_effect=('before','after')) as discover:
   self.assertEqual(prepared.capture(scope,names=('Play',)),'before')
   self.assertEqual(prepared.capture(scope,names=('GetEndTime',)),'after')
  selected.assert_not_called()
  self.assertEqual(discover.call_count,2)
 def test_other_session_released_lease_and_changed_identity_reject(self):
  prepared,scope=self.fixture()
  with patch('expedition33._sequence_metadata.capture_selected') as selected:
   with self.assertRaisesRegex(RuntimeError,'another SDK'):prepared.capture(Mock(_session=object()),names=('Play',))
   prepared.leases[0].active=False
   with self.assertRaisesRegex(RuntimeError,'released'):prepared.capture(scope,names=('Play',))
   selected.assert_not_called()
  prepared.leases[0].active=True
  with patch('expedition33._sequence_metadata.capture_selected',side_effect=RuntimeError('changed')),patch('expedition33._sequence_metadata.capture_matching') as discover:
   with self.assertRaisesRegex(RuntimeError,'changed'):prepared.capture(scope,names=('Play',))
  discover.assert_not_called()

if __name__=='__main__':unittest.main()
