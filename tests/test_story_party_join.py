import struct,unittest
from types import SimpleNamespace as N
from unittest.mock import patch
from expedition33 import party as wire

class PartyJoinWire(unittest.TestCase):
    def held(self,n):return N(object=N(index=n,serial=2,address=0x10000+n*16),_token=n+10)
    def packet(self,mode=0):return wire.packet(5,self.held(1),self.held(2),self.held(3),'e33c5701000000010000000200000003',mode,character='TestScholar')
    def test_apply_inspect_close_roundtrip(self):
        for mode in range(3):
            sent=self.packet(mode);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
            self.assertEqual(wire.decode(sent,bytes(reply)),mode+1)
            reply[40]^=1
            with self.assertRaises(RuntimeError):wire.decode(sent,bytes(reply))
    def test_only_exact_profile_and_save_namespace(self):
        for offset in (72,96,116,216):
            packet=bytearray(self.packet());packet[offset]^=1
            if offset==72:packet[72:80]=bytes(8)
            with self.assertRaises(ValueError):wire.validate(bytes(packet))
    def test_two_distinct_consumer_ids_use_the_same_packet_contract(self):
        for name in ('TestScholar','TestGuardian'):
            sent=wire.packet(5,self.held(1),self.held(2),self.held(3),
                             'e33c5701000000010000000200000003',character=name)
            self.assertEqual(sent[120:216].split(b'\0',1)[0].decode(),name)
            wire.validate(sent)
    def test_missing_invalid_or_ambiguous_ids_are_rejected(self):
        for name in ('','x'*96,'../row','name space','name\0suffix',None,42):
            with self.subTest(name=name),self.assertRaises(ValueError):wire.character_id(name)
        malformed=bytearray(self.packet());malformed[132]=1
        with self.assertRaises(ValueError):wire.validate(bytes(malformed))
        with self.assertRaises(TypeError):
            wire.packet(5,self.held(1),self.held(2),self.held(3),'e33c5701000000010000000200000003')
    def test_busy_close_retains_owner_and_scope(self):
        owner=object.__new__(wire.PartyJoinData);owner.closed=False;owner.unknown=False;owner.started=True
        with patch.object(owner,'send',side_effect=wire.OriginalNarrativeError(4272)):
            self.assertFalse(owner.close());self.assertTrue(owner.started);self.assertFalse(owner.unknown)
    def test_capability_before_preparation(self):
        with patch.object(wire._Owner,'__init__') as init:
            with self.assertRaisesRegex(RuntimeError,'protocol 2'):
                wire.PartyJoinData(N(_session=N(_transport=N())), 'key',character='TestScholar')
            init.assert_not_called()
