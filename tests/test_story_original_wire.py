import struct
import unittest
from types import SimpleNamespace as N
from expedition33 import _story_original_wire as w, _story_reward_wire as rewards, _story_item_wire as items

KEY='e33c5701aa6e49679eba69813e5c9409'
def held(i):
    return N(object=N(index=i,serial=i+10,address=0x10000+i*16),_token=i+100)

class OriginalNarrativeWireTests(unittest.TestCase):
    def test_rejected_preflight_reports_reason_without_changing_request_identity(self):
        sent=w.rewrite(1,held(1),held(2),held(3),KEY,0,held(4),held(5),texts=(('key','text'),))
        reply=bytearray(sent);struct.pack_into('<II',reply,8,3950,102)
        with self.assertRaises(w.OriginalNarrativeError) as result:w.decode(sent,bytes(reply))
        self.assertEqual((result.exception.code,result.exception.reason),(3950,102))
        reply[24]^=1
        with self.assertRaisesRegex(RuntimeError,'changed'):w.decode(sent,bytes(reply))
    def test_sound_replacement_requires_owned_identity_and_valid_line_mask(self):
        args=(1,held(1),held(2),held(3),KEY,1,held(4),held(5))
        p=w.rewrite(*args,texts=(('key','text'),),sound=held(6),sound_mask=1)
        self.assertEqual(struct.unpack_from('<I',p,16776)[0],1)
        for at in (16752,16768,16776):
            bad=bytearray(p);bad[at:at+8]=bytes(8)
            with self.assertRaises(ValueError):w.validate(bytes(bad))
        with self.assertRaises(ValueError):w.rewrite(*args,texts=(('key','text'),),sound=held(6),sound_mask=2)
    def test_rewrites_preserve_source_keys_and_reject_unbound_identity(self):
        p=w.rewrite(1,held(1),held(2),held(3),KEY,0,held(4),held(5),texts=(('ST_D_SampleGreeting','A sample greeting.'),))
        self.assertEqual(len(p),20984)
        for offset in (16,72,96,16736):
            bad=bytearray(p);bad[offset:offset+8]=bytes(8)
            with self.assertRaises(ValueError):w.validate(bytes(bad))
        self.assertIn('ST_D_SampleGreeting'.encode('utf-16-le'),p)
        with self.assertRaises(ValueError):w.rewrite(1,held(1),held(2),held(3),'0'*32,0,held(4),held(5),texts=(('key','text'),))

    def test_continuation_cancel_is_distinct_and_unused_bytes_rejected(self):
        p=w.continuation(1,held(1),held(2),held(3),KEY,mode=4,sequence=7)
        self.assertEqual(struct.unpack_from('<I',p,112)[0],4)
        bad=bytearray(p);bad[180]=1
        with self.assertRaises(ValueError):w.validate(bytes(bad))

    def test_reward_receipt_proves_both_grants_and_rejects_rebinding(self):
        p=rewards.encode(1,held(1),held(2).object,held(3),(held(4),held(5)),6,KEY,
            ('Quest_Sample','SkinSample_Default'),
            (('SkinSample_AlternateA','SkinSample_AlternateB'),('SkinExample_Outfit01',)))
        reply=bytearray(p);struct.pack_into('<I',reply,12,1);struct.pack_into('<4Q',reply,752,1,1,2,1)
        self.assertEqual(rewards.decode(p,bytes(reply))['verified_extra_grants'],(2,1))
        struct.pack_into('<Q',reply,768,1)
        with self.assertRaises(RuntimeError):rewards.decode(p,bytes(reply))
        reply[136]=0
        with self.assertRaises(RuntimeError):rewards.decode(p,bytes(reply))

    def test_resource_names_cannot_intern_original_packages(self):
        items.names(1,held(1),held(2),'/Game/SDK/Test/Resource.Resource')
        for path in ('/Game/Gameplay/Resource.Resource','/Game/SDK/../Resource.Resource','/Game/SDK/A.B'):
            with self.assertRaises(ValueError):items.names(1,held(1),held(2),path)
