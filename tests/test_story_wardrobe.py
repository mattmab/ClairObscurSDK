import struct,unittest
from expedition33 import story_wardrobe as w
from expedition33._wardrobe_config import encode,decode,inputs
PROFILE=dict(character='TestScholar',template_character='TestTemplate',template_component='TemplateChild',anchor_component='AnchorChild',anchor_tag='Anchor',default_skin='TestSkin',default_face='TestFace',party_offset=(55.,10.,0.),preview_class='/Game/SDK/Sample/Preview.Preview_C',body_anim='/Game/SDK/Sample/BodyAnim.BodyAnim_C',face_anim='/Game/SDK/Sample/FaceAnim.FaceAnim_C',face_mesh='/Game/SDK/Sample/Face.Face',portrait='/Game/SDK/Sample/Portrait.Portrait')
class WardrobeWireTests(unittest.TestCase):
 def packet(self):
  p=bytearray(w.SIZE);struct.pack_into('<4IQ',p,0,3,268,0,0,11)
  for i in range(w.COUNT):struct.pack_into('<iiQ',p,24+16*i,i+1,17,0x10000+i*8)
  struct.pack_into('<'+str(w.COUNT)+'Q',p,w.LEASES,*range(1,w.COUNT+1))
  struct.pack_into('<4I',p,w.GUID,0xe33c5701,1,2,3)
  p[w.PROFILE:w.TAIL]=encode(PROFILE)
  return bytes(p)
 def test_diagnostics_keep_save_and_leases_immutable(self):
  p=self.packet();r=bytearray(p);struct.pack_into('<I',r,12,1);struct.pack_into('<4I',r,w.RESULT,1,4,2,0)
  self.assertEqual(w.decode(p,bytes(r)),dict(previews=1,selections=4,lists=2,stage=0))
  r[w.GUID+4]^=1
  with self.assertRaisesRegex(RuntimeError,'context'):w.decode(p,bytes(r))
 def test_refresh_acknowledges_only_the_bound_owner(self):
  p=bytearray(self.packet());struct.pack_into('<I',p,w.MODE,3)
  sent=bytes(p);reply=bytearray(sent);struct.pack_into('<I',reply,12,4)
  self.assertEqual(w.decode(sent,bytes(reply))['stage'],0)
  reply[w.LEASES]^=1
  with self.assertRaisesRegex(RuntimeError,'context'):w.decode(sent,bytes(reply))
 def test_missing_lease_and_unscoped_save_rejected(self):
  for offset in (w.LEASES,w.GUID):
   p=bytearray(self.packet());p[offset:offset+4]=bytes(4)
   with self.assertRaises(ValueError):w.validate(bytes(p))
 def test_cleanup_mode_and_padding_are_bounded(self):
  p=bytearray(self.packet());struct.pack_into('<I',p,w.MODE,2);w.validate(bytes(p))
  struct.pack_into('<I',p,w.MODE,3);w.validate(bytes(p))
  for mode in (4,5):
   struct.pack_into('<I',p,w.MODE,mode);sent=bytes(p);reply=bytearray(sent);struct.pack_into('<I',reply,12,mode+1)
   self.assertEqual(w.decode(sent,bytes(reply))['stage'],0)
  struct.pack_into('<I',p,w.MODE,6)
  with self.assertRaises(ValueError):w.validate(bytes(p))
  p=bytearray(self.packet());p[-1]=1
  with self.assertRaises(ValueError):w.validate(bytes(p))
if __name__=='__main__':unittest.main()

class WardrobeProfileTests(unittest.TestCase):
 def test_independent_characters_assets_and_spacing(self):
  a=dict(PROFILE);b=dict(PROFILE,character='TestGuardian',portrait='/Game/SDK/Other/Icon.Icon',party_offset=(-80.,30.,5.))
  for p in (a,b):
   self.assertEqual(decode(encode(p)),p);rows=inputs(p)
   self.assertEqual(rows[32]['path'],p['portrait']);self.assertEqual(rows[2]['path'],p['preview_class'])
  self.assertNotEqual(encode(a),encode(b))
 def test_profile_rejects_invalid_asset_class_and_transform(self):
  for changes in (dict(character='bad name'),dict(party_offset=(float('nan'),0,0)),dict(party_offset=(1001,0,0)),dict(face_mesh='/Game/A.B'),dict(body_anim='/Game/A.A'),dict(portrait='/Game/A.A_C')):
   with self.assertRaises(ValueError):encode(dict(PROFILE,**changes))
  raw=bytearray(encode(PROFILE));raw[383]=1
  with self.assertRaises(ValueError):decode(bytes(raw))
 def test_returned_profile_change_is_not_a_valid_receipt(self):
  sent=WardrobeWireTests().packet();reply=bytearray(sent);struct.pack_into('<I',reply,12,1);reply[w.PROFILE]^=1
  with self.assertRaisesRegex(RuntimeError,'context'):w.decode(sent,bytes(reply))
