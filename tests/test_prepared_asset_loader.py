import unittest
from types import SimpleNamespace as N
from unittest.mock import Mock,patch
from expedition33.assets import PreparedAssetLoader,load_asset

class PreparedAssetLoaderTests(unittest.TestCase):
 def fixture(self):
  rows=[N(name='KismetSystemLibrary',class_name='Class',index=1,serial=2,address=0x10000),
        N(name='Default__KismetSystemLibrary',class_index=1,index=3,serial=4,address=0x20000),
        N(name='LoadAsset_Blocking',outer_index=1,index=5,serial=6,address=0x30000)]
  scope=Mock(pid=7,_session=object())
  scope.retain.side_effect=lambda obj:N(active=True,object=obj)
  with patch('expedition33.assets.capture_matching',return_value=N(objects=rows)) as discover:
   prepared=PreparedAssetLoader(scope)
  self.assertEqual(discover.call_count,1);self.assertEqual(scope.retain.call_count,3)
  return prepared,scope
 def test_each_load_observes_fresh_selected_closure(self):
  prepared,scope=self.fixture();first,second=object(),object()
  with patch('expedition33.catalog.capture_selected',side_effect=(first,second)) as selected,patch('expedition33.assets.capture_matching') as discovery:
   self.assertIs(prepared.capture(scope),first);self.assertIs(prepared.capture(scope),second)
  self.assertEqual(selected.call_count,2)
  self.assertEqual(selected.call_args.args,(7,((1,2,0x10000),(3,4,0x20000),(5,6,0x30000))))
  discovery.assert_not_called()
 def test_retired_or_other_session_loader_cannot_be_used(self):
  prepared,scope=self.fixture()
  with patch('expedition33.catalog.capture_selected') as selected:
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):prepared.capture(Mock(pid=7,_session=object()))
   prepared.leases[1].active=False
   with self.assertRaisesRegex(RuntimeError,'no longer owned'):prepared.capture(scope)
   selected.assert_not_called()
 def test_identity_failure_does_not_trigger_discovery_fallback(self):
  prepared,scope=self.fixture()
  with patch('expedition33.catalog.capture_selected',side_effect=RuntimeError('identity changed')),patch('expedition33.assets.capture_matching') as discovery:
   with self.assertRaisesRegex(RuntimeError,'identity changed'):prepared.capture(scope)
  discovery.assert_not_called()
 def test_path_validation_still_precedes_prepared_loader_and_native_call(self):
  scope=Mock(_session=N(_transport=N(asset_load_protocol=1)))
  prepared=Mock()
  with self.assertRaisesRegex(ValueError,'canonical'):load_asset(scope,'/Game/Bad.Other',prepared=prepared)
  prepared.capture.assert_not_called()
  scope._session._transport=Mock(asset_load_protocol=0)
  with self.assertRaisesRegex(Exception,'capability|candidate runtime'):load_asset(scope,'/Game/Test.Test',prepared=prepared)
  prepared.capture.assert_not_called()
 def test_numbered_asset_requires_explicit_native_capability_before_metadata_or_dispatch(self):
  from expedition33.invocation import UnsupportedInvocation
  for cap in (0,None,True,2):
   scope=Mock(_session=N(_transport=N(asset_load_protocol=1,asset_name_number_protocol=cap)))
   prepared=Mock()
   names=dict(package_id=1,asset_id=2,package_number=3,asset_number=3)
   with patch('expedition33._asset_names.resolve',return_value=names):
    with self.assertRaisesRegex(UnsupportedInvocation,'Numbered asset names'):
     load_asset(scope,'/Game/Test_2.Test_2',prepared=prepared)
   prepared.capture.assert_not_called()

if __name__=='__main__':unittest.main()
