import struct,unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace as N
from unittest.mock import Mock
from expedition33 import _battle_completion as c,_battle_parameter_wire as w
from expedition33._battle_parameter_owner import ParameterResearchOwner

class Tests(unittest.TestCase):
 def packet(self,result=1,state=2,owner=71):
  identities=tuple(v for i in range(4) for v in (i+1,1001+i,0x10000+i*256)) if state==2 else (0,)*12
  return c.PACKET.pack(c.MAGIC,1,result,state,owner,1 if state==2 else 0,*identities)
 def test_victory_and_defeat_are_explicit_immutable(self):
  for result,name in ((1,'victory'),(2,'defeat')):
   receipt=c.decode(self.packet(result),owner=71)
   self.assertEqual(receipt.result,name);self.assertEqual(receipt.world,(1,1001,0x10000))
   with self.assertRaises(FrozenInstanceError):receipt.result='victory'
 def test_pending_never_means_completed(self):
  for state in (1,3,4,5):
   self.assertIsNone(c.decode(self.packet(0,state),owner=71).result)
 def test_invalid_enum_context_owner_and_payload_rejected(self):
  for packet in (self.packet(0),self.packet(3),self.packet(4),self.packet(owner=72),self.packet()[:-1]):
   with self.assertRaises(ValueError):c.decode(packet,owner=71)
  packet=bytearray(self.packet());struct.pack_into('<i',packet,36,0)
  with self.assertRaises(ValueError):c.decode(bytes(packet),owner=71)
 def test_query_roundtrip_and_reserved_bytes(self):
  request=w.build_request(71,160);response=bytearray(request);struct.pack_into('<I',response,12,1)
  response[4096:4192]=self.packet();self.assertTrue(w.validate_response(request,bytes(response)))
  response[-1]=1
  with self.assertRaises(RuntimeError):w.validate_response(request,bytes(response))
 def test_tracking_flag_only_for_dispatch(self):
  identities=[N(index=i,serial=1001,address=0x10000+i*256) for i in range(6)]
  packet=w.build_request(71,130,identities,mode=1,anchor_owner=92,arena_policy=1,track_completion=True)
  self.assertEqual(struct.unpack_from('<I',packet,48)[0],1)
  with self.assertRaises(ValueError):w.build_request(71,160,track_completion=True)
 def test_cached_receipt_requires_fresh_native_context_validation(self):
  owner=ParameterResearchOwner.__new__(ParameterResearchOwner);owner._scope=N(_check=Mock())
  owner._tracks_completion=True;owner._attempted=True;owner._owner=71;owner._completion_receipt=None
  def response(payload):return bytes(4096)+payload+bytes(w.SIZE-4192)
  owner._command=Mock(side_effect=[response(self.packet()),response(self.packet(0,3)),response(self.packet(0,4))])
  first=owner.completion_receipt();self.assertEqual(first.result,'victory')
  self.assertIs(owner.completion_receipt(),first)
  self.assertIsNone(owner.completion_receipt().result)
  self.assertEqual(owner._command.call_count,3)
 def test_no_tracking_no_query(self):
  owner=ParameterResearchOwner.__new__(ParameterResearchOwner);owner._scope=N(_check=Mock())
  owner._tracks_completion=False;owner._attempted=True;owner._command=Mock()
  with self.assertRaisesRegex(RuntimeError,'No tracked'):owner.completion_receipt()
  owner._command.assert_not_called()
