import struct,unittest
from types import SimpleNamespace as N
from expedition33.character_skills import packet,decode,validate,COUNT,LEASES,GUID,MODE,RESULT,DIAGNOSTICS,INPUTS

from skill_samples import PROFILE,profile
from expedition33._character_skill_config import inputs,encode,decode as decode_profile,active

class CharacterSkillWireTests(unittest.TestCase):
 def packet(self,mode=0):
  held=[N(object=N(index=i+1,serial=3,address=0x10000+16*i),_token=i+1) for i in range(COUNT)]
  return packet(5,held,'e33c5701000000010000000200000003',mode,profile=PROFILE)
 def test_every_function_class_sequence_and_lease_is_correlated(self):
  sent=self.packet();reply=bytearray(sent);struct.pack_into('<I',reply,12,1)
  self.assertEqual(decode(sent,bytes(reply))['effects'],(0,)*9)
  for offset in tuple(range(24,LEASES,16))+tuple(range(LEASES,GUID,8))+(GUID,MODE):
   with self.subTest(offset=offset):
    changed=bytearray(reply);changed[offset]^=1
    with self.assertRaisesRegex(RuntimeError,'context changed'):decode(sent,bytes(changed))
 def test_native_setup_failure_keeps_its_stage_and_error_code(self):
  from expedition33._story_original_wire import OriginalNarrativeError
  sent=self.packet();reply=bytearray(sent)
  struct.pack_into('<I',reply,8,4280);struct.pack_into('<I',reply,RESULT+92,1138)
  with self.assertRaises(OriginalNarrativeError) as caught:decode(sent,bytes(reply))
  self.assertEqual(caught.exception.code,4280);self.assertEqual(caught.exception.stage,1138)
  self.assertIn('Character skill native stage: 1138',caught.exception.__notes__)
 def test_status_preserves_all_nine_counters_and_real_qte_multiplier(self):
  sent=self.packet(1);reply=bytearray(sent);struct.pack_into('<I',reply,12,2)
  struct.pack_into('<24I2d3I',reply,RESULT,*range(24),.3,1.2,2,3,4)
  observed=decode(sent,bytes(reply))
  self.assertEqual(observed['executions'],tuple(range(9)));self.assertEqual(observed['effects'],tuple(range(9,18)))
  self.assertEqual(observed['last_qte_multiplier'],1.2)
  self.assertEqual((observed['meter_starts'],observed['meter_initialized'],observed['meter_forwarded']),(2,3,4))
  reply[RESULT+DIAGNOSTICS]=1
  with self.assertRaisesRegex(RuntimeError,'context changed'):decode(sent,bytes(reply))
 def test_nan_diagnostics_and_unknown_modes_are_not_accepted(self):
  sent=self.packet(1);reply=bytearray(sent);struct.pack_into('<I',reply,12,2)
  for offset in (96,104):
   changed=bytearray(reply);struct.pack_into('<d',changed,RESULT+offset,float('nan'))
   with self.assertRaisesRegex(RuntimeError,'diagnostic'):decode(sent,bytes(changed))
  wrong=bytearray(sent);struct.pack_into('<I',wrong,MODE,3)
  with self.assertRaises(ValueError):validate(bytes(wrong))
 def test_profiles_support_distinct_casts_and_skill_counts(self):
  for count in (1,3,9):
   for meter in (False,True):
    for actor in ('TestScholar','TestGuardian'):
     p=profile(count,meter,actor);got=decode_profile(encode(p));self.assertEqual(got,p)
     dependencies=inputs(p);self.assertEqual(len(dependencies),80)
     for i,row in enumerate(dependencies):self.assertEqual(row is not None,active(i,count,meter))
 def test_inactive_packet_slots_must_be_zero(self):
  p=profile(1,False);held=[N(object=N(index=i+1,serial=3,address=0x10000+16*i),_token=i+1) if active(i,1,False) else None for i in range(COUNT)]
  data=packet(5,held,'e33c5701000000010000000200000003',profile=p);validate(data)
  for at in (24+19*16,LEASES+19*8,24+42*16):
   bad=bytearray(data);bad[at]=1
   with self.assertRaises(ValueError):validate(bytes(bad))
 def test_policy_and_profile_mutation_rejected(self):
  for edits in (dict(count=0),):
   with self.assertRaises(ValueError):encode(profile(edits['count']))
  p=profile();p['skills'][0]['damage']=float('nan')
  with self.assertRaises(ValueError):encode(p)
  p=profile();p['meter']['cap']=0
  with self.assertRaises(ValueError):encode(p)
  p=profile(1,False);p['paths']['meter']='/Game/X.X_C:Callback'
  with self.assertRaises(ValueError):encode(p)
 def test_partial_install_uncertainty_retains_scope_before_started_receipt(self):
  from unittest.mock import Mock
  from expedition33.character_skills import CharacterSkills
  from expedition33._story_original_wire import OriginalNarrativeError
  held=[N(object=N(index=i+1,serial=3,address=0x10000+16*i),_token=i+1) for i in range(COUNT)]
  def command(_,sent):
   reply=bytearray(sent);struct.pack_into('<I',reply,8,4281)
   return {'mesh_packet':bytes(reply).hex()}
  owner=CharacterSkills.__new__(CharacterSkills)
  owner.owner=5;owner.objects=held;owner.profile=PROFILE;owner.key='e33c5701000000010000000200000003'
  owner.started=False;owner.closed=False;owner.unknown=False
  owner.scope=N(_session=N(_transport=N(command=command)),close=Mock())
  with self.assertRaises(OriginalNarrativeError):owner.send(0)
  self.assertTrue(owner.unknown);self.assertFalse(owner.close())
  owner.scope.close.assert_not_called()

if __name__=='__main__':unittest.main()
