import unittest
from expedition33._character_restore_profile import encode,decode
from test_character_restore import PROFILE,_packet,RestoreWireTests
class GraphProfileTests(unittest.TestCase):
 def test_distinct_characters_and_graph_sizes(self):
  for character in ('TestScholar','TestGuardian'):
   for count in (1,3,9):
    p=dict(PROFILE,character=character,skills=PROFILE['skills'][:count])
    got=decode(encode(p));self.assertEqual(got['character'],character);self.assertEqual(len(got['skills']),count)
 def test_missing_profile_is_not_defaulted(self):
  with self.assertRaises(TypeError):_packet(42,RestoreWireTests().inputs(),'e33c5701000000010000000200000003')
 def test_bad_profiles_and_padding_fail(self):
  for changes in (dict(skills=[]),dict(character='bad id'),dict(graph='/Game/SDK/A.B'),dict(skills=[PROFILE['skills'][0]]*2)):
   with self.assertRaises(ValueError):encode(dict(PROFILE,**changes))
  one=bytearray(encode(dict(PROFILE,skills=PROFILE['skills'][:1])))
  for offset in (451,903,4555):
   bad=one[:];bad[offset]^=1
   with self.assertRaises(ValueError):decode(bytes(bad))
