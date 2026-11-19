import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33 import encounter_action as wire

from encounter_samples import ACTION

class EncounterActionWire(unittest.TestCase):
    def held(self,n):return N(object=N(index=n,serial=2,address=0x10000+n*16),_token=n+10)
    def packet(self,mode=0):return wire.packet(5,tuple(self.held(n) for n in range(1,9)),'e33c5701000000010000000200000003',mode,profile=ACTION)
    def test_apply_inspect_close_roundtrip(self):
        for mode in range(3):
            sent=self.packet(mode);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
            self.assertEqual(wire.decode(sent,bytes(reply)),mode+1)
            reply[56]^=1
            with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
    def test_exact_profile_save_namespace_and_dependencies(self):
        for offset in (216,236,1652):
            data=bytearray(self.packet());data[offset]^=1
            with self.assertRaises(ValueError):wire.validate(bytes(data))
        data=bytearray(self.packet());data[152:160]=bytes(8)
        with self.assertRaises(ValueError):wire.validate(bytes(data))
    def test_active_parameter_clone_blocks_source_cleanup(self):
        owner=object.__new__(wire.EncounterActionData);owner.closed=False;owner.unknown=False;owner.started=True
        with patch.object(owner,'send',side_effect=wire.OriginalNarrativeError(4292)):
            self.assertFalse(owner.close());self.assertTrue(owner.started);self.assertFalse(owner.unknown)
    def test_capability_before_preparation(self):
        with patch.object(wire._Owner,'__init__') as init:
            with self.assertRaisesRegex(RuntimeError,'protocol 2'):
                wire.EncounterActionData(N(_session=N(_transport=N())), 'key',profile=ACTION)
            init.assert_not_called()

class EncounterProfileTests(unittest.TestCase):
    def test_varying_roster_level_music_and_flags_roundtrip(self):
        from copy import deepcopy
        from expedition33 import _encounter_action_profile as profile
        for count in (0,2,6):
            value=deepcopy(ACTION);value['party']=tuple(dict(character='TestMember'+str(i),formation=i%3) for i in range(count))
            value.update(level_offset=12,music='/Game/Audio/OtherTheme.OtherTheme',allow_reserve=True)
            self.assertEqual(profile.decode(profile.encode(value)),value)
        for field,wrong in (('party',[dict(character='A',formation=3)]),('level_offset',-100),('play_intro',1),('table','/Game/Bad.Different')):
            value=deepcopy(ACTION);value[field]=wrong
            with self.assertRaises(ValueError):profile.encode(value)
    def test_padding_and_unused_party_slots_are_rejected(self):
        from expedition33 import _encounter_action_profile as profile
        sent=profile.encode(ACTION)
        for offset in (16,1076+96-240,1411):
            bad=bytearray(sent);bad[offset]^=1
            with self.assertRaises(ValueError):profile.decode(bytes(bad))
