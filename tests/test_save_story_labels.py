import struct,unittest
from expedition33.save_story_labels import SIGNATURE,PREFIX,STAGE,identity_from_save,label_for_save

def save(entries):
    payload=struct.pack('<II',0,len(entries))+b''.join(struct.pack('<4Ii',*row) for row in entries)
    return b'GVAS'+struct.pack('<I',3)+bytes(16)+SIGNATURE+struct.pack('<IB',len(payload),8)+payload

class SaveStoryLabelTests(unittest.TestCase):
    def test_vanilla_and_bound_story_are_distinguished_from_save_carried_marker(self):
        self.assertEqual(label_for_save(save([(1,2,3,4,1)]),{},{}),'Vanilla')
        key=f'{PREFIX:08x}000000020000000300000004'
        data=save([(PREFIX,2,3,4,STAGE)])
        self.assertEqual(identity_from_save(data),key)
        self.assertEqual(label_for_save(data,{key:{'pack':'opera'}},{'opera':'Sample Story â€” Opera'}),'Sample Story â€” Opera')
        self.assertEqual(label_for_save(data,{},{}),'Custom story (unavailable)')
    def test_invalid_history_never_mislabels_a_save_as_vanilla(self):
        good=save([(PREFIX,2,3,4,STAGE)])
        for bad in (good[:-1],save([(PREFIX,2,3,4,1)]),save([(PREFIX,2,3,4,STAGE),(PREFIX,2,3,5,STAGE)]),b'GVAS'+bytes(40)):
            self.assertEqual(label_for_save(bad,{},{}),'Story unknown')
