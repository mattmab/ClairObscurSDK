import importlib.util,io,sys,struct,unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result
runtime=module('expedition33.map_retirement_test',ROOT/'src/expedition33/map_runtime.py')
transport_module=module('expedition33.map_retirement_session_test',ROOT/'src/expedition33/_session.py')
def packet(error=0,state=0,count=0):
 raw=bytearray(runtime.SIZE);struct.pack_into('<4IQ',raw,0,3,98,error,state,123)
 struct.pack_into('<I',raw,3564,count);return bytes(raw)
class Tests(unittest.TestCase):
 def owner(self,cap=1):
  transport=SimpleNamespace(retired_world_cleanup_protocol=cap,map_runtime_protocol=1)
  scope=SimpleNamespace(_session=SimpleNamespace(_transport=transport),_check=lambda:None,_reference_owners=[])
  owner=runtime.MapRuntime(scope);owner.started=True;owner.visit=[1,2,3];owner.objects={'retained':object()}
  return owner
 def test_empty_op98_wire_is_bounded_and_not_a_scene_payload(self):
  runtime.validate_request(packet())
  malformed=bytearray(packet());malformed[88]=1
  with self.assertRaises(ValueError):runtime.validate_request(bytes(malformed))
  malformed=bytearray(packet());struct.pack_into('<I',malformed,0,7)
  with self.assertRaises(ValueError):runtime.validate_request(bytes(malformed))
 def test_pending_owner_preserves_rows_then_exact_ack_releases_bookkeeping(self):
  owner=self.owner();owner._send=Mock(side_effect=[packet(407,1,3),packet()])
  self.assertEqual(owner.retire_world(),'pending');self.assertTrue(owner.started);self.assertTrue(owner.objects)
  self.assertEqual(owner.retire_world(),'ack');self.assertFalse(owner.started);self.assertEqual(owner.objects,{})
  self.assertIsNone(owner.visit);self.assertEqual(owner.retire_world(),'ack');self.assertEqual(owner._send.call_count,2)
 def test_empty_owner_ack_sets_closed_marker_without_native_capability(self):
  owner=self.owner(0);owner.started=False;owner.objects={};owner._send=Mock()
  self.assertEqual(owner.retire_world(),'ack');self.assertTrue(owner._closed)
  owner._send.assert_not_called()
 def test_wire_roundtrip_accepts_only_exact_gcdeferred_ack(self):
  owner=self.owner();owner.scope._lease_context=lambda:nullcontext()
  calls=[]
  def command(name,sent):
   calls.append((name,sent));raw=bytearray(sent)
   struct.pack_into('<II',raw,8,407,1);struct.pack_into('<I',raw,3564,2)
   return {'mesh_packet':bytes(raw).hex()}
  owner.scope._session._transport.command=command
  self.assertEqual(owner.retire_world(),'pending');self.assertEqual(len(calls),1)
  self.assertEqual(calls[0][0],'mesh');runtime.validate_request(calls[0][1])
  self.assertEqual(struct.unpack_from('<I',calls[0][1],4)[0],98)

 def test_bad_ack_and_transport_failure_are_unknown_without_replay(self):
  for response in (packet(407,0,2),packet(0,1,0),packet(0,0,1),packet(407,1,6001),RuntimeError('transport unknown')):
   owner=self.owner();owner._send=Mock(side_effect=response if isinstance(response,Exception) else [response])
   self.assertEqual(owner.retire_world(),'unknown');self.assertTrue(owner.uncertain);self.assertTrue(owner.objects)
   self.assertEqual(owner.retire_world(),'unknown');owner._send.assert_called_once_with(98)
 def test_missing_or_wrong_type_capability_never_dispatches_or_closes(self):
  for cap in (0,False,True,2):
   owner=self.owner(cap);owner._send=Mock();owner.close=Mock()
   self.assertEqual(owner.retire_world(),'unknown');owner._send.assert_not_called();owner.close.assert_not_called()
 def transport(self,cap=1):
  target=object.__new__(transport_module.SessionTransport)
  target._check_thread=lambda:None;target._closed=False;target.mesh_protocol=3
  target.map_runtime_protocol=1;target.runtime_scene_protocol=7;target.retired_world_cleanup_protocol=cap
  target._process=SimpleNamespace(stdin=io.StringIO())
  target._read=lambda:dict(event='session_response',command='mesh',closed=False)
  return target
 def test_transport_routes_v3_op98_to_map_and_v7_op98_to_scene(self):
  target=self.transport()
  with patch.dict(sys.modules,{'expedition33.map_runtime':runtime}),patch('expedition33._runtime_scene_wire.validate_request') as scene:
   target.command('mesh',packet());scene.assert_not_called()
   raw=bytearray(packet());struct.pack_into('<I',raw,0,7)
   target.command('mesh',bytes(raw));scene.assert_called_once_with(bytes(raw),protocol=7,allow_retired=True)
 def test_transport_rejects_op98_without_capability_before_ipc(self):
  target=self.transport(0)
  with self.assertRaisesRegex(ValueError,'retired map'):target.command('mesh',packet())
  self.assertEqual(target._process.stdin.getvalue(),'')
if __name__=='__main__':unittest.main()
