import struct,unittest
from types import SimpleNamespace as N
from expedition33.battle_qte import packet,validate,decode
PROFILE=dict(sequence='/Game/SDK/Sample/Sequence.Sequence',character_class='/Game/SDK/Sample/Character.Character_C',script_class='/Game/SDK/Sample/Skill.Skill_C',impacts=(1.5,3.),validity=.2,anticipation=.4,lead=.01,bonus_per_input=.15,damage_reason=1)
class BattleQTEWireTests(unittest.TestCase):
 def sent(self,mode=0):
  held=[N(object=N(index=i+1,serial=2,address=0x10000+i*16),_token=i+10) for i in range(10)]
  return packet(42,held,'e33c5701000000010000000200000003',mode,profile=PROFILE)
 def test_selected_save_and_all_ten_dependencies_are_correlated(self):
  sent=self.sent();reply=bytearray(sent);struct.pack_into('<I',reply,12,1)
  self.assertEqual(decode(sent,bytes(reply)),0)
  for offset in (24,40,56,72,88,104,120,136,152,168,184,256,264,280):
   changed=bytearray(reply);changed[offset]^=1
   with self.assertRaises(RuntimeError):decode(sent,bytes(changed))
 def test_status_and_close_require_their_distinct_acknowledgements(self):
  for mode in (1,2):
   sent=self.sent(mode);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
   if mode==1:struct.pack_into('<I',reply,284,4)
   self.assertEqual(decode(sent,bytes(reply)),4 if mode==1 else 0)
   struct.pack_into('<I',reply,12,1)
   with self.assertRaises(RuntimeError):decode(sent,bytes(reply))
 def test_unknown_modes_and_nonzero_tail_are_rejected(self):
  for offset,value in ((280,3),(288,1),(20983,1)):
   wrong=bytearray(self.sent());wrong[offset]=value
   with self.assertRaises(ValueError):validate(bytes(wrong))
 def test_failure_diagnostics_do_not_weaken_context_validation(self):
  from expedition33._story_original_wire import OriginalNarrativeError
  sent=self.sent(1);reply=bytearray(sent)
  struct.pack_into('<I',reply,8,4251)
  struct.pack_into('<7I2d',reply,288,1,1,1,1,1,1,6,0.,.5666667)
  with self.assertRaises(OriginalNarrativeError):decode(sent,bytes(reply))
  reply[356]=1
  with self.assertRaisesRegex(RuntimeError,'context changed'):decode(sent,bytes(reply))
 def test_uncertain_partial_install_retains_scope_without_started_receipt(self):
  from unittest.mock import Mock
  from expedition33.battle_qte import BattleQTE
  from expedition33._story_original_wire import OriginalNarrativeError
  held=[N(object=N(index=i+1,serial=2,address=0x10000+i*16),_token=i+10) for i in range(10)]
  def command(_,sent):
   reply=bytearray(sent);struct.pack_into('<I',reply,8,4251)
   return {'mesh_packet':bytes(reply).hex()}
  owner=BattleQTE.__new__(BattleQTE);owner.owner=42;owner.objects=held;owner.profile=PROFILE
  owner.key='e33c5701000000010000000200000003';owner.closed=False;owner.started=False;owner.unknown=False
  owner.scope=N(_session=N(_transport=N(command=command)),close=Mock())
  with self.assertRaises(OriginalNarrativeError):owner.send(0)
  self.assertTrue(owner.unknown);self.assertFalse(owner.close());owner.scope.close.assert_not_called()
 def test_late_cast_is_reported_once_without_quarantining_next_cast(self):
  from unittest.mock import Mock
  from expedition33.battle_qte import BattleQTE
  owner=BattleQTE.__new__(BattleQTE);owner.send=Mock(return_value=2);owner.unknown=False
  owner.diagnostics=(1,1,1,1,1,1,11,0.,.96)
  with self.assertLogs('expedition33.battle_qte',level='ERROR') as logs:
   self.assertEqual(owner.status(),2);owner.status()
  self.assertEqual(len(logs.output),1);self.assertIn('investigation required',logs.output[0]);self.assertFalse(owner.unknown)
  owner.diagnostics=(2,2,2,2,2,2,10,0.,.6)
  with self.assertNoLogs('expedition33.battle_qte',level='ERROR'):owner.status()

class QTEProfileTests(unittest.TestCase):
 def test_different_sequences_counts_timings_and_rewards(self):
  from expedition33._battle_qte_profile import encode,decode
  for n in (1,4,16):
   p=dict(PROFILE,sequence='/Game/SDK/Other/Attack.Attack',impacts=tuple(float(i+1) for i in range(n)),validity=.12,bonus_per_input=.25)
   self.assertEqual(decode(encode(p)),p)
 def test_unsorted_impacts_and_nonfinite_intervals_rejected(self):
  from expedition33._battle_qte_profile import encode,decode
  for changes in (dict(impacts=()),dict(impacts=(2.,1.)),dict(impacts=(1.,1.)),dict(validity=float('nan')),dict(lead=0),dict(damage_reason=256)):
   with self.assertRaises(ValueError):encode(dict(PROFILE,**changes))
  raw=bytearray(encode(PROFILE));raw[383]=1
  with self.assertRaises(ValueError):decode(bytes(raw))
